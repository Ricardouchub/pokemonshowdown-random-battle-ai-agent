from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class Item:
    name: str
    category: str
    notes: str | None = None


def load_items(cache_dir: str | Path = "data/knowledge_cache") -> Dict[str, Item]:
    cache_path = Path(cache_dir)
    items: Dict[str, Item] = {}
    if cache_path.exists():
        for item_file in cache_path.glob("item_*.json"):
            try:
                data = json.loads(item_file.read_text())
                name = data.get("name") or item_file.stem.replace("item_", "")
                category = _categorize_item(name)
                items[name] = Item(name=name, category=category, notes=data.get("effect_entries", [{}])[0].get("short_effect"))
            except Exception:
                continue
    if not items:
        items = _fallback_items()
    return items


def _categorize_item(name: str) -> str:
    if "boots" in name:
        return "boots"
    if "choice" in name:
        return "choice"
    if "sash" in name:
        return "sash"
    if "leftovers" in name:
        return "recovery"
    if "berry" in name:
        return "berry"
    return "other"


def _fallback_items() -> Dict[str, Item]:
    return {
        "leftovers": Item(name="leftovers", category="recovery", notes="Heals each turn"),
        "choicescarf": Item(name="choicescarf", category="choice", notes="Boosts speed, locks move"),
        "heavydutyboots": Item(name="heavydutyboots", category="boots", notes="Ignores entry hazards"),
        "focussash": Item(name="focussash", category="sash", notes="Survive from full at 1 HP"),
    }
