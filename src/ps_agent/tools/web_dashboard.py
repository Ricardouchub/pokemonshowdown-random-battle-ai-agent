import argparse
import json
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, Optional

app = FastAPI(title="Pokemon Showdown Agent Dashboard")

# Global config via closure or simple file-level
LOG_DIR = Path("artifacts/logs/live")

@app.get("/api/state")
async def get_state() -> Dict[str, object]:
    """Fetch the latest state from the most recent log file."""
    if not LOG_DIR.exists():
        return {"error": "Log directory not found", "dir": str(LOG_DIR)}
    
    # Find most recently modified battle log file
    log_files = list(LOG_DIR.glob("battle-*.log"))
    if not log_files:
        return {"error": "No active battle logs found", "waiting": True}
    
    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    
    # Read last valid JSON line
    last_line = ""
    try:
        with latest_log.open("r", encoding="utf-8") as f:
            # Efficiently read last line? For small logs readlines is fine.
            # For robustness, read all and take last valid json
            lines = f.readlines()
            for line in reversed(lines):
                line = line.strip()
                if not line: continue
                try:
                    json.loads(line)
                    last_line = line
                    break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        return {"error": f"Failed to read log: {str(e)}"}

    if not last_line:
        return {"error": "Log file is empty", "file": latest_log.name}

    return json.loads(last_line)

# Serve static files (HTML/JS)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--log-dir", type=str, default="artifacts/logs/live")
    args = parser.parse_args()
    
    global LOG_DIR
    LOG_DIR = Path(args.log_dir)
    
    print(f"🚀 Dashboard running at http://localhost:{args.port}")
    print(f"📂 Monitoring logs in: {LOG_DIR}")
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="error")

if __name__ == "__main__":
    main()
