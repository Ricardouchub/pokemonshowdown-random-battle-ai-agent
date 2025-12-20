
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

@dataclass(frozen=True)
class PokemonSpecies:
    name: str
    types: List[str]
    base_stats: Dict[str, int]
    abilities: List[str]
    weight_kg: float
    
    @property
    def base_speed(self) -> int:
        return self.base_stats.get("spe", 0)

    @property
    def base_attack(self) -> int:
        return self.base_stats.get("atk", 0)

    @property
    def base_defense(self) -> int:
        return self.base_stats.get("def", 0)
        
    @property
    def base_spa(self) -> int:
        return self.base_stats.get("spa", 0)
        
    @property
    def base_spd(self) -> int:
        return self.base_stats.get("spd", 0)

    @property
    def base_hp(self) -> int:
        return self.base_stats.get("hp", 0)


def load_pokedex(cache_dir: str | Path) -> Dict[str, PokemonSpecies]:
    path = Path(cache_dir) / "pokedex.json"
    if not path.exists():
        return {}
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    pokedex = {}
    for name, info in data.items():
        pokedex[name] = PokemonSpecies(
            name=name,
            types=info.get("types", []),
            base_stats=info.get("base_stats", {}),
            abilities=info.get("abilities", []),
            weight_kg=info.get("weight_kg", 0.0)
        )
    return pokedex
