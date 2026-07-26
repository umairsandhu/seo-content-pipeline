"""The recommendation engine — fuse the four signals into one prioritized plan:

  1. Cannibalization  — query-clusters in the site's own corpus to consolidate.
  2. Content gaps      — keywords with demand the site does NOT already cover
                         (dedup gate: NOVEL/RELATED = write; EXTEND = skip).
  3. Striking distance — GSC queries at position 5–15 (one push from page 1).
  4. Low-CTR pages     — GSC pages with impressions but weak CTR (retitle).

Everything degrades gracefully: no GSC creds → skip 3&4; no DataForSEO → no
volumes, gaps still rank by intent + dedup verdict."""
import datetime
from . import providers
from .index import Index, load_corpus


def cannibalization(idx, threshold=0.55):
    return idx.clusters(threshold, space="title")


def content_gaps(idx, keywords, cfg):
    dfs = cfg.get("dataforseo", {})
    vol = providers.search_volume(keywords, dfs.get("location_name"), dfs.get("language_name")) if keywords else {}
    gaps = []
    for kw in keywords:
        verdict, nearest = idx.check_topic(kw)
        if verdict == "EXTEND":
            continue
        gaps.append({"keyword": kw, "verdict": verdict,
                     "volume": vol.get(kw, {}).get("volume"),
                     "nearest": [{"page": p, "score": round(s, 2)} for p, s in nearest[:2]],
                     "links": [p for p, _ in idx.link_targets(kw, k=3)]})
    gaps.sort(key=lambda g: -((g["volume"] or 0) + (5000 if g["verdict"] == "NOVEL" else 0)))
    return gaps


def _host(url):
    return (url or "").replace("https://", "").replace("http://", "").rstrip("/").split("/")[0]


def competitor_gap(cfg, idx, limit=40):
    """Keywords 2–3 competitors rank for that we don't cover (dedup gate drops
    topics we already own). Ranked by competitor consensus, then volume."""
    dfs = cfg.get("dataforseo", {})
    loc, lang = dfs.get("location_name"), dfs.get("language_name")
    ours = {r["keyword"].lower() for r in providers.ranked_keywords(_host(cfg.get("site")), loc, lang)}
    gap = {}
    for comp in cfg.get("competitors", []):
        for r in providers.ranked_keywords(_host(comp), loc, lang):
            low = r["keyword"].lower()
            if low in ours:
                continue
            verdict, _ = idx.check_topic(r["keyword"])
            if verdict == "EXTEND":
                continue  # we already cover this topic
            g = gap.setdefault(low, {"keyword": r["keyword"], "volume": r.get("volume"),
                                     "competitors": [], "verdict": verdict})
            g["competitors"].append(_host(comp))
    out = sorted(gap.values(), key=lambda g: (-len(g["competitors"]), -(g.get("volume") or 0)))
    return out[:limit]


def discover(seed, cfg, limit=40):
    """DataForSEO keyword suggestions for a seed → candidate keywords (trend/gap pull)."""
    dfs = cfg.get("dataforseo", {})
    return providers.suggestions(seed, dfs.get("location_name"), dfs.get("language_name"), limit)


def gsc_raw(cfg, months=3):
    """Raw GSC query + page rows (the longitudinal signal history.py snapshots).
    Prefers the live API; falls back to the latest imported CSV snapshot in
    history/ (for sites that can't grant service-account access — see gsc_csv)."""
    prop, cred = cfg.get("gsc_property"), cfg.get("gsc_credentials")
    if prop and cred:
        svc = providers.gsc_service(cred)
        if svc:
            end = datetime.date.today()
            start = end - datetime.timedelta(days=30 * months)
            return {"queries": providers.gsc_query(svc, prop, str(start), str(end), ("query",)),
                    "pages": providers.gsc_query(svc, prop, str(start), str(end), ("page",))}
    from . import history
    q, p = history.latest(cfg, "gsc_queries"), history.latest(cfg, "gsc_pages")
    if q and p:
        return {"queries": q["data"], "pages": p["data"]}
    return None


def opportunities_from(raw):
    if not raw:
        return None
    return {"striking": providers.striking_distance(raw["queries"])[:40],
            "low_ctr": providers.low_ctr(raw["pages"])[:40]}


def gsc_opportunities(cfg, months=3):
    return opportunities_from(gsc_raw(cfg, months))


def report(cfg, keywords=None, corpus_path="corpus.json"):
    idx = Index(load_corpus(corpus_path))
    out = {"pages": len(idx.corpus),
           "cannibalization": cannibalization(idx),
           "gaps": content_gaps(idx, keywords or [], cfg),
           "gsc": gsc_opportunities(cfg)}
    return idx, out


def render_md(cfg, rep):
    site = cfg.get("site", "site")
    L = [f"# SEO recommendations — {site}", "",
         f"{rep['pages']} pages indexed.", ""]
    c = rep["cannibalization"]
    L += [f"## 1. Consolidate ({len(c)} query-cannibalization clusters)"]
    for g in c[:12]:
        L.append(f"- peak {g['peak']:.2f}: " + " · ".join(m.rsplit('/', 1)[-1] for m in g["members"]))
    g = rep["gaps"]
    L += ["", f"## 2. Content gaps to write ({len(g)})", ""]
    if g:
        L += ["| keyword | vol | verdict | link into |", "|---|--:|---|---|"]
        for r in g[:25]:
            L.append(f"| {r['keyword']} | {r['volume'] or '—'} | {r['verdict']} | "
                     + ", ".join(x.rsplit('/', 1)[-1] for x in r['links'][:2]) + " |")
    gsc = rep["gsc"]
    if gsc:
        L += ["", f"## 3. Striking distance — one push to page 1 ({len(gsc['striking'])})",
              "| query | pos | impr | ctr |", "|---|--:|--:|--:|"]
        for r in gsc["striking"][:20]:
            L.append(f"| {r['query']} | {r['position']:.1f} | {r['impressions']} | {r['ctr']*100:.1f}% |")
        L += ["", f"## 4. Low-CTR pages — retitle ({len(gsc['low_ctr'])})",
              "| page | impr | ctr |", "|---|--:|--:|"]
        for r in gsc["low_ctr"][:20]:
            L.append(f"| {r['page']} | {r['impressions']} | {r['ctr']*100:.1f}% |")
    else:
        L += ["", "## 3–4. GSC opportunities", "_(set gsc_property + gsc_credentials to unlock "
              "striking-distance + low-CTR analysis)_"]
    return "\n".join(L)
