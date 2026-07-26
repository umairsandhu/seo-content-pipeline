"""Conversational diagnosis — "why did /x drop?" Instead of correlation theater, it
correlates a page's decline against the tool's OWN change ledger, the GSC trend, and
the Google-update timeline, then answers with ranked, evidence-backed causes.

This is only possible because the tool logs every change it makes (see ledger). Reads
GSC page snapshots from `history/`; degrades to what's available. Site-agnostic."""
from urllib.parse import urlparse

from . import algo, history, ledger


def _norm(u):
    return (u or "").split("#")[0].split("?")[0].rstrip("/")


def _page_series(cfg, url):
    u = _norm(url)
    series = []
    for p in history.snapshots(cfg, "gsc_pages"):
        import json
        d = json.load(open(p))
        row = next((r for r in d["data"] if _norm(r["page"]) == u), None)
        if row:
            series.append({"date": d["date"], "clicks": row.get("clicks", 0),
                           "position": round(row.get("position", 0), 1)})
    return series


def explain(cfg, url):
    series = _page_series(cfg, url)
    hist = ledger.changes(cfg, _norm(url))
    causes = []
    trend = None
    if len(series) >= 2:
        first, last = series[0], series[-1]
        dclicks = last["clicks"] - first["clicks"]
        dpos = last["position"] - first["position"]
        trend = {"from": first, "to": last, "delta_clicks": dclicks, "delta_pos": round(dpos, 1)}
        if dpos > 1.5:
            causes.append((0.5, f"rankings slipped {first['position']}→{last['position']} "
                                f"(pos +{dpos:.1f}) between {first['date']} and {last['date']}"))
        # a self-inflicted change near the window?
        for c in hist:
            if first["date"] <= c["date"] <= last["date"]:
                causes.append((0.8, f"WE changed this page on {c['date']} ({c['type']}: {c['detail']}) — "
                                    "the most likely and checkable cause; compare before/after in the ledger"))
        # a confirmed Google update in the window?
        for date, name in algo.UPDATES:
            if first["date"] <= date <= last["date"]:
                causes.append((0.6, f"Google **{name}** rolled out {date}, inside the decline window"))
    else:
        causes.append((0.3, "not enough GSC history for this URL — run `gsc` on a cadence to enable diagnosis"))
    if not hist:
        causes.append((0.2, "no logged changes to this page — the cause is external (SERP/algo/competitor), "
                            "not something we did"))
    causes.sort(key=lambda c: -c[0])
    return {"url": _norm(url), "trend": trend, "changes": hist, "causes": [c[1] for c in causes]}


def render_md(cfg, r):
    L = [f"# Why did {r['url']} change?", ""]
    t = r["trend"]
    if t:
        L.append(f"**Trend:** {t['from']['clicks']}→{t['to']['clicks']} clicks, "
                 f"position {t['from']['position']}→{t['to']['position']} "
                 f"({t['from']['date']} → {t['to']['date']}).")
    L += ["", "## Most likely causes (ranked, with evidence)"]
    for i, c in enumerate(r["causes"], 1):
        L.append(f"{i}. {c}")
    if r["changes"]:
        L += ["", f"## Our logged changes to this page ({len(r['changes'])})"]
        for c in r["changes"][:8]:
            L.append(f"- {c['date']} — {c['type']}: {c['detail']} ({c['commit_ref'] or 'no commit'})")
    L.append("\n_Evidence-based, not correlation theater: the change ledger makes self-inflicted causes "
             "checkable; the rest is GSC trend + confirmed Google updates._")
    return "\n".join(L)
