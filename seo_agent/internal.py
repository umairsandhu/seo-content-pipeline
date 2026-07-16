"""Internal-link + consolidation recommender — two high-ROI structural moves the
Site Doctor only diagnoses:

  inbound_suggestions(url) — existing pages that SHOULD link to a target (content
    similar to it that doesn't already link there). The reverse of link_targets:
    "who should point at this page?" — the fix for orphans/under-linked pages.
  consolidation() — for each cannibalization cluster, recommend which page to KEEP
    (most inbound links, then longest) and merge/redirect the rest.

Deterministic, offline (reads corpus.json + the TF-IDF index)."""
from urllib.parse import urljoin, urlparse

from sklearn.metrics.pairwise import cosine_similarity

from .index import Index, load_corpus


def _norm(base, href=""):
    try:
        p = urlparse(urljoin(base, href))
    except Exception:
        return None
    return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/") if p.scheme in ("http", "https") else None


def inbound_suggestions(cfg, target_url, k=10, corpus_path="corpus.json"):
    corpus = load_corpus(corpus_path)
    idx = Index(corpus)
    tgt = next((c for c in corpus if target_url in (c.get("url"), c.get("final_url"))), None)
    if not tgt:
        return {"error": "target not found in corpus.json"}
    tnorm = _norm(tgt.get("final_url") or tgt["url"])
    sims = cosine_similarity(idx.vec.transform([tgt.get("text", "")]), idx.X)[0]
    out = []
    for i in sims.argsort()[::-1]:
        if sims[i] < 0.1:            # below this it isn't a genuine topical match
            break
        c = idx.corpus[i]
        if _norm(c.get("final_url") or c["url"]) == tnorm:
            continue
        if tnorm in {_norm(c["url"], h) for h in c.get("links", [])}:
            continue  # already links to the target
        out.append({"from": c["url"], "score": round(float(sims[i]), 2)})
        if len(out) >= k:
            break
    return {"target": target_url, "add_links_from": out}


def link_plan(cfg, min_inbound=3, max_targets=30, corpus_path="corpus.json"):
    """A batch internal-link plan: for every under-linked/orphan page, which existing
    pages should add a contextual link, and the suggested anchor. Propose-only —
    apply as PRs. Directly attacks weak internal linking / topical-authority gaps."""
    corpus = load_corpus(corpus_path)
    idx = Index(corpus)
    norm_of = [_norm(c.get("final_url") or c["url"]) for c in corpus]
    links_of = [{_norm(c["url"], h) for h in c.get("links", [])} for c in corpus]
    inbound = {n: 0 for n in norm_of}
    for ls in links_of:
        for t in ls:
            if t in inbound:
                inbound[t] += 1
    idxable = lambda c: c.get("status", 200) == 200 and "noindex" not in (c.get("robots") or "")
    targets = sorted((i for i, c in enumerate(corpus)
                      if idxable(c) and inbound.get(norm_of[i], 0) < min_inbound),
                     key=lambda i: inbound.get(norm_of[i], 0))[:max_targets]
    plan = []
    for ti in targets:
        c = corpus[ti]
        sims = cosine_similarity(idx.vec.transform([c.get("text", "")]), idx.X)[0]
        add = []
        for si in sims.argsort()[::-1]:
            if sims[si] < 0.1:
                break
            if si == ti or norm_of[ti] in links_of[si]:
                continue
            add.append(corpus[si]["url"])
            if len(add) >= 3:
                break
        if add:
            plan.append({"target": c["url"], "inbound": inbound.get(norm_of[ti], 0),
                         "anchor": (c.get("h1") or [c.get("title", "")])[0] or c.get("title", ""),
                         "add_from": add})
    return plan


def render_link_plan(cfg, plan):
    L = [f"# Internal-link plan — {cfg.get('site','site')}",
         f"{len(plan)} under-linked pages. For each, add a contextual link **from** the listed "
         f"pages (anchor ≈ the target's topic). Apply as PRs — closes the diagnose→fix loop.", ""]
    for p in plan[:25]:
        L.append(f"- **{p['target'].rsplit('/', 1)[-1] or p['target']}** (inbound {p['inbound']}) "
                 f"← link from: " + ", ".join(u.rsplit('/', 1)[-1] or u for u in p["add_from"])
                 + f"  · anchor: “{p['anchor'][:50]}”")
    if not plan:
        L.append("_No under-linked pages — internal linking is healthy._")
    return "\n".join(L)


def consolidation(cfg, corpus_path="corpus.json"):
    corpus = load_corpus(corpus_path)
    idx = Index(corpus)
    ids = {_norm(c.get("final_url") or c["url"]): c for c in corpus}
    inbound = {k: 0 for k in ids}
    for c in corpus:
        for h in c.get("links", []):
            t = _norm(c["url"], h)
            if t in inbound:
                inbound[t] += 1
    out = []
    for g in idx.clusters(0.55, space="title"):
        score = lambda m: (inbound.get(_norm(m), 0), ids.get(_norm(m), {}).get("words", 0))
        keep = max(g["members"], key=score)
        out.append({"keep": keep, "merge_redirect": [m for m in g["members"] if m != keep],
                    "peak": round(g["peak"], 2)})
    return out


def render_md(cfg, cons):
    L = [f"# Consolidation plan — {cfg.get('site','site')}",
         f"{len(cons)} cannibalization clusters. Keep the strongest, 301-redirect the rest into it.", ""]
    for c in cons[:15]:
        L.append(f"- **keep** {c['keep'].rsplit('/', 1)[-1]} · redirect: "
                 + ", ".join(m.rsplit("/", 1)[-1] for m in c["merge_redirect"]))
    if not cons:
        L.append("_No cannibalization clusters._")
    return "\n".join(L)
