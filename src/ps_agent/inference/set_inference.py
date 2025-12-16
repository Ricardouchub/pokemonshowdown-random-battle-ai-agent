from __future__ import annotations

from typing import Dict

from ps_agent.inference.belief_state import BeliefState
from ps_agent.knowledge.randbats_sets import SetHypothesis, load_randbats_priors


def init_belief(species: str, priors: Dict[str, list[SetHypothesis]] | None = None) -> BeliefState:
    priors = priors or load_randbats_priors()
    candidates = priors.get(species, [])
    if not candidates:
        default = SetHypothesis(moves=(), item="unknown", ability="unknown", prior_prob=1.0, posterior_prob=1.0)
        candidates = [default]
    return BeliefState(candidates=candidates).normalize()
