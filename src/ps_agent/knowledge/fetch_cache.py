from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import List

from ps_agent.knowledge.online_agent import KnowledgeFetcher
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FetchConfig:
    moves: List[str]
    items: List[str]
    abilities: List[str]
    fetch_type_chart: bool
    cache_dir: Path


def _read_list_from_file(path: str | Path | None) -> List[str]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return [line.strip() for line in p.read_text().splitlines() if line.strip() and not line.startswith("#")]


def fetch_from_config(cfg: FetchConfig) -> None:
    fetcher = KnowledgeFetcher(cache_dir=cfg.cache_dir)
    for move in cfg.moves:
        fetcher.fetch_move(move)
    for item in cfg.items:
        fetcher.fetch_item(item)
    for ability in cfg.abilities:
        fetcher.fetch_ability(ability)
    if cfg.fetch_type_chart:
        fetcher.fetch_type_chart()
    logger.info(
        "knowledge_cache_filled",
        moves=len(cfg.moves),
        items=len(cfg.items),
        abilities=len(cfg.abilities),
        type_chart=cfg.fetch_type_chart,
        cache=str(cfg.cache_dir),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and cache knowledge data from PokeAPI.")
    parser.add_argument("--cache-dir", default="data/knowledge_cache", help="Cache directory for JSON files.")
    parser.add_argument("--moves", default="", help="Comma-separated move names to fetch.")
    parser.add_argument("--items", default="", help="Comma-separated item names to fetch.")
    parser.add_argument("--abilities", default="", help="Comma-separated ability names to fetch.")
    parser.add_argument("--moves-file", help="File with move names (one per line).")
    parser.add_argument("--items-file", help="File with item names (one per line).")
    parser.add_argument("--abilities-file", help="File with ability names (one per line).")
    parser.add_argument("--type-chart", action="store_true", help="Fetch the full type chart.")
    args = parser.parse_args()

    moves = [m.strip() for m in args.moves.split(",") if m.strip()]
    items = [i.strip() for i in args.items.split(",") if i.strip()]
    abilities = [a.strip() for a in args.abilities.split(",") if a.strip()]

    moves.extend(_read_list_from_file(args.moves_file))
    items.extend(_read_list_from_file(args.items_file))
    abilities.extend(_read_list_from_file(args.abilities_file))

    cfg = FetchConfig(
        moves=moves,
        items=items,
        abilities=abilities,
        fetch_type_chart=args.type_chart,
        cache_dir=Path(args.cache_dir),
    )
    fetch_from_config(cfg)


if __name__ == "__main__":
    main()
