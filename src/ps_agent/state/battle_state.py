from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field as data_field, replace
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .field_state import FieldState
from .pokemon_state import PokemonState


SCHEMA_VERSION = "0.1.0"


@dataclass(frozen=True)
class PlayerState:
    name: str
    rating: Optional[float] = None
    active_slot: int = 0
    team: List[PokemonState] = data_field(default_factory=PokemonState.empty_team)

    def active_pokemon(self) -> PokemonState:
        if self.team and 0 <= self.active_slot < len(self.team):
            return self.team[self.active_slot]
        return PokemonState(species="unknown", is_fainted=True)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "rating": self.rating,
            "active_slot": self.active_slot,
            "team": [p.to_dict() for p in self.team],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "PlayerState":
        team_payload = data.get("team", PokemonState.empty_team())
        team = [PokemonState.from_dict(p) if isinstance(p, dict) else p for p in team_payload]
        return cls(
            name=data["name"],
            rating=data.get("rating"),
            active_slot=int(data.get("active_slot", 0)),
            team=team,
        )


@dataclass(frozen=True)
class BattleState:
    battle_id: str
    gen: int
    format: str
    turn: int
    timestamp: str
    player_self: PlayerState
    player_opponent: PlayerState
    field: FieldState = data_field(default_factory=FieldState)
    history: List[str] = data_field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, object]:
        return {
            "battle_id": self.battle_id,
            "gen": self.gen,
            "format": self.format,
            "turn": self.turn,
            "timestamp": self.timestamp,
            "player_self": self.player_self.to_dict(),
            "player_opponent": self.player_opponent.to_dict(),
            "field": self.field.to_dict(),
            "history": self.history,
            "schema_version": self.schema_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    def summary(self) -> Dict[str, object]:
        return {
            "turn": self.turn,
            "self_active": self.player_self.active_pokemon().species,
            "opp_active": self.player_opponent.active_pokemon().species,
            "weather": self.field.weather,
            "terrain": self.field.terrain,
            "recent_history": self.history[-5:],
        }

    def with_turn(self, turn: int, timestamp: Optional[str] = None) -> "BattleState":
        new_ts = timestamp or datetime.now(timezone.utc).isoformat()
        return replace(self, turn=turn, timestamp=new_ts)

    @classmethod
    def new(
        cls,
        battle_id: str,
        gen: int,
        format: str,
        player_self: PlayerState,
        player_opponent: PlayerState,
        turn: int = 0,
        timestamp: Optional[str] = None,
    ) -> "BattleState":
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        return cls(
            battle_id=battle_id,
            gen=gen,
            format=format,
            turn=turn,
            timestamp=ts,
            player_self=player_self,
            player_opponent=player_opponent,
            history=[],
        )

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "BattleState":
        return cls(
            battle_id=data["battle_id"],
            gen=int(data.get("gen", 9)),
            format=data.get("format", "randombattle"),
            turn=int(data.get("turn", 0)),
            timestamp=data.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            player_self=PlayerState.from_dict(data["player_self"]),
            player_opponent=PlayerState.from_dict(data["player_opponent"]),
            field=FieldState.from_dict(data.get("field", {})),
            history=list(data.get("history", [])),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )
