from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class Move:
    name: str
    move_type: str
    category: str
    power: int | None
    accuracy: int | None
    priority: int = 0
    is_status: bool = False


def load_moves(cache_dir: str | Path = "data/knowledge_cache") -> Dict[str, Move]:
    cache_path = Path(cache_dir)
    moves: Dict[str, Move] = {}
    if cache_path.exists():
        for move_file in cache_path.glob("move_*.json"):
            try:
                data = json.loads(move_file.read_text())
                name = data.get("name") or move_file.stem.replace("move_", "")
                moves[name] = Move(
                    name=name,
                    move_type=data.get("type", "normal"),
                    category=data.get("damage_class", {}).get("name", data.get("category", "status")),
                    power=data.get("power"),
                    accuracy=data.get("accuracy"),
                    priority=data.get("priority", 0),
                    is_status=(data.get("damage_class", {}).get("name", "") == "status")
                    or data.get("category") == "status",
                )
            except Exception:
                continue
    if not moves:
        moves = _fallback_moves()
    return moves


def _fallback_moves() -> Dict[str, Move]:
    return {
        "tackle": Move(name="tackle", move_type="normal", category="physical", power=40, accuracy=100),
        "ember": Move(name="ember", move_type="fire", category="special", power=40, accuracy=100),
        "thunder-wave": Move(
            name="thunder-wave",
            move_type="electric",
            category="status",
            power=None,
            accuracy=90,
            is_status=True,
        ),
    }
