from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import json

TYPE_LIST: Tuple[str, ...] = (
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
)


def load_type_chart(cache_dir: str | Path = "data/knowledge_cache") -> Dict[str, Dict[str, float]]:
    """Load type chart from cache if present, else fallback to minimal placeholder."""
    cache_path = Path(cache_dir) / "type_chart.json"
    if cache_path.exists():
        data = json.loads(cache_path.read_text())
        return _build_chart_from_cache(data)
    return _fallback_chart()


def _build_chart_from_cache(data: Dict[str, object]) -> Dict[str, Dict[str, float]]:
    chart: Dict[str, Dict[str, float]] = {t: {ot: 1.0 for ot in TYPE_LIST} for t in TYPE_LIST}
    for atk_type, relations in data.items():
        rel = relations or {}
        for t in rel.get("double_damage_to", []):
            if t in chart.get(atk_type, {}):
                chart[atk_type][t] = 2.0
        for t in rel.get("half_damage_to", []):
            if t in chart.get(atk_type, {}):
                chart[atk_type][t] = 0.5
        for t in rel.get("no_damage_to", []):
            if t in chart.get(atk_type, {}):
                chart[atk_type][t] = 0.0
    return chart


def _fallback_chart() -> Dict[str, Dict[str, float]]:
    chart: Dict[str, Dict[str, float]] = {t: {ot: 1.0 for ot in TYPE_LIST} for t in TYPE_LIST}
    chart["fire"]["grass"] = 2.0
    chart["grass"]["fire"] = 0.5
    chart["water"]["fire"] = 2.0
    chart["electric"]["water"] = 2.0
    chart["ground"]["electric"] = 2.0
    return chart
