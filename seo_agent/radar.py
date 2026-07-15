"""Build-loop radar — the sensor for the continuous-improvement loop (see
BUILDLOOP.md). It turns "Google changed something" into a concrete tool task by
watching machine-followable signals and flagging when the tool's own knowledge
(the `algo.py` UPDATES list) has gone stale relative to them.

Authoritative feed: Google's Search Status Dashboard (Crawling/Indexing/Ranking/
Serving). Non-machine sources to review by hand are listed in BUILDLOOP.md. Best
effort — degrades cleanly if the dashboard shape changes."""
import datetime
import json
import urllib.request

from . import algo

DASHBOARD_JSON = "https://status.search.google.com/incidents.json"
DASHBOARD_URL = "https://status.search.google.com/summary"


def dashboard_incidents(timeout=30):
    try:
        req = urllib.request.Request(DASHBOARD_JSON, headers={"User-Agent": "seo-content-pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except Exception as e:
        return {"error": str(e), "review": DASHBOARD_URL, "incidents": []}
    rows = data if isinstance(data, list) else data.get("incidents", [])
    out = []
    for it in rows[:20]:
        out.append({"name": it.get("external_desc") or it.get("name"),
                    "begin": it.get("begin"), "end": it.get("end"),
                    "products": [p.get("title") for p in (it.get("affected_products") or [])]})
    return {"review": DASHBOARD_URL, "incidents": out}


def staleness():
    dates = [d for d, _ in algo.UPDATES]
    latest = max(dates) if dates else None
    days = (datetime.date.today() - datetime.date.fromisoformat(latest)).days if latest else None
    return {"latest_tracked_update": latest, "days_since": days, "stale": bool(days and days > 45)}


def check():
    s = staleness()
    return {"staleness": s, "dashboard": dashboard_incidents(),
            "action": ("⚠ Review status.search.google.com + the BUILDLOOP.md sources and append any "
                       "new confirmed Google update to seo_agent/algo.py UPDATES."
                       if s["stale"] else "algo.UPDATES current — monthly review still recommended.")}
