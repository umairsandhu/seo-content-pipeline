"""Zero-click measurement — the KPI layer for a web where impressions rise while
clicks fall (~58% of Google searches end without a click; roughly 360 of every
1,000 send someone to the open web). Traffic is a bad primary KPI; this module
measures what the zero-click playbook says to measure instead:

  · the ALLIGATOR — is the impressions-vs-clicks gap opening on YOUR site?
  · BRANDED SEARCH — the demand-creation proxy: people who saw you somewhere
    (social, AI answers, a podcast, a Slack thread) and later searched your name.
    Analytics calls that "organic"; branded volume is the honest leading indicator.
  · CORRELATION, not attribution — per snapshot period: what we shipped (ledger)
    next to branded demand, visibility, AI citations, and AI referrals. "Did we
    do more of X, and did Y go up?" — patterns over time, not single-touch proof.

Four layers, mapped to our data: Reach (impressions) → Interest (branded search,
AI citations) → Visits (clicks, AI referrals) → Outcomes (GA4 conversions).
Pure-local (GSC history + ledger + aivis + GA4, all optional). Stdlib only."""
import json
import re

from . import history


def _brand_terms(cfg):
    """Tokens that mark a branded query: brand name words + the domain stem."""
    from urllib.parse import urlparse
    terms = set()
    name = ((cfg.get("brand") or {}).get("name") or "").lower()
    for w in re.findall(r"[a-z0-9]+", name):
        if len(w) > 2 and w not in ("the", "inc", "llc", "site"):
            terms.add(w)
    dom = urlparse(cfg.get("site") or "").netloc.replace("www.", "").split(".")[0]
    if len(dom) > 2:
        terms.add(dom.lower())
    return terms


def _is_branded(query, terms):
    q = query.lower()
    return any(t in q for t in terms)


def _series(cfg, kind="gsc_queries"):
    out = []
    for p in history.snapshots(cfg, kind):
        try:
            out.append(json.load(open(p)))
        except Exception:
            continue
    return out


def alligator(cfg):
    """Impressions trend vs clicks trend between the first and last GSC snapshots.
    Opening jaws = visibility up, clicks flat/down → you're being SEEN without being
    VISITED: exactly when zero-click assets + citability matter most."""
    snaps = _series(cfg)
    if len(snaps) < 2:
        return None
    tot = lambda s, k: sum(r.get(k, 0) for r in s.get("data", []))
    first, last = snaps[0], snaps[-1]
    fi, fc = tot(first, "impressions"), tot(first, "clicks")
    li, lc = tot(last, "impressions"), tot(last, "clicks")
    if not (fi and fc):
        return None
    di, dc = (li - fi) / fi, (lc - fc) / fc
    verdict = ("opening" if di > 0.05 and dc < di - 0.05
               else "closing" if dc > di + 0.05 else "tracking")
    return {"from": first["date"], "to": last["date"],
            "impressions": {"from": fi, "to": li, "pct": round(di * 100, 1)},
            "clicks": {"from": fc, "to": lc, "pct": round(dc * 100, 1)},
            "verdict": verdict}


def branded_trend(cfg):
    """Branded vs non-branded demand per snapshot — branded growth is the closest
    measurable proxy for 'our off-site presence is creating demand'."""
    terms = _brand_terms(cfg)
    if not terms:
        return None
    rows = []
    for s in _series(cfg):
        b_i = b_c = n_i = n_c = 0
        for r in s.get("data", []):
            if _is_branded(r.get("query", ""), terms):
                b_i += r.get("impressions", 0)
                b_c += r.get("clicks", 0)
            else:
                n_i += r.get("impressions", 0)
                n_c += r.get("clicks", 0)
        rows.append({"date": s["date"], "branded_impressions": b_i, "branded_clicks": b_c,
                     "nonbranded_impressions": n_i, "nonbranded_clicks": n_c})
    delta = None
    if len(rows) >= 2 and rows[0]["branded_impressions"]:
        delta = round((rows[-1]["branded_impressions"] - rows[0]["branded_impressions"])
                      / rows[0]["branded_impressions"] * 100, 1)
    return {"terms": sorted(terms), "series": rows, "branded_impressions_pct": delta}


def correlation(cfg):
    """The monthly-review table: per GSC snapshot, what we SHIPPED since the previous
    one (ledger) next to what MOVED (branded demand, clicks). Correlation, not
    attribution — the honest way to read organic + brand work."""
    bt = branded_trend(cfg)
    if not bt or len(bt["series"]) < 2:
        return None
    changes = []
    try:
        from . import ledger
        changes = ledger.changes(cfg)
    except Exception:
        pass
    rows = []
    prev_date = None
    for s in bt["series"]:
        shipped = sum(1 for c in changes
                      if (prev_date is None or c.get("date", "") > prev_date)
                      and c.get("date", "") <= s["date"]) if changes else 0
        rows.append({"date": s["date"], "shipped_changes": shipped,
                     "branded_impressions": s["branded_impressions"],
                     "branded_clicks": s["branded_clicks"],
                     "nonbranded_clicks": s["nonbranded_clicks"]})
        prev_date = s["date"]
    return rows


def report(cfg):
    r = {"alligator": alligator(cfg), "branded": branded_trend(cfg),
         "correlation": correlation(cfg)}
    try:
        from . import history as _h
        av = _h.latest(cfg, "aivis")
        if av and av.get("data"):
            rows = av["data"]
            r["ai_citations"] = {"prompts": len(rows),
                                 "mentioned": sum(1 for x in rows if x.get("mentioned"))}
    except Exception:
        pass
    try:
        from . import ga4
        ai = ga4.ai_referrals(cfg)
        if not ai.get("error"):
            r["ai_referrals"] = ai["total"]
    except Exception:
        pass
    return r


def render_md(cfg, r=None):
    r = r or report(cfg)
    L = [f"# Zero-click reality — {cfg.get('site', 'site')}",
         "_~58% of searches end without a click; visibility ≠ visits. Measure the layers, "
         "not just traffic._", ""]
    a = r.get("alligator")
    if a:
        icon = {"opening": "🐊 OPENING", "closing": "✅ closing", "tracking": "➖ tracking together"}[a["verdict"]]
        L += [f"## The alligator ({a['from']} → {a['to']}): {icon}",
              f"- impressions {a['impressions']['pct']:+g}% · clicks {a['clicks']['pct']:+g}%"]
        if a["verdict"] == "opening":
            L.append("- you're increasingly SEEN without being VISITED → double down on "
                     "`citability` (be the quoted answer), branded demand, and zero-click assets "
                     "(`repurpose <url>`) — and judge content by the layers below, not clicks")
        L.append("")
    b = r.get("branded")
    if b and b["series"]:
        L += [f"## Branded demand (queries containing: {', '.join(b['terms'])})",
              "| snapshot | branded impr | branded clicks | non-branded clicks |", "|---|--:|--:|--:|"]
        for row in b["series"][-6:]:
            L.append(f"| {row['date']} | {row['branded_impressions']:,} | {row['branded_clicks']:,} "
                     f"| {row['nonbranded_clicks']:,} |")
        if b.get("branded_impressions_pct") is not None:
            L.append(f"\n**Branded impressions {b['branded_impressions_pct']:+g}%** across the window — "
                     "the closest proxy for demand your off-site presence is CREATING.")
        L.append("")
    c = r.get("correlation")
    if c and len(c) >= 2:
        L += ["## Correlation view — what we shipped vs what moved (not attribution)",
              "| period ending | changes shipped | branded impr | branded clicks |", "|---|--:|--:|--:|"]
        for row in c[-6:]:
            L.append(f"| {row['date']} | {row['shipped_changes']} | {row['branded_impressions']:,} "
                     f"| {row['branded_clicks']:,} |")
        L.append("\n_Read it like the monthly review: did we do more of X, and did Y go up 2–4 "
                 "weeks later? Patterns over time beat single-touch attribution (which under-counts "
                 "dark social ~100% and lets platforms overclaim 2–10×)._")
        L.append("")
    if r.get("ai_citations"):
        ac = r["ai_citations"]
        L.append(f"**AI answers:** mentioned in {ac['mentioned']}/{ac['prompts']} tracked prompts (`aivis`)"
                 + (f" · **{r.get('ai_referrals', 0):,} AI-referred sessions** (`ga4`)" if "ai_referrals" in r else ""))
    if not (a or (b and b["series"])):
        L.append("_Needs ≥2 GSC snapshots (`gsc` / `gsc --csv` on a cadence). The layers light up "
                 "as history accrues._")
    L.append("\n_Layers: Reach (impressions) → Interest (branded search, AI citations) → Visits "
             "(clicks, AI referrals) → Outcomes (`ga4`). Traffic is a secondary metric._")
    return "\n".join(L)
