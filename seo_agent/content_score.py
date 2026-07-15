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


def score(cfg, keyword, page_url, competitors=8):
    dfs = cfg.get("dataforseo", {})
    s = providers.serp(keyword, dfs.get("location_name"), dfs.get("language_name"), depth=competitors)
    urls = [o["url"] for o in s.get("organic", []) if o.get("url")][:competitors]
    if not urls:
        return {"error": "no SERP results (need DataForSEO creds)"}
    texts = []
    for u in urls:
        if u == page_url:
            continue
        try:
            _, _, doc = ingest._fetch(u)
            texts.append(ingest.extract(u, doc)["text"])
        except Exception:
            pass
    if len(texts) < 3:
        return {"error": "too few competitor pages fetched"}
    terms = _terms(texts)
    try:
        _, _, doc = ingest._fetch(page_url)
        ours = ingest.extract(page_url, doc)["text"].lower()
    except Exception:
        ours = ""
    have = [t for t in terms if t in ours]
    missing = [t for t in terms if t not in ours]
    return {"keyword": keyword, "page": page_url,
            "coverage_pct": round(100 * len(have) / len(terms)) if terms else 0,
            "competitors_analyzed": len(texts),
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
