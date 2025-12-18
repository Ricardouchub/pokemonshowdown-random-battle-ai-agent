from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, List, Optional

import requests

from ps_agent.connector.protocol_parser import ProtocolParser
from ps_agent.connector.showdown_client import ShowdownClient, ShowdownClientConfig
from ps_agent.logging.event_log import EventLogger
from ps_agent.policy.baseline_rules import BaselinePolicy
from ps_agent.policy.factory import create_policy
from ps_agent.policy.llm_policy import LLMPolicy
from ps_agent.state.battle_state import BattleState, PlayerState
from ps_agent.state.pokemon_state import PokemonState
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ActionOption:
    label: str
    command: str
    meta: Dict[str, object]


@dataclass
class BattleContext:
    battle_id: str
    state: BattleState
    logger: EventLogger
    policy: BaselinePolicy
    parser: ProtocolParser


def _placeholder_player(name: str) -> PlayerState:
    return PlayerState(name=name, rating=None, active_slot=0, team=PokemonState.empty_team())


def parse_request_actions(request_data: Dict[str, object]) -> List[ActionOption]:
    actions: List[ActionOption] = []
    if request_data.get("wait"):
        return actions

    active_data = request_data.get("active") or []
    trapped = False
    if active_data:
        trapped = active_data[0].get("trapped", False)
    if active_data:
        moves = active_data[0].get("moves", [])
        for idx, move in enumerate(moves, start=1):
            if move.get("disabled"):
                continue
            move_id = move.get("id") or move.get("move", f"move{idx}").lower().replace(" ", "-")
            label = f"move:{move_id}"
            command = f"/choose move {idx}"
            actions.append(ActionOption(label=label, command=command, meta={"slot": idx, "move": move_id}))

    side = request_data.get("side") or {}
    pokemon = side.get("pokemon", [])
    for idx, mon in enumerate(pokemon, start=1):
        if trapped:
            continue  # Cannot switch if trapped
        condition = mon.get("condition", "")
        if mon.get("active"):
            continue
        if "fnt" in condition:
            continue
        ident = mon.get("ident", f"slot-{idx}")
        # Use name for switch command as it is more robust on some servers
        name = ident.split(':')[-1].strip()
        label = f"switch:{name or idx}"
        command = f"/choose switch {name}"
        actions.append(ActionOption(label=label, command=command, meta={"slot": idx, "name": name}))

    return actions


def _parse_hp_fraction(condition: str) -> float:
    if "fnt" in condition:
        return 0.0
    if "/" in condition:
        current, total = condition.split("/")[:2]
        try:
            return max(0.0, min(1.0, float(_sanitize_hp(current)) / float(_sanitize_hp(total))))
        except ValueError:
            return 1.0
    return 1.0


def _sanitize_hp(value: str) -> float:
    return float(value.replace("%", "")) if "%" in value else float(value)


def apply_request_to_state(state: BattleState, request_data: Dict[str, object]) -> BattleState:
    side = request_data.get("side") or {}
    team_payload = side.get("pokemon", [])
    team: List[PokemonState] = []
    active_slot = 0
    for idx, mon in enumerate(team_payload):
        details = mon.get("details", f"unknown-{idx+1}")
        species = details.split(",")[0].strip()
        hp_fraction = _parse_hp_fraction(mon.get("condition", "1/1"))
        moves_known = tuple(mon.get("moves", []))
        poke = PokemonState(
            species=species or f"unknown-{idx+1}",
            level=mon.get("level", 100),
            hp_fraction=hp_fraction,
            status=None,
            is_fainted="fnt" in mon.get("condition", ""),
            moves_known=moves_known,
            active=mon.get("active", False),
            ability=mon.get("ability"),
            item=mon.get("item"),
        )
        if mon.get("active"):
            active_slot = idx
        team.append(poke)

    if not team:
        team = state.player_self.team

    player_self = replace(
        state.player_self,
        name=side.get("name", state.player_self.name),
        team=team,
        active_slot=active_slot,
    )
    return replace(state, player_self=player_self)


class LiveMatchRunner:
    def __init__(
        self,
        server_url: str,
        username: str,
        password: str | None,
        log_dir: str | Path,
        http_base: str,
        rooms: Optional[List[str]] = None,
        policy_name: str = "baseline",
    ) -> None:
        self.config = ShowdownClientConfig(server_url=server_url, username=username, password=password)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.client: Optional[ShowdownClient] = None
        self.contexts: Dict[str, BattleContext] = {}
        self.http_base = http_base.rstrip("/")
        self.rooms = rooms or []
        self.logged_in = False
        policy = create_policy(policy_name)
        self.policy = policy

    async def _log_traffic(self, direction: str, content: str) -> None:
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{direction}] {content}\n"
        with open("artifacts/logs/live/traffic.log", "a", encoding="utf-8") as f:
            f.write(log_entry)

    async def run(self) -> None:
        async with ShowdownClient(self.config) as client:
            self.client = client
            async for message in client.messages():
                await self._log_traffic("IN", message)
                await self._handle_raw_message(message)

    async def _handle_raw_message(self, message: str) -> None:
        current_battle: Optional[str] = None
        for line in message.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("|challstr|"):
                await self._handle_challstr(line)
            elif line.startswith("|updateuser|"):
                await self._handle_updateuser(line)
            elif line.startswith("|pm|"):
                await self._handle_pm(line)
            elif line.startswith(">"):
                data = line[1:]
                if "|" in data:
                    battle_id, content = data.split("|", 1)
                    current_battle = battle_id
                    await self._handle_battle_line(battle_id, f"|{content}")
                else:
                    current_battle = data
            else:
                if line.startswith("|") and current_battle:
                    await self._handle_battle_line(current_battle, line)
                else:
                    logger.debug("unhandled_line", line=line)

    async def _handle_challstr(self, line: str) -> None:
        logger.info("received_challstr")
        assert self.client is not None
        chall_parts = line.split("|")[2:]
        challstr = "|".join(chall_parts)
        try:
            assertion = self._fetch_assertion(challstr)
        except Exception as exc:
            logger.error("assertion_failed", error=str(exc))
            return
        
        msg = f"|/trn {self.config.username},0,{assertion}"
        await self._log_traffic("OUT", msg)
        await self.client.send(msg)

    async def _handle_battle_line(self, battle_id: str, content: str) -> None:
        context = self.contexts.get(battle_id)
        if context is None:
            context = self._create_context(battle_id)
            self.contexts[battle_id] = context

        if content.startswith("|init|"):
            join_cmd = f"|/join {battle_id}"
            await self._log_traffic("OUT", join_cmd)
            await self.client.send(join_cmd)

        if content.startswith("|request|"):
            request_payload = content.split("|request|", 1)[1]
            await self._handle_request(context, battle_id, request_payload)
            return

        logger.debug("battle_event", battle_id=battle_id, content=content[:200])
        events = context.parser.parse_events([content])
        context.state = context.parser.apply(events, context.state)

    async def _handle_request(self, context: BattleContext, battle_id: str, payload: str) -> None:
        # Ensure we are joined to the room to avoid "must be used in a chat room" error
        if self.client:
            join_cmd = f"|/join {battle_id}"
            await self._log_traffic("OUT", join_cmd)
            await self.client.send(join_cmd)
            # Short safety delay
            await asyncio.sleep(0.1)


        try:
            request_data = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("invalid_request_json", payload=payload[:200])
            return

        if len(payload) > 1000:
            logger.debug("request_payload_truncated", battle_id=battle_id, payload_len=len(payload))
        else:
            logger.debug("request_payload", battle_id=battle_id, payload=payload)
        
        # DEBUG: Write payload to file for inspection
        with open("artifacts/logs/live/debug_payloads.log", "a", encoding="utf-8") as f:
            f.write(f"--- BATTLE {battle_id} ---\n")
            f.write(payload + "\n")

        context.state = apply_request_to_state(context.state, request_data)
        options = parse_request_actions(request_data)
        if not options:
            logger.info("no_actions_available", battle_id=battle_id)
            return
        labels = [opt.label for opt in options]
        chosen, ordered, insights = context.policy.choose_action(context.state, labels)
        option = next((opt for opt in options if opt.label == chosen), options[0])
        rqid = request_data.get("rqid")
        await self._send_battle_command(battle_id, option.command, rqid=rqid)
        context.logger.log_turn(
            context.state,
            chosen_action=option.label,
            legal_actions=labels,
            reasons=insights[0].breakdown if insights else {},
            top_actions=[{"action": insight.action, "score": insight.score, "breakdown": insight.breakdown} for insight in insights],
            extras={"ordered_actions": ordered},
        )

    async def _send_battle_command(self, battle_id: str, command: str, rqid: int | None = None) -> None:
        if not self.client:
            raise RuntimeError("Client not connected")
        line = command
        if rqid is not None:
            line = f"{line}|{rqid}"
        payload = f"{battle_id}|{line}"
        logger.debug("sending_battle_command", battle_id=battle_id, command=line)

        # DEBUG: Write sent payload (Legacy debug file)
        with open("artifacts/logs/live/debug_payloads.log", "a", encoding="utf-8") as f:
            f.write(f"SENT: {payload}\n")

        await self._log_traffic("OUT", payload)
        await self.client.send(payload)

    def _create_context(self, battle_id: str) -> BattleContext:
        parser = ProtocolParser()
        state = parser.bootstrap(
            battle_id=battle_id,
            gen=9,
            format="randombattle",
            player_self=_placeholder_player(self.config.username),
            player_opp=_placeholder_player("opponent"),
        )
        log_path = self.log_dir / f"{battle_id}.log"
        logger.info("context_created", battle_id=battle_id, log=str(log_path))
        return BattleContext(
            battle_id=battle_id,
            state=state,
            logger=EventLogger(log_path=log_path),
            policy=self.policy,
            parser=parser,
        )
        # Wait, the return statement line 256 in original file was simple. I should be careful not to introduce syntax errors.
        # Let's re-read the _create_context in original to match args.
        # Original: return BattleContext(battle_id=battle_id, state=state, logger=EventLogger..., policy=self.policy, parser=parser)
        
    def _fetch_assertion(self, challstr: str) -> str:
        userid = "".join(ch.lower() for ch in self.config.username if ch.isalnum())
        url = f"{self.http_base}/action.php"
        resp = requests.post(
            url,
            data={"act": "getassertion", "userid": userid, "challstr": challstr},
            timeout=10,
        )
        resp.raise_for_status()
        assertion = resp.text.strip()
        if not assertion:
            raise RuntimeError("empty assertion response")
        logger.info("assertion_obtained")
        return assertion

    async def _handle_updateuser(self, line: str) -> None:
        parts = line.split("|")
        if len(parts) < 4:
            return
        username = parts[2].strip()
        success_flag = parts[3].strip()
        if username.lower() != self.config.username.lower():
            return
        if success_flag != "1":
            logger.warning("updateuser_failed", line=line)
            return
        if self.logged_in:
            return
        self.logged_in = True
        logger.info("login_confirmed", username=username)
        if not self.rooms or not self.client:
            return
        for room in self.rooms:
            join_cmd = f"|/join {room}"
            await self._log_traffic("OUT", join_cmd)
            await self.client.send(join_cmd)
            logger.info("room_join_sent", room=room)

    async def _handle_pm(self, line: str) -> None:
        parts = line.split("|")
        if len(parts) < 5:
            return
        sender = parts[2].strip()
        receiver = parts[3].strip()
        if receiver.lower() != self.config.username.lower():
            return
        message = "|".join(parts[4:]).strip()
        if message.startswith("/challenge"):
            logger.info("challenge_received", challenger=sender, payload=message)
            if self.client:
                accept_cmd = f"|/accept {sender}"
                await self._log_traffic("OUT", accept_cmd)
                await self.client.send(accept_cmd)
                logger.info("challenge_accepted", challenger=sender)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the agent against a local Showdown server.")
    parser.add_argument("--server-url", default="ws://localhost:8000/showdown/websocket", help="Websocket URL.")
    parser.add_argument("--username", default="CodexBot", help="Bot username.")
    parser.add_argument("--password", default=None, help="Bot password/assertion (if needed).")
    parser.add_argument("--log-dir", default="artifacts/logs/live", help="Directory for live battle logs.")
    parser.add_argument("--http-base", default="http://localhost:8000", help="HTTP base URL for challstr assertions.")
    parser.add_argument(
        "--autojoin",
        action="append",
        help="Room to join after login (can be specified multiple times). Defaults to lobby.",
    )
    parser.add_argument(
        "--policy",
        default="baseline",
        help="Policy to use for decision making (baseline or llm).",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    rooms = args.autojoin if args.autojoin else ["lobby"]
    runner = LiveMatchRunner(
        server_url=args.server_url,
        username=args.username,
        password=args.password,
        log_dir=args.log_dir,
        http_base=args.http_base,
        rooms=rooms,
        policy_name=args.policy,
    )
    await runner.run()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
