from __future__ import annotations

from typing import Iterable, Tuple

from ps_agent.policy.evaluator import Evaluator
from ps_agent.state.battle_state import BattleState


class LookaheadPlanner:
    """One-ply lookahead stub; extend with real simulation."""

    def __init__(self, evaluator: Evaluator | None = None) -> None:
        self.evaluator = evaluator or Evaluator()

    def choose(self, state: BattleState, legal_actions: Iterable[str]) -> Tuple[str, float]:
        best_action = None
        best_score = float("-inf")
        for action in legal_actions:
            score = self.evaluator.evaluate(state, action)
            if score > best_score:
                best_action = action
                best_score = score
        if best_action is None:
            raise ValueError("No legal actions provided")
        return best_action, best_score
