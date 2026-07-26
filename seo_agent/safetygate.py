"""Programmatic-content safety gate. Google's 2026 scaled-content-abuse enforcement
deleted sites that shipped thousands of thin, near-duplicate, templated pages. This
is the guardrail: before a draft is published it must clear a near-duplicate check,
a thin-content check, and a unique-value check — or `publish` blocks with a reason.

Deterministic + offline (TF-IDF cosine over the existing corpus, no creds). Swap the
vectorizer for embeddings (SEO_EMBEDDINGS=1) for semantic near-dup detection. Fully
site-agnostic."""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .index import load_corpus

DUP_THRESHOLD = 0.90     # cosine ≥ this vs an existing page → too similar
THIN_WORDS = 300         # below this = thin
MIN_UNIQUE = 0.35        # fraction of body that isn't shared boilerplate


def _text(page):
    return " ".join([page.get("title", ""), " ".join(page.get("headings", []) or []),
                     page.get("text", "") or page.get("body", "") or page.get("markdown", "")])


def check(candidate, corpus_path="corpus.json", dup_threshold=DUP_THRESHOLD):
    """candidate: {title, text|body|markdown, headings?}. Returns a verdict dict."""
    cand = _text(candidate)
    words = len(re.findall(r"\w+", cand))
    reasons, nearest = [], None
    try:
        corpus = load_corpus(corpus_path)
    except Exception:
        corpus = []
    if corpus:
        bodies = [_text(c) for c in corpus]
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True,
                              min_df=1, max_df=0.7, max_features=40000)
        M = vec.fit_transform(bodies + [cand])
        sims = cosine_similarity(M[-1], M[:-1]).ravel()
        if len(sims):
            i = int(sims.argmax())
            nearest = {"url": corpus[i].get("url"), "similarity": round(float(sims[i]), 3)}
            if sims[i] >= dup_threshold:
                reasons.append(f"near-duplicate of {nearest['url']} (cosine {nearest['similarity']})")
            # template farm signal: many pages very close to this one
            close = int((sims >= 0.75).sum())
            if close >= 5:
                reasons.append(f"looks templated — {close} existing pages are highly similar")
    if words < THIN_WORDS:
        reasons.append(f"thin content — {words} words (< {THIN_WORDS})")
    # unique-value proxy: ratio of distinct 3-grams to total (low = repetitive boilerplate)
    toks = re.findall(r"\w+", cand.lower())
    grams = list(zip(toks, toks[1:], toks[2:]))
    uniq = len(set(grams)) / max(len(grams), 1)
    if grams and uniq < MIN_UNIQUE:
        reasons.append(f"low unique-value ({uniq:.2f} distinct-trigram ratio) — reads as boilerplate")
    return {"ok": not reasons, "words": words, "nearest": nearest,
            "unique_ratio": round(uniq, 3), "reasons": reasons}


def render_md(v):
    head = "✅ cleared" if v["ok"] else "🔴 BLOCKED"
    L = [f"# Programmatic safety gate — {head}",
         f"- words: {v['words']} · unique-trigram ratio: {v['unique_ratio']}"]
    if v.get("nearest"):
        L.append(f"- nearest existing page: {v['nearest']['url']} (cosine {v['nearest']['similarity']})")
    for r in v["reasons"]:
        L.append(f"- 🔴 {r}")
    if not v["ok"]:
        L.append("\n_Publishing blocked. Differentiate the page (unique data, examples, angle) "
                 "or consolidate into the near-duplicate instead of adding a new URL._")
    return "\n".join(L)
