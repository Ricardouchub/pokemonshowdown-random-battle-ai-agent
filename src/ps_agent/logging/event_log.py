from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional

from ps_agent.state.battle_state import BattleState, SCHEMA_VERSION
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


class EventLogger:
    """Append-only JSONL logger for match turns."""

    def __init__(self, log_path: Path, schema_version: str = SCHEMA_VERSION) -> None:
        self.log_path = log_path
        self.schema_version = schema_version
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_turn(
        self,
        state: BattleState,
        chosen_action: str,
        legal_actions: Iterable[str],
        reasons: Optional[Dict[str, float]] = None,
        top_actions: Optional[Iterable[Dict[str, object]]] = None,
        extras: Optional[Dict[str, object]] = None,
    ) -> None:
        legal_list = list(legal_actions)
        payload: Dict[str, object] = {
            "schema_version": self.schema_version,
            "timestamp": datetime.utcnow().isoformat(),
            "turn": state.turn,
            "battle_id": state.battle_id,
            "state_summary": state.summary(),
            "legal_actions_count": len(legal_list),
            "legal_actions": legal_list,
            "chosen_action": chosen_action,
            "reasons": reasons or {},
            "top_actions": list(top_actions or []),
        }
        payload.update(extras or {})
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=self._fallback) + "\n")
        logger.debug("turn_logged", **payload)

    @staticmethod
    def _fallback(value: object) -> object:
        if hasattr(value, "__dict__"):
            return asdict(value)
        return str(value)
