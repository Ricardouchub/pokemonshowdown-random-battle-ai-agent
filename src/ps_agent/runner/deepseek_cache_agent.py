from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, List

import requests

from ps_agent.knowledge.deepseek_agent import DeepseekConfig, DeepseekKnowledgeAgent
from ps_agent.knowledge.online_agent import KnowledgeFetcher
from ps_agent.utils.env import load_env
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


def _fetch_all_names(base_url: str, resource: str, limit: int) -> List[str]:
    url = f"{base_url}/{resource}?limit={limit}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return [r["name"] for r in data.get("results", [])]


def _chunked(seq: Iterable[str], size: int) -> List[List[str]]:
    seq = list(seq)
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def auto_deepseek_cache(
    api_key: str,
    cache_dir: str | Path = "data/knowledge_cache",
    base_url: str = "https://pokeapi.co/api/v2",
    pokemon_limit: int = 200,
    item_limit: int = 150,
    ability_limit: int = 150,
    batch_size: int = 20,
) -> None:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Use PokeAPI to enumerate names
    fetcher = KnowledgeFetcher(cache_dir=cache_dir, base_url=base_url)
    pokemon_names = _fetch_all_names(base_url, "pokemon", pokemon_limit)
    item_names = _fetch_all_names(base_url, "item", item_limit)
    ability_names = _fetch_all_names(base_url, "ability", ability_limit)

    logger.info(
        "auto_deepseek_start",
        pokemon=len(pokemon_names),
        items=len(item_names),
        abilities=len(ability_names),
    )

    agent = DeepseekKnowledgeAgent(
        DeepseekConfig(api_key=api_key, cache_dir=cache_dir, model="deepseek-chat")
    )

    for chunk in _chunked(pokemon_names, batch_size):
        for name in chunk:
            agent.fetch_pokemon(name)
    for chunk in _chunked(item_names, batch_size):
        for name in chunk:
            agent.fetch_item(name)
    for chunk in _chunked(ability_names, batch_size):
        for name in chunk:
            agent.fetch_ability(name)

    logger.info("auto_deepseek_done", cache=str(cache_dir))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automatically populate knowledge cache via Deepseek and PokeAPI enumeration."
    )
    parser.add_argument("--cache-dir", default="data/knowledge_cache", help="Cache directory.")
    parser.add_argument("--base-url", default="https://pokeapi.co/api/v2", help="PokeAPI base URL.")
    parser.add_argument("--pokemon-limit", type=int, default=200, help="How many pokemon to fetch.")
    parser.add_argument("--item-limit", type=int, default=150, help="How many items to fetch.")
    parser.add_argument("--ability-limit", type=int, default=150, help="How many abilities to fetch.")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for iteration.")
    args = parser.parse_args()
    env_file = load_env()
    api_key = os.getenv("DEEPSEEK_API_KEY") or env_file.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY env var is required.")
    auto_deepseek_cache(
        api_key=api_key,
        cache_dir=args.cache_dir,
        base_url=args.base_url,
        pokemon_limit=args.pokemon_limit,
        item_limit=args.item_limit,
        ability_limit=args.ability_limit,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
