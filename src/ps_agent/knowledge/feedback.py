from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class KnowledgeFeedbackStore:
    """Append-only store for LLM-suggested knowledge updates."""

    def __init__(self, path: str | Path = "artifacts/knowledge_feedback.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, entry: Dict[str, object]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
