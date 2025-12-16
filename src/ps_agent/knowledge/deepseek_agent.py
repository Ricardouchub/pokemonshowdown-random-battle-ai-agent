from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import requests

from ps_agent.utils.env import load_env
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


@dataclass
class DeepseekConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    cache_dir: Path = Path("data/knowledge_cache")


class DeepseekKnowledgeAgent:
    """Calls Deepseek API to generate structured knowledge for Pokémon, items, and abilities."""

    def __init__(self, config: DeepseekConfig, requester: Optional[requests.sessions.Session] = None):
        self.config = config
        self.requester = requester or requests.Session()
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_pokemon(self, name: str) -> Dict[str, object]:
        prompt = (
            "Produce concise JSON for a Pokémon species with keys: "
            '"species","types","roles","notable_moves","abilities","common_items","summary". '
            "All values in lower-case where applicable. Keep arrays short (<=5). "
            f'Species: "{name}". Respond ONLY with JSON.'
        )
        return self._query_and_cache(
            prompt, cache_file=self.config.cache_dir / f"llm_pokemon_{self._slug(name)}.json"
        )

    def fetch_item(self, name: str) -> Dict[str, object]:
        prompt = (
            "Produce concise JSON for a competitive item with keys: "
            '"item","category","summary","typical_users". '
            f'Item: "{name}". Respond ONLY with JSON.'
        )
        return self._query_and_cache(
            prompt, cache_file=self.config.cache_dir / f"llm_item_{self._slug(name)}.json"
        )

    def fetch_ability(self, name: str) -> Dict[str, object]:
        prompt = (
            "Produce concise JSON for an ability with keys: "
            '"ability","effect","synergies","notes". '
            f'Ability: "{name}". Respond ONLY with JSON.'
        )
        return self._query_and_cache(
            prompt, cache_file=self.config.cache_dir / f"llm_ability_{self._slug(name)}.json"
        )

    def _query_and_cache(self, prompt: str, cache_file: Path) -> Dict[str, object]:
        payload = self._call_chat(prompt)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = {"raw": payload}
        cache_file.write_text(json.dumps(data, indent=2))
        logger.info("deepseek_cached", path=str(cache_file))
        return data

    def _call_chat(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": "You are a competitive Pokémon expert. Output JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        resp = self.requester.post(DEEPSEEK_API_URL, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return content

    @staticmethod
    def _slug(name: str) -> str:
        return name.lower().replace(" ", "-").replace("_", "-")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch knowledge using Deepseek API and cache as JSON.")
    parser.add_argument("--pokemon", nargs="*", default=[], help="List of Pokémon species to fetch.")
    parser.add_argument("--items", nargs="*", default=[], help="List of items to fetch.")
    parser.add_argument("--abilities", nargs="*", default=[], help="List of abilities to fetch.")
    parser.add_argument("--cache-dir", default="data/knowledge_cache", help="Cache directory.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Deepseek model id.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    env_file = load_env()
    api_key = os.getenv("DEEPSEEK_API_KEY") or env_file.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY env var is required to call Deepseek API.")
    agent = DeepseekKnowledgeAgent(
        DeepseekConfig(api_key=api_key, model=args.model, cache_dir=Path(args.cache_dir))
    )
    for name in args.pokemon:
        agent.fetch_pokemon(name)
    for item in args.items:
        agent.fetch_item(item)
    for ability in args.abilities:
        agent.fetch_ability(ability)


if __name__ == "__main__":
    main()
