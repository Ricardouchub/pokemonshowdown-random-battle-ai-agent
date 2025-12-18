from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ps_agent.knowledge.deepseek_agent import DeepseekConfig, DeepseekKnowledgeAgent
from ps_agent.utils.env import load_env
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


class OfflineLearner:
    def __init__(self, agent: DeepseekKnowledgeAgent, feedback_path: str | Path) -> None:
        self.agent = agent
        self.feedback_path = Path(feedback_path)
        self.processed_dir = self.feedback_path.parent / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def process_pending_feedback(self) -> None:
        if not self.feedback_path.exists():
            logger.info("no_feedback_found", path=str(self.feedback_path))
            return

        logger.info("processing_feedback", path=str(self.feedback_path))
        entries = self._load_entries()
        
        updates_count = 0
        for entry in entries:
            updates = entry.get("updates", [])
            for update in updates:
                if self._apply_update(update):
                    updates_count += 1

        self._archive_log()
        logger.info("learning_complete", updates_processed=updates_count)

    def _load_entries(self) -> List[Dict[str, Any]]:
        entries = []
        with self.feedback_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("skipping_invalid_json_line", line=line[:100])
        return entries

    def _apply_update(self, update: Dict[str, Any]) -> bool:
        """
        Interprets a knowledge update request and calls the agent to fetch/cache it.
        Expected format: {"type": "pokemon|item|ability", "data": "name_or_object"}
        """
        u_type = update.get("type", "").lower()
        data = update.get("data")

        # Extract name from data (it might be a string or a dict with 'name')
        name = None
        if isinstance(data, str):
            name = data
        elif isinstance(data, dict):
            name = data.get("name") or data.get("species") or data.get("item") or data.get("ability")

        if not name:
            logger.warning("update_missing_name", update=update)
            return False

        name = str(name).strip()
        
        try:
            if u_type in ("pokemon", "species", "mon"):
                self.agent.fetch_pokemon(name)
            elif u_type in ("item", "held_item"):
                self.agent.fetch_item(name)
            elif u_type in ("ability",):
                self.agent.fetch_ability(name)
            else:
                logger.debug("unknown_update_type", type=u_type, name=name)
                return False
            return True
        except Exception as exc:
            logger.error("update_failed", name=name, error=str(exc))
            return False

    def _archive_log(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"feedback_{timestamp}.jsonl"
        dest = self.processed_dir / archive_name
        shutil.move(str(self.feedback_path), str(dest))
        logger.info("feedback_archived", destination=str(dest))


def main() -> None:
    parser = argparse.ArgumentParser(description="Process offline feedback logs to update knowledge base.")
    parser.add_argument("--feedback-file", default="artifacts/knowledge_feedback.jsonl", help="Path to feedback log.")
    parser.add_argument("--cache-dir", default="data/knowledge_cache", help="Directory for knowledge base.")
    args = parser.parse_args()

    env_file = load_env()
    api_key = os.getenv("DEEPSEEK_API_KEY") or env_file.get("DEEPSEEK_API_KEY")
    
    if not api_key:
        logger.error("api_key_missing", msg="DEEPSEEK_API_KEY is required for learning.")
        return

    config = DeepseekConfig(api_key=api_key, cache_dir=Path(args.cache_dir))
    agent = DeepseekKnowledgeAgent(config)
    learner = OfflineLearner(agent, args.feedback_file)
    learner.process_pending_feedback()


if __name__ == "__main__":
    main()
