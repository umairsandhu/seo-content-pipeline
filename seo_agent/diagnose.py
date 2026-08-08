"""`diagnose` — the site-level "why is traffic down?" command. When traffic drops,
an SEO burns hours correlating suspects by hand; every instrument for that already
exists in this tool, so this wires them into ONE ranked differential diagnosis:

  1. self-inflicted?     ledger (what WE changed recently) + sitediff (what changed
                         on the site: noindex appearing, schema drops, status flips)
  2. Google update?      algo timeline overlap with the drop window
  3. zero-click erosion? zeroclick alligator + AI-Overview presence — impressions
                         holding while clicks fall means visibility moved, not rank
  4. ranking decay?      decay + rank movement (which queries/pages actually fell)
  5. still-indexed?      anomaly radar (indexation cliffs, traffic anomalies)

Output: probable causes ranked by evidence strength, each with the evidence and the
next command. Per-URL flavor: `explain <url>`. All inputs optional — it diagnoses
from whatever history exists. Stdlib only."""
import json

from . import history


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _clicks_trend(cfg):
    files = history.snapshots(cfg, "gsc_queries")
    if len(files) < 2:
        return None
    prev, curr = json.load(open(files[-2])), json.load(open(files[-1]))
    tot = lambda s: sum(r.get("clicks", 0) for r in s.get("data", []))
    pc, cc = tot(prev), tot(curr)
    if not pc:
        return None
    return {"from": prev["date"], "to": curr["date"], "prev": pc, "curr": cc,
            "pct": round((cc - pc) / pc * 100, 1)}


def run(cfg):
    causes = []
    trend = _clicks_trend(cfg)

    # 1 · self-inflicted — our own shipped changes + on-page regressions
    sd = _safe(lambda: __import__("seo_agent.sitediff", fromlist=["x"]).alerts(cfg)) or []
    high = [a for a in sd if a["sev"] == "high"]
    if high:
        causes.append({"cause": "On-page regression (possibly self-inflicted)", "confidence": "high",
                       "evidence": "; ".join(a["msg"] for a in high[:3]),
                       "next": "`sitediff` for the full diff — fix/revert, or `rollback` the ledger change"})
    changes = _safe(lambda: __import__("seo_agent.ledger", fromlist=["x"]).changes(cfg)) or []
    recent = [c for c in changes if trend and c.get("date", "") >= trend["from"]]
    if recent and trend and trend["pct"] < -5:
        causes.append({"cause": "Our own recent changes overlap the drop window", "confidence": "med",
                       "evidence": f"{len(recent)} change(s) since {trend['from']}: "
                                   + ", ".join(f"{c['type']} {c['url'].rsplit('/', 1)[-1]}" for c in recent[:4]),
                       "next": "`ledger` per-change attribution · `explain <url>` on the dropping pages"})

    # 2 · Google update overlap
    for a in (_safe(lambda: __import__("seo_agent.algo", fromlist=["x"]).attribution(cfg)) or []):
        if a.get("change_pct", 0) < -5:
            causes.append({"cause": f"Google update: {a['update']}", "confidence": "med",
                           "evidence": f"clicks {a['change_pct']:+g}% across the {a['date']} rollout",
                           "next": "`algo` for the timeline · quality/E-E-A-T review on hit clusters (`eeat`)"})

    # 3 · zero-click erosion — seen without being visited
    zc = _safe(lambda: __import__("seo_agent.zeroclick", fromlist=["x"]).alligator(cfg))
    if zc and zc["verdict"] == "opening":
        causes.append({"cause": "Zero-click erosion (visibility intact, clicks leaking)", "confidence": "high",
                       "evidence": f"impressions {zc['impressions']['pct']:+g}% vs clicks "
                                   f"{zc['clicks']['pct']:+g}% ({zc['from']} → {zc['to']}) — "
                                   "rankings likely fine; the SERP/AI answers absorb the click",
                       "next": "`zeroclick` + `citability` — become the quoted answer; track branded demand"})

    # 4 · ranking decay
    dec = _safe(lambda: __import__("seo_agent.decay", fromlist=["x"]).detect(cfg)) or {}
    dq = dec.get("queries") or []
    if dq:
        causes.append({"cause": "Ranking/traffic decay on specific queries", "confidence": "med",
                       "evidence": f"{len(dq)} decaying queries, worst: "
                                   + ", ".join(m.get("query", "?") for m in dq[:3]),
                       "next": "`decay` for the list · `refresh <url>` the pages behind them"})

    # 5 · anomaly radar (indexation cliffs etc.) — skip site-change dupes of #1
    for a in (_safe(lambda: __import__("seo_agent.anomaly", fromlist=["x"]).detect(cfg)) or []):
        if a["sev"] == "high" and a.get("kind") != "site-change":
            causes.append({"cause": f"Anomaly: {a.get('kind', 'signal')}", "confidence": "med",
                           "evidence": a["msg"], "next": "`anomaly --alert` to watch it"})

    order = {"high": 0, "med": 1, "low": 2}
    causes.sort(key=lambda c: order[c["confidence"]])
    if trend and trend["pct"] >= -2 and not causes:
        causes.append({"cause": "No drop detected", "confidence": "high",
                       "evidence": f"clicks {trend['pct']:+g}% ({trend['from']} → {trend['to']})",
                       "next": "nothing to fix — `plan` for growth work"})
    return {"trend": trend, "causes": causes}


def render_md(cfg, r=None):
    r = r or run(cfg)
    t = r.get("trend")
    L = [f"# Diagnosis — {cfg.get('site', 'site')}"]
    if t:
        L.append(f"Clicks **{t['pct']:+g}%** ({t['from']} → {t['to']}: {t['prev']:,} → {t['curr']:,})")
    L.append("")
    if not r["causes"]:
        L.append("_Not enough history to diagnose — run `gsc` on a cadence and re-crawl "
                 "(`ingest`) so the instruments have two points to compare._")
    for i, c in enumerate(r["causes"], 1):
        icon = {"high": "🔴", "med": "🟠", "low": "🟡"}[c["confidence"]]
        L += [f"## {i}. {icon} {c['cause']}  _({c['confidence']} confidence)_",
              f"- evidence: {c['evidence']}", f"- next: {c['next']}", ""]
    L.append("_Differential diagnosis from the ledger, sitediff, algo timeline, zero-click "
             "alligator, decay, and the anomaly radar — ranked by evidence. Per-URL: `explain <url>`._")
    return "\n".join(L)
