from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


BOOST_ORDER: Tuple[str, ...] = (
    "atk",
    "def",
    "spa",
    "spd",
    "spe",
    "acc",
    "eva",
)


@dataclass(frozen=True)
class PokemonVolatile:
    substitute: bool = False
    confusion: bool = False
    taunt: bool = False
    torment: bool = False
    encore: bool = False
    disable: bool = False
    leech_seeded: bool = False
    perish_song_active: bool = False
    perish_song_count: int = 0

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PokemonState:
    species: str
    level: int = 100
    types: Tuple[str, ...] = field(default_factory=tuple)
    hp_fraction: float = 1.0
    status: Optional[str] = None
    is_fainted: bool = False
    boosts: Dict[str, int] = field(default_factory=lambda: {key: 0 for key in BOOST_ORDER})
    volatiles: PokemonVolatile = field(default_factory=PokemonVolatile)
    item: Optional[str] = None
    ability: Optional[str] = None
    moves_known: Tuple[str, ...] = field(default_factory=tuple)
    last_move: Optional[str] = None
    active: bool = False
    # New fields for stat awareness
    base_stats: Dict[str, int] = field(default_factory=dict)
    stats: Dict[str, int] = field(default_factory=dict) # Estimated actual stats

    def moves_known_count(self) -> int:
        return len(self.moves_known)

    def item_known(self) -> bool:
        return self.item is not None

    def ability_known(self) -> bool:
        return self.ability is not None

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["moves_known"] = list(self.moves_known)
        payload["types"] = list(self.types)
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "PokemonState":
        return cls(
            species=data["species"],
            level=int(data.get("level", 100)),
            types=tuple(data.get("types", ())),
            hp_fraction=float(data.get("hp_fraction", 1.0)),
            status=data.get("status"),
            is_fainted=bool(data.get("is_fainted", False)),
            boosts={k: int(v) for k, v in data.get("boosts", {key: 0 for key in BOOST_ORDER}).items()},
            volatiles=PokemonVolatile(**data.get("volatiles", {})),
            item=data.get("item"),
            ability=data.get("ability"),
            moves_known=tuple(data.get("moves_known", ())),
            last_move=data.get("last_move"),
            active=bool(data.get("active", False)),
            base_stats=data.get("base_stats", {}),
            stats=data.get("stats", {}),
        )

    @staticmethod
    def empty_team() -> List["PokemonState"]:
        return [PokemonState(species=f"unknown-{idx+1}") for idx in range(6)]
