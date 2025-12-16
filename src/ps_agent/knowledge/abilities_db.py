from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class Ability:
    name: str
    notes: str | None = None


def load_abilities(cache_dir: str | Path = "data/knowledge_cache") -> Dict[str, Ability]:
    cache_path = Path(cache_dir)
    abilities: Dict[str, Ability] = {}
    if cache_path.exists():
        for ability_file in cache_path.glob("ability_*.json"):
            try:
                data = json.loads(ability_file.read_text())
                name = data.get("name") or ability_file.stem.replace("ability_", "")
                notes = ""
                entries = data.get("effect_entries") or []
                if entries:
                    notes = entries[0].get("short_effect", "")
                abilities[name] = Ability(name=name, notes=notes)
            except Exception:
                continue
    if not abilities:
        abilities = _fallback_abilities()
    return abilities


def _fallback_abilities() -> Dict[str, Ability]:
    return {
        "levitate": Ability(name="levitate", notes="Immune to ground moves"),
        "intimidate": Ability(name="intimidate", notes="Lowers foe attack on switch-in"),
        "regenerator": Ability(name="regenerator", notes="Heals on switch out"),
    }
