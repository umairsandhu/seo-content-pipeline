"""Content comprehensiveness scoring (Surfer / Clearscope-lite). For a target
keyword, pull the top organic results, extract the salient terms the ranking
pages share, and score how much a given page covers vs them — surfacing the
subtopics / terms you're missing so the draft can be made more complete.

Needs DataForSEO to fetch the SERP; fetches competitor pages with the built-in
crawler. Degrades to an error dict without creds."""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from . import ingest, providers


def _terms(texts, top=40):
    for mdf in (2, 1):
        try:
            vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                  min_df=mdf, max_features=2000)
            X = vec.fit_transform(texts)
            break
        except ValueError:
            continue
    else:
        return []
    scores = np.asarray(X.mean(axis=0)).ravel()
    vocab = vec.get_feature_names_out()
    return [vocab[i] for i in scores.argsort()[::-1][:top]]


def _corpus_reference(keyword, page_url, k=8, corpus_path="corpus.json"):
    """No-key fallback: reference texts = the most keyword-similar pages on YOUR OWN
    site. Weaker than a live SERP but never a dead end — coverage vs your best
    related pages still surfaces missing subtopics."""
    try:
        from .index import Index, load_corpus
        corpus = load_corpus(corpus_path)
        others = [c for c in corpus if page_url.rstrip("/") not in
                  (c.get("url", "").rstrip("/"), (c.get("final_url") or "").rstrip("/"))
                  and len(c.get("text") or "") > 400]
        by_url = {c["url"]: c for c in others}
        texts = []
        try:  # tier 1: semantic similarity
            urls = [u for u, _ in Index(corpus).link_targets(keyword, k=k + 2)]
            texts = [(by_url.get(u) or {}).get("text", "") for u in urls]
            texts = [t for t in texts if len(t) > 400]
        except Exception:
            pass
        if len(texts) < 3:  # tier 2: keyword-token overlap (robust on small corpora)
            toks = [w for w in keyword.lower().split() if len(w) > 2]
            scored = sorted(others, key=lambda c: (-sum((c.get("text") or "").lower().count(t)
                                                        for t in toks), -len(c.get("text") or "")))
            texts = [c["text"] for c in scored if any(t in (c.get("text") or "").lower() for t in toks)]
        return texts[:k]
    except Exception:
        return []


def _page_text(page_url, corpus_path="corpus.json"):
    try:  # prefer the crawled copy (offline-friendly); fetch live only as fallback
        from .index import load_corpus
        for c in load_corpus(corpus_path):
            if page_url in (c.get("url"), c.get("final_url")):
                return (c.get("text") or "").lower()
    except Exception:
        pass
    try:
        _, _, doc = ingest._fetch(page_url)
        return ingest.extract(page_url, doc)["text"].lower()
    except Exception:
        return ""


def score(cfg, keyword, page_url, competitors=8):
    dfs = cfg.get("dataforseo", {})
    s = providers.serp(keyword, dfs.get("location_name"), dfs.get("language_name"), depth=competitors)
    urls = [o["url"] for o in s.get("organic", []) if o.get("url")][:competitors]
    texts, mode = [], "serp"
    for u in urls:
        if u == page_url:
            continue
        try:
            _, _, doc = ingest._fetch(u)
            texts.append(ingest.extract(u, doc)["text"])
        except Exception:
            pass
    if len(texts) < 3:  # no creds / SERP fetch failed → corpus-relative, never a dead end
        texts, mode = _corpus_reference(keyword, page_url, competitors), "corpus-relative"
    if len(texts) < 3:
        return {"error": "need DataForSEO for SERP-grounded scoring, or a crawled corpus "
                         "(`ingest`) with ≥3 related pages for the offline fallback"}
    terms = _terms(texts)
    ours = _page_text(page_url)
    have = [t for t in terms if t in ours]
    missing = [t for t in terms if t not in ours]
    return {"keyword": keyword, "page": page_url, "mode": mode,
            "coverage_pct": round(100 * len(have) / len(terms)) if terms else 0,
            "competitors_analyzed": len(texts),
            "note": ("scored vs your own most-related pages — add DATAFORSEO_* for "
                     "SERP-grounded scoring" if mode == "corpus-relative" else ""),
            "covered": have[:20], "missing": missing[:25]}


def render_md(r):
    if "error" in r:
        return f"_content score unavailable: {r['error']}_"
    L = [f"# Content score — “{r['keyword']}”",
         f"Coverage vs top {r['competitors_analyzed']} results: **{r['coverage_pct']}%**", "",
         f"Page: {r['page']}", "",
         "## Missing subtopics/terms competitors cover (add these)",
         ", ".join(r["missing"]) or "_none — comprehensive_", "",
         "## Already covered", ", ".join(r["covered"])]
    return "\n".join(L)
