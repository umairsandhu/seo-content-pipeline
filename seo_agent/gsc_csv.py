"""Import Google Search Console CSV exports into the pipeline's raw GSC schema —
for sites that can't grant service-account API access but can export from the GSC
UI (Performance → Export).

Handles: a single Queries CSV, a single Pages CSV, both, a directory, or the
zipped export bundle. Also handles a combined query+page export (Looker Studio /
custom), from which it aggregates a query view + a page view AND keeps the
query×page pairs (the only thing that lets us *confirm* cannibalization — which
page actually earns impressions for a query).

Every row normalizes to the schema providers.striking_distance / low_ctr and the
history store already expect:
    {query|page, clicks:int, impressions:int, ctr:float(0-1), position:float}
so once imported the whole pipeline (analyze/aio/run/decay) lights up unchanged.
"""
import csv
import io
import zipfile
from pathlib import Path

from . import history

QUERY_KEYS = {"query", "queries", "top queries", "search query", "keyword", "keywords"}
PAGE_KEYS = {"page", "pages", "top pages", "address", "url", "landing page", "top pages "}


def _num(s):
    """'1,234' / '1 234' / '' → int."""
    t = str(s or "").strip().replace(",", "").replace(" ", "").replace(" ", "")
    if not t:
        return 0
    try:
        return int(float(t))
    except ValueError:
        return 0


def _ctr(s):
    """GSC exports CTR as '3.45%'. Also accept a raw fraction ('0.0345') or a bare
    percent ('3.45'). Returns a 0–1 fraction."""
    raw = str(s or "").strip()
    had_pct = "%" in raw
    t = raw.replace("%", "").replace(",", "").strip()
    if not t:
        return 0.0
    try:
        v = float(t)
    except ValueError:
        return 0.0
    if had_pct:
        return v / 100.0
    return v / 100.0 if v > 1 else v


def _pos(s):
    t = str(s or "").strip().replace(",", "")
    try:
        return float(t)
    except ValueError:
        return 0.0


def _colmap(header):
    idx = {}
    for i, h in enumerate(header):
        hl = h.strip().lower().lstrip("﻿")
        if hl in QUERY_KEYS and "query" not in idx:
            idx["query"] = i
        elif hl in PAGE_KEYS and "page" not in idx:
            idx["page"] = i
        elif "click" in hl and "clicks" not in idx:
            idx["clicks"] = i
        elif "impress" in hl and "impressions" not in idx:
            idx["impressions"] = i
        elif hl.startswith("ctr") and "ctr" not in idx:
            idx["ctr"] = i
        elif ("position" in hl or hl == "rank" or "avg" in hl) and "position" not in idx:
            idx["position"] = i
    return idx


def parse_text(text):
    """Parse one CSV's text → list of normalized rows (each may carry query and/or page)."""
    rows = [r for r in csv.reader(io.StringIO(text)) if r]
    if not rows:
        return []
    idx = _colmap(rows[0])
    if "query" not in idx and "page" not in idx:
        return []  # not a GSC perf export
    out = []
    for r in rows[1:]:
        def cell(k):
            i = idx.get(k)
            return r[i] if i is not None and i < len(r) else ""
        row = {"clicks": _num(cell("clicks")), "impressions": _num(cell("impressions")),
               "ctr": _ctr(cell("ctr")), "position": _pos(cell("position"))}
        if "query" in idx:
            q = (cell("query") or "").strip()
            if q:
                row["query"] = q
        if "page" in idx:
            p = (cell("page") or "").strip()
            if p:
                row["page"] = p
        if row.get("query") or row.get("page"):
            out.append(row)
    return out


def _iter_csv_texts(path):
    p = Path(path)
    if p.is_dir():
        for f in sorted(p.glob("*.csv")):
            yield f.name, f.read_text(encoding="utf-8-sig", errors="ignore")
    elif p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():
                if name.lower().endswith(".csv"):
                    yield name, z.read(name).decode("utf-8-sig", errors="ignore")
    else:
        yield p.name, p.read_text(encoding="utf-8-sig", errors="ignore")


def _aggregate(rows, key):
    """Sum clicks/impressions per key; CTR from the sums; impression-weighted position."""
    acc = {}
    for r in rows:
        k = r.get(key)
        if not k:
            continue
        a = acc.setdefault(k, {key: k, "clicks": 0, "impressions": 0, "_wpos": 0.0})
        a["clicks"] += r["clicks"]
        a["impressions"] += r["impressions"]
        a["_wpos"] += r["position"] * max(r["impressions"], 1)
    out = []
    for a in acc.values():
        impr = a["impressions"] or 1
        out.append({key: a[key], "clicks": a["clicks"], "impressions": a["impressions"],
                    "ctr": (a["clicks"] / impr) if a["impressions"] else 0.0,
                    "position": round(a["_wpos"] / impr, 2)})
    return sorted(out, key=lambda r: -r["impressions"])


def load(paths):
    """Parse one or more CSV paths → {queries, pages, pairs}. Pure per-dimension
    exports are used as-is; a combined query+page export is aggregated into both
    views and its pairs are preserved."""
    if isinstance(paths, (str, Path)):
        paths = [paths]
    q_rows, p_rows, pairs = [], [], []
    for path in paths:
        for _name, text in _iter_csv_texts(path):
            for row in parse_text(text):
                has_q, has_p = "query" in row, "page" in row
                if has_q and has_p:
                    pairs.append(row)
                elif has_q:
                    q_rows.append(row)
                elif has_p:
                    p_rows.append(row)
    queries = q_rows or _aggregate(pairs, "query")
    pages = p_rows or _aggregate(pairs, "page")
    return {"queries": queries, "pages": pages, "pairs": pairs}


def import_csv(cfg, paths, date=None):
    """Load CSV(s), snapshot to history (so decay/analyze/run pick them up), and
    return the raw dict. Same-day re-imports overwrite the snapshot."""
    raw = load(paths)
    if raw["queries"]:
        history.snapshot(cfg, "gsc_queries", raw["queries"], date=date)
    if raw["pages"]:
        history.snapshot(cfg, "gsc_pages", raw["pages"], date=date)
    if raw["pairs"]:
        history.snapshot(cfg, "gsc_query_pages", raw["pairs"], date=date)
    return raw
