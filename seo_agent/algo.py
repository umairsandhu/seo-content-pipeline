"""Layer 2 — Decide (goal #7). Google algorithm-update calendar + impact
attribution. On each monthly run, build a sitewide-clicks series from the GSC
page snapshots and, for every known update that falls between two snapshots,
report the before/after change. UPDATES is the maintenance point — append new
confirmed Google updates as they ship (that IS the monthly-run task in goal #7)."""
import json

from . import history

# Confirmed Google updates (date = rollout start). Extend as Google announces.
UPDATES = [
    ("2024-03-05", "March 2024 Core Update + Spam Updates"),
    ("2024-06-20", "June 2024 Spam Update"),
    ("2024-08-15", "August 2024 Core Update"),
    ("2024-11-11", "November 2024 Core Update"),
    ("2024-12-12", "December 2024 Core Update"),
    ("2024-12-19", "December 2024 Spam Update"),
    ("2025-03-13", "March 2025 Core Update"),
    ("2025-06-30", "June 2025 Core Update"),
    ("2026-03-27", "March 2026 Core Update"),
    ("2026-05-21", "May 2026 Core Update"),        # completed 2026-06-02
    ("2026-06-01", "June 2026 Spam Update"),        # verify exact date on review
    # Append new confirmed updates here each monthly run.
    # Authoritative feed: https://status.search.google.com/summary — `radar` flags staleness.
]


def series(cfg):
    """[(date, total_clicks)] from every GSC page snapshot, oldest first."""
    pts = []
    for f in history.snapshots(cfg, "gsc_pages"):
        s = json.load(open(f))
        pts.append((s["date"], sum(r.get("clicks", 0) for r in s["data"])))
    return pts


def attribution(cfg):
    pts = series(cfg)
    if len(pts) < 2:
        return None
    out = []
    for date, name in UPDATES:
        before = [c for d, c in pts if d < date]
        after = [c for d, c in pts if d >= date]
        if before and after and before[-1]:
            b, a = before[-1], after[0]
            out.append({"date": date, "update": name, "before": b, "after": a,
                        "change_pct": round((a - b) / b * 100, 1)})
    return out
