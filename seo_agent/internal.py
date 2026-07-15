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
