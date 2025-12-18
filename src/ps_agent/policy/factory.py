from __future__ import annotations

from ps_agent.policy.baseline_rules import BaselinePolicy
from ps_agent.policy.llm_policy import LLMPolicy


def create_policy(name: str) -> BaselinePolicy | LLMPolicy:
    key = name.lower()
    if key == "baseline":
        return BaselinePolicy()
    if key in {"llm", "deepseek"}:
        return LLMPolicy()
    raise ValueError(f"Unknown policy '{name}'")
