from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live dashboard for agent reasoning/logs.")
    parser.add_argument(
        "--log-dir",
        default="artifacts/logs/live",
        help="Directory containing live battle logs (.log JSONL).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Seconds between polling the log directory.",
    )
    return parser.parse_args()


def print_entry(entry: Dict[str, object]) -> None:
    turn = entry.get("turn")
    battle_id = entry.get("battle_id")
    summary = entry.get("state_summary", {})
    chosen = entry.get("chosen_action")
    reasons = entry.get("reasons", {})
    top = entry.get("top_actions", [])[:3]
    print("=" * 80)
    print(f"Battle {battle_id} | Turn {turn}")
    print(f"State  : self={summary.get('self_active')} vs opp={summary.get('opp_active')}")
    print(f"Chosen : {chosen} | Score={reasons.get('score')} | Reason={reasons.get('llm_reason', '')}")
    legal_count = entry.get("legal_actions_count")
    print(f"Legal  : {legal_count} actions")
    print("Top-K  :")
    for rank, item in enumerate(top, start=1):
        breakdown = item.get("breakdown", {})
        print(
            f"  #{rank}: {item.get('action')} | score={round(item.get('score', 0.0), 3)} "
            f"material={breakdown.get('material')} position={breakdown.get('position')} "
            f"risk={breakdown.get('risk')}"
        )
    if "updates" in entry:
        print(f"Knowledge updates: {entry['updates']}")


def tail_logs(log_dir: Path, poll_interval: float) -> None:
    offsets: Dict[Path, int] = {}
    print(f"Monitoring {log_dir} ... ctrl+c to exit")
    while True:
        for log_file in sorted(log_dir.glob("*.log")):
            size = log_file.stat().st_size
            offset = offsets.get(log_file, 0)
            if size < offset:
                offset = 0
            if size == offset:
                continue
            with log_file.open("r", encoding="utf-8") as f:
                f.seek(offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    print_entry(entry)
                offsets[log_file] = f.tell()
        time.sleep(poll_interval)


def main() -> None:
    args = parse_args()
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        tail_logs(log_dir, args.poll_interval)
    except KeyboardInterrupt:
        print("\nExiting live monitor.")


if __name__ == "__main__":
    main()
