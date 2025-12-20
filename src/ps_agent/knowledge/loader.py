from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from ps_agent.knowledge.abilities_db import Ability, load_abilities
from ps_agent.knowledge.items_db import Item, load_items
from ps_agent.knowledge.moves_db import Move, load_moves
from ps_agent.knowledge.pokedex_db import PokemonSpecies, load_pokedex

@dataclass(frozen=True)
class KnowledgeBase:
    type_chart: Dict[str, Dict[str, float]]
    moves: Dict[str, Move]
    items: Dict[str, Item]
    abilities: Dict[str, Ability]
    pokedex: Dict[str, PokemonSpecies]


def load_all_knowledge(cache_dir: str | Path = "data/knowledge_cache") -> KnowledgeBase:
    return KnowledgeBase(
        type_chart=load_type_chart(cache_dir),
        moves=load_moves(cache_dir),
        items=load_items(cache_dir),
        abilities=load_abilities(cache_dir),
        pokedex=load_pokedex(cache_dir),
    )
