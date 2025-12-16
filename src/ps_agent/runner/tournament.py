from __future__ import annotations

from typing import Dict, Iterable, List

from ps_agent.runner.play_match import play_match


def tournament(seeds: Iterable[int]) -> List[Dict[str, object]]:
    """Run a batch of mock matches for quick regression checks."""
    results: List[Dict[str, object]] = []
    for seed in seeds:
        results.append(play_match(seed=seed))
    return results
