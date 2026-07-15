"""Layer 1 — Observe. File-based time-series store: snapshot each GSC / rank /
backlink / trend pull to history/<kind>/<YYYY-MM-DD>.json and diff run-over-run.

This is the unlock for goals #3 (rank movement) and #5 (SERP tracking): the rest
of the pipeline was point-in-time; history makes it longitudinal. No DB — one
JSON file per snapshot, "latest" is the last by filename sort."""
import datetime
import json
from pathlib import Path


def _dir(cfg, kind):
    d = Path(cfg.get("history_dir", "history")) / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


def snapshot(cfg, kind, data, date=None):
    """Persist a dated snapshot; same-day re-runs overwrite. Returns the path."""
    date = date or datetime.date.today().isoformat()
    p = _dir(cfg, kind) / f"{date}.json"
    p.write_text(json.dumps({"date": date, "kind": kind, "data": data},
                            ensure_ascii=False, indent=1))
    return p


def snapshots(cfg, kind):
    return sorted(_dir(cfg, kind).glob("*.json"))


def latest(cfg, kind):
    ss = snapshots(cfg, kind)
    return json.load(open(ss[-1])) if ss else None


def previous(cfg, kind):
    ss = snapshots(cfg, kind)
    return json.load(open(ss[-2])) if len(ss) >= 2 else None


def diff_rows(prev, curr, key, metric):
    """Compare two lists of dict rows on `key`, tracking change in `metric`.
    Returns {new, gone, moved:[{key, prev, curr, delta}]}. For rank/position a
    NEGATIVE delta means improved (moved up); for clicks/impressions positive is
    better — callers filter on the sign they care about."""
    pv = {r[key]: r for r in (prev or [])}
    cv = {r[key]: r for r in (curr or [])}
    new = [cv[k] for k in cv if k not in pv]
    gone = [pv[k] for k in pv if k not in cv]
    moved = []
    for k in cv:
        a, b = pv.get(k, {}).get(metric), cv[k].get(metric)
        if k in pv and a is not None and b is not None and b != a:
            moved.append({key: k, "prev": round(a, 2), "curr": round(b, 2),
                          "delta": round(b - a, 2)})
    return {"new": new, "gone": gone, "moved": moved}
