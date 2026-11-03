"""Brand SERP check (network, paid, opt-in) — what Google shows for the site's own name.

The Site Doctor audits our pages; nothing looked at the RESULT for the brand. superx.pk,
3 Nov 2026: a search for superx.pk showed no sitelinks, "More results from superx.pk", and
snippets that quoted raw embed code and the footer; DataForSEO showed that for "superx" the site
is not in the top 10 at all. This check reads Google's top 10 for the brand terms and reports,
per term: our best rank, whether our result carries sitelinks, who holds the top 3, our snippet.

Terms (config `brand.serp_terms` replaces the list): the brand name, the bare domain, and
brand + market word (`brand.market`, else `dataforseo.location_name` when it is not the default
"United States"). One DataForSEO live request per term (the Live endpoint takes one task per request), depth 10 (one billing unit each).
The estimate is checked against `dataforseo.max_cost` (default USD 0.05) BEFORE the call; the
cost the API reports is printed after. Reuses providers._dfs_post (DATAFORSEO_LOGIN/PASSWORD)."""
import datetime
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from . import ingest, providers

UNIT_COST = 0.002      # USD per SERP of up to 10 results, live advanced (docs.dataforseo.com)
MAX_COST = 0.05
BOILER = re.compile(r"privacy policy|terms of (?:use|service)|all rights reserved|cookie policy|"
                    r"disclaimer|\blegal\b|©", re.I)
LEVERS = ("one clear primary nav in the server HTML; a distinct <title> for each main section; "
          "WebSite schema with name and alternateName; the same anchor text for a section on every "
          "internal link; and time and authority. Sitelinks are Google's choice: no markup forces them")


def host_of(cfg):
    h = urlparse(cfg.get("site") or "").netloc.lower()
    return h[4:] if h.startswith("www.") else h


def terms(cfg):
    b = cfg.get("brand") or {}
    if b.get("serp_terms"):
        return list(dict.fromkeys(str(x).strip() for x in b["serp_terms"] if str(x).strip()))
    name = (b.get("name") or "").strip()
    out = [name.lower()] if name and name != "Site" else []
    if host_of(cfg):
        out.append(host_of(cfg))
    loc = (cfg.get("dataforseo") or {}).get("location_name")
    market = b.get("market") or (loc if loc and loc != "United States" else "")
    if out and market:
        out.append(f"{out[0]} {market.lower()}")
    return list(dict.fromkeys(out))


def estimate(cfg, n):
    return round(n * (cfg.get("dataforseo") or {}).get("serp_cost", UNIT_COST), 4)


def _ours(domain, host):
    d = (domain or "").lower()
    return bool(host) and (d == host or d.endswith("." + host))


def _is_sitelink_item(it):
    return "sitelink" in (it.get("type") or "").replace("_", "").lower()


def analyse(term, items, host):
    """One term's report from a SERP's `items` (organic items carry sitelinks in `links`; a
    separate sitelink-type item is handled too)."""
    organic = [i for i in items if i.get("type") == "organic"][:10]
    mine = [i for i in organic if _ours(i.get("domain") or urlparse(i.get("url") or "").netloc, host)]
    best = min(mine, key=lambda i: i.get("rank_group") or 99) if mine else None
    links = list((best or {}).get("links") or [])
    for it in items:                     # a separate sitelink element that belongs to our domain
        if _is_sitelink_item(it) and (_ours(it.get("domain"), host) or any(
                _ours(urlparse(x.get("url") or "").netloc, host) for x in it.get("items") or [])
                or (best and it.get("rank_group") == best.get("rank_group"))):
            links += it.get("items") or [it]
    snippet = ""
    if best:
        snippet = " ".join(str(best.get(k) or "") for k in ("description",)).strip() \
                  or str(best.get("extended_snippet") or best.get("pre_snippet") or "").strip()
    top3 = []
    for i in organic[:3]:
        top3.append(i.get("domain") or urlparse(i.get("url") or "").netloc)
    return {"term": term, "rank": (best.get("rank_group") if best else None),
            "url": (best or {}).get("url"), "title": (best or {}).get("title"),
            "sitelinks": [x.get("title") or x.get("url") for x in links],
            "top3": top3, "snippet": snippet, "results": len(organic)}


def snippet_problem(snippet):
    """'markup' | 'boilerplate' | '' for the snippet text as Google showed it."""
    if not snippet:
        return ""
    if ingest.MARKUP.search(snippet):
        return "markup"
    if len({m.group(0).lower() for m in BOILER.finditer(snippet)}) >= 2:
        return "boilerplate"
    return ""


def findings(host, rows):
    F = []
    for r in rows:
        t, u = r["term"], f"https://{host}/"
        if r.get("failed"):
            F.append({"cat": "brand", "sev": "low", "url": u, "term": t,
                      "msg": f"search \"{t}\": no result ({r['failed']}); no claim about rank"})
            continue
        if r["rank"] != 1:
            where = "is not in the top 10" if r["rank"] is None else f"ranks #{r['rank']}"
            F.append({"cat": "brand", "sev": "high", "url": u, "term": t,
                      "msg": f"search \"{t}\": {host} {where}; the top 3 are "
                             f"{', '.join(r['top3']) or 'none'}"})
        elif not r["sitelinks"]:
            F.append({"cat": "brand", "sev": "med", "url": u, "term": t,
                      "msg": f"search \"{t}\": {host} is #1 with no sitelinks. Levers: {LEVERS}"})
        p = snippet_problem(r["snippet"])
        if p:
            F.append({"cat": "brand", "sev": "med", "url": r["url"] or u, "term": t,
                      "msg": f"search \"{t}\": the snippet of {host} holds "
                             + ("escaped markup" if p == "markup" else "footer/legal boilerplate")
                             + f" (\"{r['snippet'][:90]}\") — run `snippet` and put data-nosnippet "
                               "on the block that holds it"})
    return F


def check(cfg, post=None):
    """Run the check. `post` replaces the DataForSEO call in tests. Returns
    {terms, rows, findings, cost, estimate} or {error}."""
    host, ts = host_of(cfg), terms(cfg)
    if not host or not ts:
        return {"error": "no site or brand name in config — set `site` and `brand.name`"}
    est = estimate(cfg, len(ts))
    cap = (cfg.get("dataforseo") or {}).get("max_cost", MAX_COST)
    if est > cap:
        return {"error": f"refused: {len(ts)} terms cost about USD {est:.3f}, over the cap "
                         f"USD {cap:.3f} (`dataforseo.max_cost` in config)", "estimate": est}
    d = cfg.get("dataforseo") or {}
    got, failed, cost = {}, {}, 0.0
    for n, k in enumerate(ts):
        # The Live endpoint takes ONE task per request ("You can set only one task at a time",
        # status 40000, 3 Nov 2026), so each term is its own request; the cost is the same.
        task = {"keyword": k, "location_name": d.get("location_name", "United States"),
                "language_name": d.get("language_name", "English"), "device": d.get("device", "desktop"),
                "depth": 10}
        res = (post or providers._dfs_post)("serp/google/organic/live/advanced", [task], 120)
        if not res:
            failed[k] = "no DataForSEO creds, or the call failed"
            if n == 0:
                return {"error": failed[k] + " (see the message above)", "estimate": est}
            continue
        cost += res.get("cost") or 0
        tk = (res.get("tasks") or [{}])[0]
        if tk.get("status_code", 20000) == 20000:
            got[k] = ((tk.get("result") or [{}])[0] or {}).get("items") or []
        else:
            failed[k] = f"{tk.get('status_code')} {tk.get('status_message')}"
        if post is None and n < len(ts) - 1:
            time.sleep(0.3)
    rows = []
    for k in ts:
        if k in got:
            rows.append(analyse(k, got[k], host))
        else:
            rows.append({"term": k, "rank": None, "url": None, "title": None, "sitelinks": [],
                         "top3": [], "snippet": "", "results": 0, "failed": failed.get(k, "no result")})
    return {"host": host, "terms": ts, "rows": rows, "findings": findings(host, rows),
            "cost": round(cost, 4), "estimate": est}


def render_md(cfg, r):
    if r.get("error"):
        return f"brand: {r['error']}"
    L = [f"# Brand SERP — {r['host']} — {datetime.date.today().isoformat()}",
         f"{len(r['terms'])} terms · Google top 10 · {cfg['dataforseo'].get('location_name')} · "
         f"{cfg['dataforseo'].get('language_name')} · desktop · cost USD {r['cost']} "
         f"(estimate {r['estimate']})", "",
         "| term | our rank | sitelinks | top 3 |", "|---|--:|--:|---|"]
    for x in r["rows"]:
        L.append(f"| {x['term']} | {'request failed' if x.get('failed') else (x['rank'] or 'not in top 10')} | {len(x['sitelinks'])} | "
                 f"{', '.join(x['top3']) or '—'} |")
    L.append("")
    for x in r["rows"]:
        if x["snippet"]:
            L.append(f"- \"{x['term']}\" snippet: {x['snippet'][:200]}")
    L.append("")
    order = {"high": 0, "med": 1, "low": 2}
    for f in sorted(r["findings"], key=lambda f: order[f["sev"]]):
        L.append(f"- {f['sev'].upper()}: {f['msg']}")
    if not r["findings"]:
        L.append("_No brand findings._")
    return "\n".join(L)


def save(cfg, r):
    """A dated snapshot in history/brand/ so the rank can be tracked over time."""
    d = Path(cfg.get("history_dir", "history")) / "brand"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{datetime.date.today().isoformat()}.json").write_text(
        json.dumps({k: r[k] for k in ("host", "terms", "rows", "cost")}, indent=1))
