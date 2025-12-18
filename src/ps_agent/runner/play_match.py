from __future__ import annotations

import random
from pathlib import Path
import argparse
from typing import Dict

from ps_agent.logging.event_log import EventLogger
from ps_agent.policy.baseline_rules import BaselinePolicy
from ps_agent.policy.factory import create_policy
from ps_agent.policy.legal_actions import enumerate_legal_actions
from ps_agent.state.battle_state import BattleState, PlayerState
from ps_agent.state.pokemon_state import PokemonState


def _dummy_player(name: str) -> PlayerState:
    team = [PokemonState(species=f"{name}-poke-{i+1}") for i in range(6)]
    return PlayerState(name=name, rating=None, active_slot=0, team=team)


def play_match(
    seed: int,
    policy_self: BaselinePolicy | None = None,
    policy_opp: BaselinePolicy | None = None,
    mode: str = "offline",
    log_path: str | None = None,
    max_turns: int = 3,
) -> Dict[str, object]:
    """Run a minimal deterministic mock match to verify plumbing.

    This stub does not communicate with Showdown yet but preserves the public API.
    """

    random.seed(seed)
    policy_self = policy_self or BaselinePolicy()
    policy_opp = policy_opp or BaselinePolicy()

    state = BattleState.new(
        battle_id=f"offline-{seed}",
        gen=9,
        format="randombattle",
        player_self=_dummy_player("self"),
        player_opponent=_dummy_player("opp"),
        turn=0,
    )

    logger = EventLogger(log_path=Path(log_path) if log_path else Path("artifacts/logs/mock.log"))
    for turn in range(1, max_turns + 1):
        state = state.with_turn(turn)
        legal_actions = enumerate_legal_actions(state)
        action_self, ranked_self, insights_self = policy_self.choose_action(state, legal_actions)
        action_opp, ranked_opp, _ = policy_opp.choose_action(state, legal_actions)
        top_actions_payload = [
            {"action": insight.action, "score": insight.score, "breakdown": insight.breakdown}
            for insight in insights_self
        ]
        logger.log_turn(
            state,
            chosen_action=action_self,
            legal_actions=legal_actions,
            reasons=top_actions_payload[0]["breakdown"] if top_actions_payload else {},
            top_actions=top_actions_payload,
            extras={
                "opponent_action": action_opp,
                "ranked_self": ranked_self,
                "ranked_opp": ranked_opp,
            },
        )

    return {
        "battle_id": state.battle_id,
        "turns": max_turns,
        "result": "mock",
        "mode": mode,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a mock Random Battle match with configurable policy.")
    parser.add_argument("--seed", type=int, default=1, help="Random seed for deterministic behavior.")
    parser.add_argument("--max-turns", type=int, default=3, help="Number of turns to simulate.")
    parser.add_argument("--log-path", type=str, default="artifacts/logs/mock.log", help="Path to JSONL log.")
    parser.add_argument(
        "--policy",
        default="baseline",
        help="Policy to use (baseline or llm). Opponent always uses baseline for now.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    policy = create_policy(args.policy)
    result = play_match(
        seed=args.seed,
        max_turns=args.max_turns,
        log_path=args.log_path,
        policy_self=policy,
        policy_opp=BaselinePolicy(),
    )
    print(result)


if __name__ == "__main__":
    main()
