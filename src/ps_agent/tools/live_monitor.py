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


def _draw_bar(percent: int, width: int = 10) -> str:
    filled = int(width * percent / 100)
    bar = "=" * filled + " " * (width - filled)
    return f"[{bar}] {percent}%"


def _fmt_mon(info: Dict[str, object] | str) -> str:
    if isinstance(info, str):
        return info  # Fallback for old logs
    species = info.get("species", "Unknown")
    hp = info.get("hp_percent", 100)
    status = info.get("status")
    boosts = info.get("boosts", {})
    
    parts = [f"{species:<12}"]
    if status:
        parts.append(f"({status})")
    if boosts:
        b_str = " ".join(f"{k}{'+' if v>0 else ''}{v}" for k, v in boosts.items())
        parts.append(f"[{b_str}]")
    
    parts.append(_draw_bar(hp))
    return " ".join(parts)


def print_entry(entry: Dict[str, object]) -> None:
    turn = entry.get("turn")
    battle_id = entry.get("battle_id")
    summary = entry.get("state_summary", {})
    chosen = entry.get("chosen_action")
    reasons = entry.get("reasons", {})
    top = entry.get("top_actions", [])[:3]
    
    # Header
    print("\n" + "=" * 60)
    print(f" BATTLE: {battle_id} | TURN: {turn}")
    print("-" * 60)
    
    # State Table
    my_active = summary.get("my_active") or summary.get("self_active")
    opp_active = summary.get("opponent_active") or summary.get("opp_active")
    
    print(f"🤖 YOU: {_fmt_mon(my_active)}")
    print(f"👤 OPP: {_fmt_mon(opp_active)}")
    
    # Decision Highlight
    print("-" * 60)
    print(f"👉 ACTION: {chosen}")
    llm_reason = reasons.get('llm_reason')
    if llm_reason:
        print(f"🧠 LOGIC : \"{llm_reason}\"")
    
    # Stats row
    breakdown = top[0].get("breakdown", {}) if top else {}
    if breakdown:
        mat = round(breakdown.get('material', 0), 2)
        pos = round(breakdown.get('position', 0), 2)
        risk = round(breakdown.get('risk', 0), 2) or round(breakdown.get('lookahead_risk', 0), 2)
        print(f"📊 STATS : Material={mat} | Position={pos} | Risk={risk} | FinalScore={round(reasons.get('score', 0), 3)}")

    # Alternatives
    print("-" * 60)
    print("Alternatives considered:")
    for rank, item in enumerate(top[1:], start=2):
        bd = item.get("breakdown", {})
        rsk = round(bd.get('risk', 0) or bd.get('lookahead_risk', 0), 2)
        print(f"  #{rank}: {item.get('action'):<20} (Score: {round(item.get('score', 0), 3)}, Risk: {rsk})")

    if "updates" in entry:
        print(f"📚 LEARNING: {entry['updates']}")
    print("=" * 60 + "\n")


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
