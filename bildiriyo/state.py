from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "state" / "state.json"
KEEP_DAYS = 180


def load() -> dict:
    if PATH.exists():
        return json.loads(PATH.read_text(encoding="utf-8"))
    return {"seen": {}, "health": {}, "heartbeat": ""}


def save(st: dict) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat()
    for src, ids in st["seen"].items():
        st["seen"][src] = {k: v for k, v in ids.items() if v >= cutoff}
    st["skipped"] = {k: v for k, v in st.get("skipped", {}).items() if v["d"] >= cutoff}
    PATH.parent.mkdir(exist_ok=True)
    PATH.write_text(json.dumps(st, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
