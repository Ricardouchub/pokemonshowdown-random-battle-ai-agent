from __future__ import annotations

from typing import List

from ps_agent.state.battle_state import BattleState


def enumerate_legal_actions(state: BattleState) -> List[str]:
    """Enumerate legal moves and switches for the active Pokémon on both sides."""
    actions: List[str] = []
    active = state.player_self.active_pokemon()
    if active.moves_known:
        actions.extend([f"move:{m}" for m in active.moves_known])
    else:
        actions.extend([f"move{i}" for i in range(1, 5)])

    for idx, mon in enumerate(state.player_self.team):
        if idx == state.player_self.active_slot:
            continue
        if mon.is_fainted:
            continue
        actions.append(f"switch:{mon.species or idx}")
    # Deduplicate while preserving order
    seen = set()
    unique_actions = []
    for action in actions:
        if action not in seen:
            unique_actions.append(action)
            seen.add(action)
    return unique_actions
