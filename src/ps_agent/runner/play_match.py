from __future__ import annotations

import random
from pathlib import Path
from typing import Dict

from ps_agent.logging.event_log import EventLogger
from ps_agent.policy.baseline_rules import BaselinePolicy
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
        action_self, ranked_self = policy_self.choose_action(state, legal_actions)
        action_opp, ranked_opp = policy_opp.choose_action(state, legal_actions)
        logger.log_turn(
            state,
            chosen_action=action_self,
            legal_actions=legal_actions,
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
