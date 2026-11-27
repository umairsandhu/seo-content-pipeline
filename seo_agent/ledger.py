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

from . import history, providers, store


def _con(cfg):
    con = store._con(cfg)  # same seo.db
    con.execute("CREATE TABLE IF NOT EXISTS changes("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, url TEXT, type TEXT, "
                "detail TEXT, commit_ref TEXT, status TEXT)")
    for col, typ in (("before_state", "TEXT"), ("verified", "INTEGER DEFAULT -1")):
        try:  # W3: before-state (for rollback) + post-apply verification flag; in-place migration
            con.execute(f"ALTER TABLE changes ADD COLUMN {col} {typ}")
        except Exception:
            pass
    return con


def record(cfg, url, ctype, detail="", commit_ref="", date=None, status="applied", before=None):
    """Log a change; returns its new id. `before` (dict of the pre-change title/meta/content)
    is stored so the change can be rolled back later (W3)."""
    con = _con(cfg)
    with con:
        cur = con.execute("INSERT INTO changes(date,url,type,detail,commit_ref,status,before_state) "
                          "VALUES (?,?,?,?,?,?,?)",
                          (date or datetime.date.today().isoformat(), url, ctype, detail, commit_ref,
                           status, json.dumps(before) if before else None))
        cid = cur.lastrowid
    con.close()
    return cid


def set_verified(cfg, change_id, ok):
    con = _con(cfg)
    with con:
        con.execute("UPDATE changes SET verified=? WHERE id=?", (1 if ok else 0, change_id))
    con.close()


_CHG_COLS = ["id", "date", "url", "type", "detail", "commit_ref", "status", "before_state", "verified"]


def changes(cfg, url=None):
    con = _con(cfg)
    where, args = (" WHERE url=?", (url,)) if url else ("", ())
    rows = con.execute("SELECT id,date,url,type,detail,commit_ref,status,before_state,verified "
                       "FROM changes" + where + " ORDER BY date DESC, id DESC", args).fetchall()
    con.close()
    out = []
    for r in rows:
        d = dict(zip(_CHG_COLS, r))
        d["before_state"] = json.loads(d["before_state"]) if d.get("before_state") else None
        out.append(d)
    return out


def get_change(cfg, change_id):
    return next((c for c in changes(cfg) if c["id"] == change_id), None)


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


def _daily(cfg, start, end):
    """Per-day Search Console rows, {norm_url: {date: (clicks, impressions, position)}}, plus the last
    date that has data. None when no API is connected (CSV sites keep the snapshot comparison)."""
    prop, cred = cfg.get("gsc_property"), cfg.get("gsc_credentials")
    svc = providers.gsc_service(cred) if prop and cred else None
    if not svc:
        return None
    rows, offset, size = [], 0, 25000
    while True:
        page = providers.gsc_query(svc, prop, start.isoformat(), end.isoformat(), ("page", "date"),
                                   row_limit=size, start_row=offset)
        rows += page
        offset += len(page)
        if len(page) < size:
            break
    pages, last = {}, None
    for r in rows:
        day = datetime.date.fromisoformat(r["date"])
        last = max(last or day, day)
        days = pages.setdefault(_norm(r["page"]), {})
        c, i, p = days.get(day, (0, 0, 0))
        n = r.get("impressions", 0)  # two raw URLs can share one normalised URL
        days[day] = (c + r.get("clicks", 0), i + n,
                     (p * i + r.get("position", 0) * n) / (i + n) if i + n else 0)
    first = min((d for days in pages.values() for d in days), default=None)
    return {"pages": pages, "first": first, "last": last}


def _sum(days, start, length):
    """(clicks, impressions, impression-weighted position) over `length` days from `start`."""
    got = [days[d] for d in (start + datetime.timedelta(days=n) for n in range(length)) if d in days]
    imps = sum(g[1] for g in got)
    return (sum(g[0] for g in got), imps,
            sum(g[2] * g[1] for g in got) / imps if imps else 0)


def _compare(daily, url, changed, cdate, length):
    """Equal windows either side of `cdate` (the change day itself is in neither). None when either
    window is outside the data, or the page was never shown in both: that is no evidence, not zero."""
    before = cdate - datetime.timedelta(days=length)
    after = cdate + datetime.timedelta(days=1)
    if not daily["last"] or before < daily["first"] or after + datetime.timedelta(days=length - 1) > daily["last"]:
        return None
    days = daily["pages"].get(url, {})
    b, a = _sum(days, before, length), _sum(days, after, length)
    if not (b[1] or a[1]):
        return None
    hds = []
    for u, other in daily["pages"].items():
        if u in changed:
            continue
        ob, oa = _sum(other, before, length), _sum(other, after, length)
        if ob[1] or oa[1]:
            hds.append(oa[0] - ob[0])
    return {"from": before, "to": after + datetime.timedelta(days=length - 1), "before": b, "after": a,
            "hold": sorted(hds)[len(hds) // 2] if hds else 0, "holdout_n": len(hds),
            "dpos": a[2] - b[2] if b[1] and a[1] else 0}


def _daily_for(cfg, applied, longest):
    dates = []
    for c in applied:
        try:
            dates.append(datetime.date.fromisoformat(c["date"]))
        except Exception:
            pass
    if not dates:
        return None
    today = datetime.date.today()
    return _daily(cfg, min(dates) - datetime.timedelta(days=longest), today)


def _ensure_followups(con):
    """One home for the followups DDL (was declared twice — ARCHITECTURE-V2 §7.6) +
    in-place migration for the W2 statistical columns."""
    con.execute("CREATE TABLE IF NOT EXISTS followups(change_id INTEGER, horizon INTEGER, "
                "from_date TEXT, to_date TEXT, delta_clicks REAL, holdout REAL, lift REAL, "
                "delta_pos REAL, PRIMARY KEY(change_id, horizon))")
    for col, typ in (("confounded", "INTEGER DEFAULT 0"), ("holdout_n", "INTEGER DEFAULT 0")):
        try:
            con.execute(f"ALTER TABLE followups ADD COLUMN {col} {typ}")
        except Exception:
            pass  # column already exists


def _confounded(cdate, window=5):
    """A change shipped within ±window days of a known Google update can't be cleanly
    attributed — the algorithm moved the ground under the measurement (W2/G2)."""
    import datetime
    try:
        from . import algo
        for d, _name in algo.UPDATES:
            if abs((cdate - datetime.date.fromisoformat(d)).days) <= window:
                return 1
    except Exception:
        pass
    return 0


def follow_up(cfg, horizons=(7, 28, 90)):
    """Measure each change's impact at day/week/month horizons — the follow-up loop.
    With the Search Console API connected, compare the `horizon` days before the change with the
    `horizon` days after it (`_compare`) and rebuild `followups`. Without it, compare its URL's
    clicks/position from the snapshot nearest D to the snapshot nearest D+horizon, minus the MEDIAN DELTA of a holdout of untouched
    pages over the same window (diff-in-diff: seasonality/weekday/algorithm effects common
    to the whole site cancel out). Changes within ±5d of a Google update are flagged
    `confounded` and excluded from learning aggregates. Persists to `followups`."""
    ch_all = changes(cfg)
    applied = [c for c in ch_all if c["status"] == "applied"]
    if cfg.get("gsc_property") and cfg.get("gsc_credentials"):
        return _follow_up_daily(cfg, applied, horizons)
    snaps = _snapshots_sorted(cfg)
    if len(snaps) < 2:
        return {"error": "need ≥2 GSC page snapshots over time (run `gsc` on a cadence)", "recorded": 0}
    con = _con(cfg)
    _ensure_followups(con)
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
                con.execute("INSERT OR REPLACE INTO followups VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (ch["id"], h, base[0].isoformat(), res[0].isoformat(),
                             dclicks, hold, dclicks - hold, round(dpos, 1),
                             _confounded(cdate), len(hds)))
                recorded += 1
    con.close()
    return {"recorded": recorded, "horizons": list(horizons)}


def _follow_up_daily(cfg, applied, horizons):
    try:
        daily = _daily_for(cfg, applied, max(horizons))
    except Exception as e:  # never fall back to the rolling snapshots: they measure something else
        return {"error": f"Search Console daily pull failed: {type(e).__name__}", "recorded": 0}
    if not daily:
        return {"error": "no daily Search Console data (nothing applied, or the API client is missing)",
                "recorded": 0}
    changed = {_norm(c["url"]) for c in applied}
    out = []
    for ch in applied:
        try:
            cdate = datetime.date.fromisoformat(ch["date"])
        except Exception:
            continue
        for h in horizons:
            m = _compare(daily, _norm(ch["url"]), changed, cdate, h)
            if not m:
                continue
            dclicks = m["after"][0] - m["before"][0]
            out.append((ch["id"], h, m["from"].isoformat(), m["to"].isoformat(), dclicks, m["hold"],
                        dclicks - m["hold"], round(m["dpos"], 1), _confounded(cdate), m["holdout_n"]))
    con = _con(cfg)
    _ensure_followups(con)
    with con:
        con.execute("DELETE FROM followups")  # rows from the snapshot comparison are not comparable
        con.executemany("INSERT OR REPLACE INTO followups VALUES (?,?,?,?,?,?,?,?,?,?)", out)
    con.close()
    return {"recorded": len(out), "horizons": list(horizons), "data_through": str(daily["last"])}


def followups(cfg):
    """Joined change type + horizon lift rows (for the learning layer), with the W2
    trust columns: confound flag + holdout size."""
    con = _con(cfg)
    _ensure_followups(con)
    rows = con.execute("SELECT c.type, f.horizon, f.lift, f.delta_pos, f.to_date, "
                       "f.confounded, f.holdout_n "
                       "FROM followups f JOIN changes c ON c.id=f.change_id").fetchall()
    con.close()
    return [{"type": t, "horizon": h, "lift": lift, "delta_pos": dp, "to_date": td,
             "confounded": bool(cf), "holdout_n": hn or 0}
            for t, h, lift, dp, td, cf, hn in rows]


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
    if cfg.get("gsc_property") and cfg.get("gsc_credentials"):
        return _attribution_daily(cfg, window)
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


def _attribution_daily(cfg, window):
    """`window` days either side of each URL's latest change; URLs without a full window yet are left out."""
    applied = [c for c in changes(cfg) if c["status"] == "applied"]
    try:
        daily = _daily_for(cfg, applied, window)
    except Exception as e:
        return {"error": f"Search Console daily pull failed: {type(e).__name__}"}
    if not daily:
        return {"error": "no daily Search Console data (nothing applied, or the API client is missing)"}
    latest = {}
    for c in applied:
        u = _norm(c["url"])
        latest[u] = max(latest.get(u, ""), c["date"])
    rows = []
    for u, d in latest.items():
        try:
            m = _compare(daily, u, set(latest), datetime.date.fromisoformat(d), window)
        except ValueError:
            continue
        if not m:
            continue
        dclicks = m["after"][0] - m["before"][0]
        rows.append({"url": u, "before_clicks": m["before"][0], "after_clicks": m["after"][0],
                     "delta_clicks": dclicks, "holdout_adjusted_lift": dclicks - m["hold"],
                     "before_pos": round(m["before"][2], 1), "after_pos": round(m["after"][2], 1),
                     "delta_pos": round(m["dpos"], 1), "holdout_median_delta": m["hold"]})
    rows.sort(key=lambda r: -r["holdout_adjusted_lift"])
    holds = sorted(r["holdout_median_delta"] for r in rows)
    return {"window": f"{window} days before vs {window} days after each change (data through {daily['last']})",
            "holdout_median_delta": holds[len(holds) // 2] if holds else 0,
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
