from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class ScreensState:
    reflect_turns: int = 0
    light_screen_turns: int = 0
    aurora_veil_turns: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class SideHazards:
    stealth_rock: bool = False
    spikes_layers: int = 0
    toxic_spikes_layers: int = 0
    sticky_web: bool = False

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FieldState:
    weather: Optional[str] = None
    terrain: Optional[str] = None
    trick_room_turns_remaining: int = 0
    tailwind_turns_remaining_self: int = 0
    tailwind_turns_remaining_opp: int = 0
    screens_self: ScreensState = field(default_factory=ScreensState)
    screens_opp: ScreensState = field(default_factory=ScreensState)
    hazards_self_side: SideHazards = field(default_factory=SideHazards)
    hazards_opp_side: SideHazards = field(default_factory=SideHazards)
    field_effects: Tuple[str, ...] = field(default_factory=tuple)
    last_actions: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["field_effects"] = list(self.field_effects)
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "FieldState":
        return cls(
            weather=data.get("weather"),
            terrain=data.get("terrain"),
            trick_room_turns_remaining=int(data.get("trick_room_turns_remaining", 0)),
            tailwind_turns_remaining_self=int(data.get("tailwind_turns_remaining_self", 0)),
            tailwind_turns_remaining_opp=int(data.get("tailwind_turns_remaining_opp", 0)),
            screens_self=ScreensState(**data.get("screens_self", {})),
            screens_opp=ScreensState(**data.get("screens_opp", {})),
            hazards_self_side=SideHazards(**data.get("hazards_self_side", {})),
            hazards_opp_side=SideHazards(**data.get("hazards_opp_side", {})),
            field_effects=tuple(data.get("field_effects", ())),
            last_actions=dict(data.get("last_actions", {})),
        )
