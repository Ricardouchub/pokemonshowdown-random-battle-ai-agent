from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional

import requests

from ps_agent.utils.env import load_env
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


@dataclass
class DeepseekConfig:
    api_key: str
    model: str = "deepseek-chat"
    temperature: float = 0.3


class DeepseekClient:
    def __init__(self, config: Optional[DeepseekConfig] = None) -> None:
        env = load_env()
        api_key = (config.api_key if config else None) or os.getenv("DEEPSEEK_API_KEY") or env.get(
            "DEEPSEEK_API_KEY"
        )
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for LLM-assisted policy.")
        cfg = config or DeepseekConfig(api_key=api_key)
        self.config = cfg

    def chat(self, messages: List[dict]) -> str:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=40)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        logger.debug("deepseek_response", content_preview=content[:200])
        return content
