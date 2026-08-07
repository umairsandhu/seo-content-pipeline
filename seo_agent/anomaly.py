"""Anomaly & regression radar — catch problems in hours, not at the monthly report. A
deploy that broke canonicals, an indexation cliff, a traffic drop, or an AI Overview
appearing on a money keyword are all strategy-changing events. Compares the latest
snapshots to the previous ones and raises ranked alerts; `alert()` pushes them to your
channels. Reads GSC + rank history; degrades to whatever exists. Site-agnostic."""
from . import channels, history, rank


def _sum(snap, field):
    return sum((r.get(field, 0) or 0) for r in (snap or {}).get("data", []))


def detect(cfg):
    alerts = []
    ss = history.snapshots(cfg, "gsc_pages")
    if len(ss) >= 2:
        import json
        prev, curr = json.load(open(ss[-2])), json.load(open(ss[-1]))
        pc, cc = len(prev["data"]), len(curr["data"])
        if pc and cc < pc * 0.85:
            alerts.append({"sev": "high", "kind": "indexation",
                           "msg": f"indexed/ranking pages dropped {pc}→{cc} ({(cc-pc)/pc*100:.0f}%) "
                                  f"between {prev['date']} and {curr['date']} — check for a bad deploy / noindex"})
        pclicks, cclicks = _sum(prev, "clicks"), _sum(curr, "clicks")
        if pclicks and cclicks < pclicks * 0.8:
            alerts.append({"sev": "high", "kind": "traffic",
                           "msg": f"organic clicks dropped {pclicks}→{cclicks} ({(cclicks-pclicks)/pclicks*100:.0f}%)"})
    # rank movement + AI-Overview appearance on tracked keywords
    try:
        mv = rank.movement(cfg)
    except Exception:
        mv = None
    if mv:
        big = [m for m in mv.get("moved", []) if m["delta"] >= 5]
        for m in big[:10]:
            alerts.append({"sev": "med", "kind": "rank",
                           "msg": f"'{m['keyword']}' dropped {m['prev']}→{m['curr']} (+{m['delta']})"})
        for c in mv.get("features", []):
            if "ai_overview" in (c.get("gained") or []):
                alerts.append({"sev": "high", "kind": "ai_overview",
                               "msg": f"AI Overview now appears on '{c['keyword']}' — CTR will drop; "
                                      "adapt the page for citation (entity + citability)"})
    alerts.sort(key=lambda a: {"high": 0, "med": 1}.get(a["sev"], 2))
    try:  # on-page regressions between crawls (sitediff): noindex appeared, schema dropped…
        from . import sitediff
        alerts += sitediff.alerts(cfg)
    except Exception:
        pass
    return alerts


def alert(cfg):
    """Detect and push to channels if anything fired."""
    a = detect(cfg)
    if not a:
        return {"alerts": [], "sent": None}
    text = f"*🚨 SEO alerts — {cfg.get('site','')}*\n" + "\n".join(
        f"• [{x['sev']}] {x['msg']}" for x in a[:12])
    return {"alerts": a, "sent": channels.send(cfg, text, subject="SEO anomaly alert")}


def render_md(cfg, a):
    if not a:
        return f"# Anomaly radar — {cfg.get('site','site')}\n\n✅ No anomalies detected (or not enough history yet)."
    L = [f"# Anomaly radar — {cfg.get('site','site')}", f"**{len(a)} alert(s)**", ""]
    for x in a:
        L.append(f"- {'🔴' if x['sev']=='high' else '🟡'} **{x['kind']}** — {x['msg']}")
    return "\n".join(L)
