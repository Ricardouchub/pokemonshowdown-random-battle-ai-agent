from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional

import requests

from ps_agent.utils.env import load_env
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)

# Default to Deepseek for backward compatibility, but allow override
DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"

@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.3


class LLMClient:
    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        env = load_env()
        
        # Resolve Config
        api_key = (
            (config.api_key if config else None) 
            or os.getenv("LLM_API_KEY") 
            or os.getenv("DEEPSEEK_API_KEY") 
            or env.get("LLM_API_KEY")
            or env.get("DEEPSEEK_API_KEY")
        )
        
        base_url = (
            (config.base_url if config else None)
            or os.getenv("LLM_BASE_URL")
            or os.getenv("DEEPSEEK_API_URL") # Legacy support
            or env.get("LLM_BASE_URL")
            or DEFAULT_API_URL
        )

        model = (
            (config.model if config else None)
            or os.getenv("LLM_MODEL")
            or env.get("LLM_MODEL")
            or DEFAULT_MODEL
        )

        if not api_key:
            raise RuntimeError("LLM_API_KEY (or DEEPSEEK_API_KEY) is required for LLM-assisted policy.")
        
        self.config = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=config.temperature if config else 0.3
        )
        
        logger.info(f"LLM Client initialized with model={self.config.model} url={self.config.base_url}")

    def chat(self, messages: List[dict]) -> str:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.config.base_url, 
                headers=headers, 
                json=payload, 
                timeout=120
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            logger.debug("llm_response", content_preview=content[:200])
            return content
        except Exception as e:
            logger.error("llm_request_failed", error=str(e), url=self.config.base_url)
            raise e
