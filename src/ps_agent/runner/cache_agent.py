from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable, List

from ps_agent.knowledge.fetch_cache import fetch_from_config, FetchConfig
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


DEFAULT_MOVES = [
    "ember",
    "tackle",
    "thunder-wave",
    "earthquake",
    "surf",
    "flamethrower",
    "ice-beam",
    "shadow-ball",
    "psychic",
    "close-combat",
]

DEFAULT_ITEMS = [
    "leftovers",
    "choice-scarf",
    "choice-band",
    "choice-specs",
    "heavy-duty-boots",
    "focus-sash",
    "life-orb",
]

DEFAULT_ABILITIES = [
    "levitate",
    "intimidate",
    "regenerator",
    "prankster",
    "flash-fire",
    "magic-guard",
    "unaware",
]


def auto_fill_cache(
    cache_dir: str | Path = "data/knowledge_cache",
    moves: Iterable[str] | None = None,
    items: Iterable[str] | None = None,
    abilities: Iterable[str] | None = None,
    sample_size: int = 20,
) -> None:
    """Automatically populate cache with a curated and sampled list of knowledge entries."""
    moves_list: List[str] = list(moves) if moves else []
    items_list: List[str] = list(items) if items else []
    abilities_list: List[str] = list(abilities) if abilities else []

    # Sample extra items to enrich coverage
    rng = random.Random(42)
    if len(moves_list) < sample_size:
        moves_list.extend(rng.sample(DEFAULT_MOVES, k=min(sample_size, len(DEFAULT_MOVES))))
    if len(items_list) < sample_size:
        items_list.extend(rng.sample(DEFAULT_ITEMS, k=min(sample_size, len(DEFAULT_ITEMS))))
    if len(abilities_list) < sample_size:
        abilities_list.extend(rng.sample(DEFAULT_ABILITIES, k=min(sample_size, len(DEFAULT_ABILITIES))))

    cfg = FetchConfig(
        moves=list(dict.fromkeys(moves_list)),  # dedupe preserving order
        items=list(dict.fromkeys(items_list)),
        abilities=list(dict.fromkeys(abilities_list)),
        fetch_type_chart=True,
        cache_dir=Path(cache_dir),
    )
    fetch_from_config(cfg)
    logger.info("auto_cache_populated", cache=str(cache_dir), moves=len(cfg.moves), items=len(cfg.items), abilities=len(cfg.abilities))


def main() -> None:
    auto_fill_cache()


if __name__ == "__main__":
    main()
