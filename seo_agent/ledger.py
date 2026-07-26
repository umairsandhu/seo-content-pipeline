"""Causal change ledger — the moat. Logs every change the tool makes (URL, what, when,
commit) into `seo.db`, then does what no human practitioner does rigorously:
change-level attribution. For each changed URL it compares before→after GSC metrics
against a **holdout** of untouched, similar pages over the same window — isolating the
change's effect from the sitewide trend. Over time this becomes a proprietary
"what actually works on THIS site" dataset that feeds the plan's prioritization.

Reads GSC page snapshots from `history/` (populated by `gsc` / `gsc --csv`); needs ≥2
snapshots straddling a change to attribute it. Stdlib (sqlite3). Site-agnostic."""
import datetime
import json
from urllib.parse import urlparse

from . import history, store


def _con(cfg):
    con = store._con(cfg)  # same seo.db
    con.execute("CREATE TABLE IF NOT EXISTS changes("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, url TEXT, type TEXT, "
                "detail TEXT, commit_ref TEXT, status TEXT)")
    return con


def record(cfg, url, ctype, detail="", commit_ref="", date=None, status="applied"):
    con = _con(cfg)
    with con:
        con.execute("INSERT INTO changes(date,url,type,detail,commit_ref,status) VALUES (?,?,?,?,?,?)",
                    (date or datetime.date.today().isoformat(), url, ctype, detail, commit_ref, status))
    con.close()


def changes(cfg, url=None):
    con = _con(cfg)
    where, args = (" WHERE url=?", (url,)) if url else ("", ())
    rows = con.execute("SELECT id,date,url,type,detail,commit_ref,status FROM changes" + where
                       + " ORDER BY date DESC, id DESC", args).fetchall()
    con.close()
    cols = ["id", "date", "url", "type", "detail", "commit_ref", "status"]
    return [dict(zip(cols, r)) for r in rows]


def _norm(u):
    return (u or "").split("#")[0].split("?")[0].rstrip("/")


def _section(u):
    parts = [p for p in urlparse(u).path.split("/") if p]
    return "/" + (parts[0] if parts else "")


def _two_snapshots(cfg):
    ss = history.snapshots(cfg, "gsc_pages")
    if len(ss) < 2:
        return None, None
    prev = json.load(open(ss[-2])); curr = json.load(open(ss[-1]))
    return ({_norm(r["page"]): r for r in prev["data"]}, prev["date"]), \
           ({_norm(r["page"]): r for r in curr["data"]}, curr["date"])


def attribution(cfg, window=28):
    """Before→after clicks/position per changed URL vs a holdout of untouched pages."""
    prev, curr = _two_snapshots(cfg)
    if not prev:
        return {"error": "need ≥2 GSC page snapshots straddling the change (run `gsc` on a cadence)"}
    (pmap, pdate), (cmap, cdate) = prev, curr
    changed = {_norm(c["url"]) for c in changes(cfg) if c["status"] == "applied"}
    # holdout: pages present in both snapshots that we did NOT change → sitewide baseline
    holdout_deltas = []
    for u in set(pmap) & set(cmap):
        if u in changed:
            continue
        holdout_deltas.append((cmap[u].get("clicks", 0) or 0) - (pmap[u].get("clicks", 0) or 0))
    holdout_deltas.sort()
    base = (holdout_deltas[len(holdout_deltas) // 2] if holdout_deltas else 0)  # median sitewide Δ
    rows = []
    for u in changed:
        p, c = pmap.get(u), cmap.get(u)
        if not (p and c):
            continue
        dclicks = (c.get("clicks", 0) or 0) - (p.get("clicks", 0) or 0)
        dpos = (c.get("position", 0) or 0) - (p.get("position", 0) or 0)
        rows.append({"url": u, "before_clicks": p.get("clicks"), "after_clicks": c.get("clicks"),
                     "delta_clicks": dclicks, "holdout_adjusted_lift": dclicks - base,
                     "before_pos": round(p.get("position", 0), 1), "after_pos": round(c.get("position", 0), 1),
                     "delta_pos": round(dpos, 1)})
    rows.sort(key=lambda r: -r["holdout_adjusted_lift"])
    return {"window": f"{pdate} → {cdate}", "holdout_median_delta": base,
            "changed_pages_measured": len(rows), "rows": rows}


def render_md(cfg, mode="both"):
    L = [f"# Change ledger & attribution — {cfg.get('site','site')}", ""]
    ch = changes(cfg)
    L += [f"## Change log ({len(ch)})"]
    if ch:
        L += ["| date | url | type | detail |", "|---|---|---|---|"]
        for c in ch[:25]:
            L.append(f"| {c['date']} | {(_norm(c['url']) or '').rsplit('/',1)[-1]} | {c['type']} | {(c['detail'] or '')[:40]} |")
    else:
        L.append("_No changes logged yet. `control` / `pr` write here automatically._")
    att = attribution(cfg)
    L += ["", "## Causal attribution (vs holdout)"]
    if att.get("error"):
        L.append(f"_{att['error']}_")
    else:
        L.append(f"window {att['window']} · sitewide baseline Δclicks/page: {att['holdout_median_delta']}")
        if att["rows"]:
            L += ["", "| page | before | after | holdout-adj lift | pos Δ |", "|---|--:|--:|--:|--:|"]
            for r in att["rows"][:20]:
                L.append(f"| {r['url'].rsplit('/',1)[-1]} | {r['before_clicks']} | {r['after_clicks']} | "
                         f"**{r['holdout_adjusted_lift']:+}** | {r['delta_pos']:+} |")
        else:
            L.append("_Changes logged, but not yet in two straddling GSC snapshots — attribution builds over time._")
    return "\n".join(L)
