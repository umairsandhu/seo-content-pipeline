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


def _snapshots_sorted(cfg):
    """[(date, {norm_url: row})] for every gsc_pages snapshot, oldest first."""
    import datetime
    out = []
    for p in history.snapshots(cfg, "gsc_pages"):
        d = json.load(open(p))
        try:
            dt = datetime.date.fromisoformat(d["date"])
        except Exception:
            continue
        out.append((dt, {_norm(r["page"]): r for r in d["data"]}))
    return sorted(out, key=lambda x: x[0])


def _on_or_before(snaps, target):
    prior = [s for s in snaps if s[0] <= target]
    return prior[-1] if prior else None


def _on_or_after(snaps, target):
    later = [s for s in snaps if s[0] >= target]
    return later[0] if later else None


def follow_up(cfg, horizons=(7, 28, 90)):
    """Measure each change's impact at day/week/month horizons — the follow-up loop.
    For a change on date D, compare its URL's clicks/position from the snapshot nearest D
    to the snapshot nearest D+horizon, minus a holdout of untouched pages over the same
    window. Persists to a `followups` table so learning accrues as history builds."""
    import datetime
    snaps = _snapshots_sorted(cfg)
    if len(snaps) < 2:
        return {"error": "need ≥2 GSC page snapshots over time (run `gsc` on a cadence)", "recorded": 0}
    con = _con(cfg)
    con.execute("CREATE TABLE IF NOT EXISTS followups(change_id INTEGER, horizon INTEGER, "
                "from_date TEXT, to_date TEXT, delta_clicks REAL, holdout REAL, lift REAL, "
                "delta_pos REAL, PRIMARY KEY(change_id, horizon))")
    ch_all = changes(cfg)
    changed_urls = {_norm(c["url"]) for c in ch_all}
    recorded = 0
    with con:
        for ch in ch_all:
            if ch["status"] != "applied":
                continue
            try:
                cdate = datetime.date.fromisoformat(ch["date"])
            except Exception:
                continue
            base = _on_or_before(snaps, cdate) or snaps[0]
            u = _norm(ch["url"])
            for h in horizons:
                res = _on_or_after(snaps, cdate + datetime.timedelta(days=h))
                if not res or res[0] <= base[0]:
                    continue
                b, r = base[1].get(u), res[1].get(u)
                if not (b and r):
                    continue
                dclicks = (r.get("clicks", 0) or 0) - (b.get("clicks", 0) or 0)
                hds = sorted((res[1][x].get("clicks", 0) or 0) - (base[1][x].get("clicks", 0) or 0)
                             for x in set(base[1]) & set(res[1]) if x not in changed_urls)
                hold = hds[len(hds) // 2] if hds else 0
                dpos = (r.get("position", 0) or 0) - (b.get("position", 0) or 0)
                con.execute("INSERT OR REPLACE INTO followups VALUES (?,?,?,?,?,?,?,?)",
                            (ch["id"], h, base[0].isoformat(), res[0].isoformat(),
                             dclicks, hold, dclicks - hold, round(dpos, 1)))
                recorded += 1
    con.close()
    return {"recorded": recorded, "horizons": list(horizons)}


def followups(cfg):
    """Joined change type + horizon lift rows (for the learning layer)."""
    con = _con(cfg)
    con.execute("CREATE TABLE IF NOT EXISTS followups(change_id INTEGER, horizon INTEGER, "
                "from_date TEXT, to_date TEXT, delta_clicks REAL, holdout REAL, lift REAL, delta_pos REAL, "
                "PRIMARY KEY(change_id, horizon))")
    rows = con.execute("SELECT c.type, f.horizon, f.lift, f.delta_pos, f.to_date "
                       "FROM followups f JOIN changes c ON c.id=f.change_id").fetchall()
    con.close()
    return [{"type": t, "horizon": h, "lift": lift, "delta_pos": dp, "to_date": td}
            for t, h, lift, dp, td in rows]


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
