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


def discover(seed, cfg, limit=40):
    """DataForSEO keyword suggestions for a seed → candidate keywords (trend/gap pull)."""
    dfs = cfg.get("dataforseo", {})
    return providers.suggestions(seed, dfs.get("location_name"), dfs.get("language_name"), limit)


def gsc_opportunities(cfg, months=3):
    prop, cred = cfg.get("gsc_property"), cfg.get("gsc_credentials")
    if not (prop and cred):
        return None
    svc = providers.gsc_service(cred)
    if not svc:
        return None
    end = datetime.date.today()
    start = end - datetime.timedelta(days=30 * months)
    q = providers.gsc_query(svc, prop, str(start), str(end), ("query",))
    pages = providers.gsc_query(svc, prop, str(start), str(end), ("page",))
    return {"striking": providers.striking_distance(q)[:40],
            "low_ctr": providers.low_ctr(pages)[:40]}


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
