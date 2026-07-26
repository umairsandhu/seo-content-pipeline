"""Queryable results store (SQLite) alongside the file-based `history/`. Additive
and portable — `history.snapshot()` keeps writing JSON; this mirrors metric points
into a single `seo.db` so trends, deltas and share-of-voice are *queryable* instead
of requiring a diff of two JSON files. Stdlib only (sqlite3). Site-agnostic.

    record(cfg, "rank", rows, key_field="query", value_fields=["position"])
    series(cfg, "rank", "best pizza|position")          # time series for one key
    deltas(cfg, "rank", "position")                     # every key: latest vs previous
"""
import datetime
import json
import sqlite3
from pathlib import Path


def _con(cfg):
    con = sqlite3.connect(str(Path(cfg.get("store_path", "seo.db"))))
    con.execute("CREATE TABLE IF NOT EXISTS metric("
                "ts TEXT, kind TEXT, entity TEXT, key TEXT, value REAL, meta TEXT)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_metric ON metric(kind, entity, key, ts)")
    return con


def record(cfg, kind, rows, key_field, value_fields, entity="", date=None):
    """Store one metric point per (row, value_field). `entity` scopes a namespace
    (e.g. a competitor domain or an AI engine)."""
    date = date or datetime.date.today().isoformat()
    con = _con(cfg)
    with con:
        con.execute("DELETE FROM metric WHERE ts=? AND kind=? AND entity=?", (date, kind, entity))
        for r in rows:
            k = str(r.get(key_field, "")).strip()
            if not k:
                continue
            for vf in value_fields:
                v = r.get(vf)
                if v is None:
                    continue
                try:
                    con.execute("INSERT INTO metric VALUES (?,?,?,?,?,?)",
                                (date, kind, entity, f"{k}|{vf}", float(v), json.dumps(r)[:1800]))
                except (TypeError, ValueError):
                    pass
    con.close()
    return date


def series(cfg, kind, key, entity=""):
    con = _con(cfg)
    rows = con.execute("SELECT ts,value FROM metric WHERE kind=? AND key=? AND entity=? ORDER BY ts",
                       (kind, key, entity)).fetchall()
    con.close()
    return [{"ts": t, "value": v} for t, v in rows]


def deltas(cfg, kind, value_field, entity=""):
    """For every key of this kind+value_field, latest value and change vs the
    previous snapshot date. Negative delta = improved for rank/position."""
    con = _con(cfg)
    keys = [r[0] for r in con.execute(
        "SELECT DISTINCT key FROM metric WHERE kind=? AND entity=? AND key LIKE ?",
        (kind, entity, f"%|{value_field}")).fetchall()]
    out = []
    for key in keys:
        pts = con.execute("SELECT ts,value FROM metric WHERE kind=? AND key=? AND entity=? "
                          "ORDER BY ts DESC LIMIT 2", (kind, key, entity)).fetchall()
        if not pts:
            continue
        cur = pts[0][1]
        prev = pts[1][1] if len(pts) > 1 else None
        out.append({"key": key.rsplit("|", 1)[0], "current": cur,
                    "previous": prev, "delta": (cur - prev) if prev is not None else None})
    con.close()
    return out


def snapshot_dates(cfg, kind, entity=""):
    con = _con(cfg)
    ds = [r[0] for r in con.execute(
        "SELECT DISTINCT ts FROM metric WHERE kind=? AND entity=? ORDER BY ts", (kind, entity)).fetchall()]
    con.close()
    return ds
