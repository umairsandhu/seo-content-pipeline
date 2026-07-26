"""Shared blackboard state — the surface the autopilot agents write and the dashboard
reads. Plain JSON under `state/` so it's inspectable, diffable, and portable. Each
agent owns one key: situation (Audit), plan (Planner), executions (Executor), report
(Analyst). Stdlib only. Site-agnostic."""
import json
from pathlib import Path

KEYS = ("situation", "plan", "executions", "report")


def _dir(cfg):
    d = Path(cfg.get("state_dir", "state"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def write(cfg, key, data):
    (_dir(cfg) / f"{key}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return data


def read(cfg, key, default=None):
    p = _dir(cfg) / f"{key}.json"
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def summary(cfg):
    return {k: read(cfg, k) for k in KEYS}
