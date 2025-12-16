from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class SetHypothesis:
    moves: Tuple[str, ...]
    item: str
    ability: str
    prior_prob: float
    posterior_prob: float


def load_randbats_priors() -> Dict[str, List[SetHypothesis]]:
    """Placeholder priors for Random Battle sets."""
    return {
        "pikachu": [
            SetHypothesis(
                moves=("thunderbolt", "grass-knot", "voltswitch", "surf"),
                item="lightball",
                ability="static",
                prior_prob=1.0,
                posterior_prob=1.0,
            )
        ]
    }
