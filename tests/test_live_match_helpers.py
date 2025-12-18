import json

import pytest

from ps_agent.runner.live_match import LiveMatchRunner, apply_request_to_state, parse_request_actions
from ps_agent.state.battle_state import BattleState, PlayerState
from ps_agent.state.pokemon_state import PokemonState


def make_state():
    player = PlayerState(name="bot", team=[PokemonState(species="a")] * 6, active_slot=0)
    opp = PlayerState(name="opp", team=[PokemonState(species="b")] * 6, active_slot=0)
    return BattleState.new(
        battle_id="battle-test",
        gen=9,
        format="randombattle",
        player_self=player,
        player_opponent=opp,
        turn=0,
    )


def test_parse_request_actions_moves_and_switches():
    request = {
        "active": [
            {
                "moves": [
                    {"move": "Thunderbolt", "id": "thunderbolt", "disabled": False},
                    {"move": "Surf", "id": "surf", "disabled": True},
                ]
            }
        ],
        "side": {
            "pokemon": [
                {"ident": "p1: Raichu", "details": "Raichu, L80", "active": True, "condition": "200/200"},
                {"ident": "p1: Vaporeon", "details": "Vaporeon, L80", "active": False, "condition": "1/1"},
            ]
        },
    }
    actions = parse_request_actions(request)
    labels = [a.label for a in actions]
    assert "move:thunderbolt" in labels
    assert all("surf" not in label for label in labels)
    assert any(label.startswith("switch:") for label in labels)


def test_apply_request_to_state_updates_team():
    request = {
        "side": {
            "name": "CodexBot",
            "pokemon": [
                {"details": "Charizard, L80", "condition": "200/200", "active": True, "moves": ["ember", "airslash"]},
                {"details": "Blastoise, L80", "condition": "0 fnt", "active": False, "moves": ["surf"]},
            ]
        }
    }
    state = make_state()
    updated = apply_request_to_state(state, request)
    assert updated.player_self.team[0].species == "Charizard"
    assert updated.player_self.team[0].moves_known == ("ember", "airslash")
    assert updated.player_self.team[1].is_fainted is True


def test_fetch_assertion(monkeypatch, tmp_path):
    runner = LiveMatchRunner(
        server_url="ws://test",
        username="CodexBot",
        password=None,
        log_dir=tmp_path,
        http_base="http://example",
    )

    class DummyResp:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    def fake_post(url, data, timeout):
        assert data["userid"] == "codexbot"
        assert "challstr" in data
        return DummyResp("assert-token")

    monkeypatch.setattr("ps_agent.runner.live_match.requests.post", fake_post)
    token = runner._fetch_assertion("1|challenge")
    assert token == "assert-token"


@pytest.mark.asyncio
async def test_handle_updateuser_joins_rooms(tmp_path):
    runner = LiveMatchRunner(
        server_url="ws://test",
        username="CodexBot",
        password=None,
        log_dir=tmp_path,
        http_base="http://example",
        rooms=["lobby", "staff"],
    )

    class DummyClient:
        def __init__(self):
            self.sent: List[str] = []

        async def send(self, message: str) -> None:
            self.sent.append(message)

    dummy = DummyClient()
    runner.client = dummy
    await runner._handle_updateuser("|updateuser| CodexBot|1|102|{}")
    assert dummy.sent == ["|/join lobby", "|/join staff"]


@pytest.mark.asyncio
async def test_handle_pm_accepts_challenge(tmp_path):
    runner = LiveMatchRunner(
        server_url="ws://test",
        username="CodexBot",
        password=None,
        log_dir=tmp_path,
        http_base="http://example",
        rooms=[],
    )

    class DummyClient:
        def __init__(self):
            self.sent: List[str] = []

        async def send(self, message: str) -> None:
            self.sent.append(message)

    dummy = DummyClient()
    runner.client = dummy
    await runner._handle_pm("|pm| Rickybot| CodexBot|/challenge gen9randombattle|gen9randombattle|||")
    assert dummy.sent == ["|/accept Rickybot"]


@pytest.mark.asyncio
async def test_send_battle_command_includes_rqid(tmp_path):
    runner = LiveMatchRunner(
        server_url="ws://test",
        username="CodexBot",
        password=None,
        log_dir=tmp_path,
        http_base="http://example",
        rooms=[],
    )

    class DummyClient:
        def __init__(self):
            self.sent: List[str] = []

        async def send(self, message: str) -> None:
            self.sent.append(message)

    dummy = DummyClient()
    runner.client = dummy
    await runner._send_battle_command("battle-test", "/choose move 1", rqid=3)
    assert dummy.sent == [">battle-test|/choose move 1|3"]
