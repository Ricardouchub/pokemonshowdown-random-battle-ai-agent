from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import List

from ps_agent.knowledge.randbats_sets import SetHypothesis


@dataclass(frozen=True)
class BeliefState:
    candidates: List[SetHypothesis] = field(default_factory=list)
    evidence_log: List[str] = field(default_factory=list)

    def normalize(self) -> "BeliefState":
        total = sum(c.posterior_prob for c in self.candidates) or 1.0
        normalized = [
            replace(c, posterior_prob=c.posterior_prob / total) for c in self.candidates
        ]
        return replace(self, candidates=normalized)

    def update_with_move(self, move: str) -> "BeliefState":
        filtered = [c for c in self.candidates if move in c.moves]
        evidence = self.evidence_log + [f"move:{move}"]
        return BeliefState(candidates=filtered or self.candidates, evidence_log=evidence).normalize()

    def update_with_item(self, item: str) -> "BeliefState":
        filtered = [c for c in self.candidates if c.item == item]
        evidence = self.evidence_log + [f"item:{item}"]
        return BeliefState(candidates=filtered or self.candidates, evidence_log=evidence).normalize()

    def update_with_ability(self, ability: str) -> "BeliefState":
        filtered = [c for c in self.candidates if c.ability == ability]
        evidence = self.evidence_log + [f"ability:{ability}"]
        return BeliefState(candidates=filtered or self.candidates, evidence_log=evidence).normalize()

    def entropy_norm(self) -> float:
        n = len(self.candidates)
        if n <= 1:
            return 0.0
        entropy = 0.0
        for c in self.candidates:
            p = max(c.posterior_prob, 1e-9)
            entropy -= p * math.log(p)
        return float(entropy / math.log(n))
