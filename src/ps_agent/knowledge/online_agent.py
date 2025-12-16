from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Dict, Optional

import requests

from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeFetcher:
    """Online fetcher that queries PokeAPI and stores raw JSON caches."""

    def __init__(self, base_url: str = "https://pokeapi.co/api/v2", cache_dir: str | Path = "data/knowledge_cache", requester: Optional[Callable[..., object]] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._requester = requester or requests.get

    def fetch_move(self, name: str) -> Dict[str, object]:
        return self._fetch_resource("move", name)

    def fetch_item(self, name: str) -> Dict[str, object]:
        return self._fetch_resource("item", name)

    def fetch_ability(self, name: str) -> Dict[str, object]:
        return self._fetch_resource("ability", name)

    def fetch_type_chart(self) -> Dict[str, object]:
        """Pull the full list of types and their damage relations."""
        types_url = f"{self.base_url}/type"
        resp = self._requester(types_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        type_results = {}
        for entry in data.get("results", []):
            type_name = entry["name"]
            detail_resp = self._requester(entry["url"], timeout=10)
            detail_resp.raise_for_status()
            detail = detail_resp.json()
            type_results[type_name] = {
                "double_damage_from": [t["name"] for t in detail["damage_relations"]["double_damage_from"]],
                "double_damage_to": [t["name"] for t in detail["damage_relations"]["double_damage_to"]],
                "half_damage_from": [t["name"] for t in detail["damage_relations"]["half_damage_from"]],
                "half_damage_to": [t["name"] for t in detail["damage_relations"]["half_damage_to"]],
                "no_damage_from": [t["name"] for t in detail["damage_relations"]["no_damage_from"]],
                "no_damage_to": [t["name"] for t in detail["damage_relations"]["no_damage_to"]],
            }
        cache_path = self.cache_dir / "type_chart.json"
        cache_path.write_text(json.dumps(type_results, indent=2))
        logger.info("type_chart_cached", path=str(cache_path))
        return type_results

    def _fetch_resource(self, resource: str, name: str) -> Dict[str, object]:
        candidates = self._name_variants(name)
        last_exc: Exception | None = None
        for normalized in candidates:
            url = f"{self.base_url}/{resource}/{normalized}"
            try:
                resp = self._requester(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                cache_path = self.cache_dir / f"{resource}_{normalized}.json"
                cache_path.write_text(json.dumps(data, indent=2))
                logger.info("resource_cached", resource=resource, name=normalized, path=str(cache_path))
                return data
            except Exception as exc:
                last_exc = exc
                logger.info("resource_fetch_failed", resource=resource, name=normalized, error=str(exc))
                continue
        if last_exc:
            raise last_exc
        raise RuntimeError(f"Unable to fetch {resource} {name}")

    @staticmethod
    def _name_variants(name: str) -> list[str]:
        aliases = {
            "lifeorb": "life-orb",
            "focus-sash": "focus-sash",
            "focussash": "focus-sash",
            "choiceband": "choice-band",
            "choicespecs": "choice-specs",
            "heavydutyboots": "heavy-duty-boots",
            "heavy-dutyboots": "heavy-duty-boots",
        }
        base = name.lower().replace(" ", "-").replace("_", "-")
        variants = [base]
        if base in aliases:
            variants.append(aliases[base])
        return list(dict.fromkeys(variants))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch knowledge data from PokeAPI and cache locally.")
    parser.add_argument("--move", help="Move name to fetch")
    parser.add_argument("--item", help="Item name to fetch")
    parser.add_argument("--ability", help="Ability name to fetch")
    parser.add_argument("--type-chart", action="store_true", help="Fetch type chart")
    parser.add_argument("--cache-dir", default="data/knowledge_cache", help="Cache directory")
    args = parser.parse_args()

    fetcher = KnowledgeFetcher(cache_dir=args.cache_dir)
    if args.move:
        fetcher.fetch_move(args.move)
    if args.item:
        fetcher.fetch_item(args.item)
    if args.ability:
        fetcher.fetch_ability(args.ability)
    if args.type_chart:
        fetcher.fetch_type_chart()


if __name__ == "__main__":
    main()
