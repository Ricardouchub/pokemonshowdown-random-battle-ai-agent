from __future__ import annotations

from pathlib import Path
from typing import Mapping


def load_env(path: str | Path = ".env") -> Mapping[str, str]:
    """Lightweight .env loader (KEY=VALUE per line, ignores comments/blank)."""
    env_path = Path(path)
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        env[key.strip()] = val.strip()
    return env
