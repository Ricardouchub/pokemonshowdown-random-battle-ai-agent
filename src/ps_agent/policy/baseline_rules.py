from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from ps_agent.policy.evaluator import Evaluator
from ps_agent.policy.legal_actions import enumerate_legal_actions
from ps_agent.state.battle_state import BattleState


@dataclass(frozen=True)
class ActionInsight:
    action: str
    score: float
    breakdown: Dict[str, float]


class BaselinePolicy:
    """Baseline deterministic policy following simple rules.

    The policy is intentionally conservative and deterministic for reproducibility.
    """

    def __init__(self, evaluator: Evaluator | None = None) -> None:
        self.evaluator = evaluator or Evaluator()

    def choose_action(
        self,
        state: BattleState,
        legal_actions: Optional[Iterable[str]] = None,
        top_k: int = 3,
    ) -> Tuple[str, List[str], List[ActionInsight]]:
        actions_iterable = legal_actions or enumerate_legal_actions(state)
        actions = sorted(set(actions_iterable))
        if not actions:
            raise ValueError("No legal actions provided")
        scored = [(self.evaluator.evaluate(state, act), act) for act in actions]
        scored.sort(key=lambda x: (-x[0], x[1]))
        chosen = scored[0][1]
        ordered = [act for _, act in scored]
        insights: List[ActionInsight] = []
        for _, action in scored[:top_k]:
            breakdown = self.evaluator.explain(state, action)
            insights.append(ActionInsight(action=action, score=breakdown["score"], breakdown=breakdown))
        return chosen, ordered, insights
