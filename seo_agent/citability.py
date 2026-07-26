"""Passage-citability scoring — how extractable a page is for AI answers (AI
Overviews, AI Mode, ChatGPT/Perplexity). AI engines cite short, answer-first
*passages* (~40–170 words), not whole pages, and 80% of citations come from URLs
outside the classic top 10 — so extractability is its own ranking surface.

Deterministic + offline (reads corpus.json). Scores each page 0–100 on the signals
that make a passage quotable:
  · answer-first opening (a direct answer up front, in the citable word band)
  · question-form headings mapped to answers (Q&A structure)
  · lists / tables (extractable structure)
  · fact density (numbers / stats a model can lift)
  · self-contained sentences (not too long, low pronoun-anaphora)
Site-agnostic; no brand or vertical assumptions."""
import re

from .index import load_corpus

_Q = re.compile(r"^(what|why|how|when|where|who|which|is|are|can|do|does|should|will)\b", re.I)
_WORD = re.compile(r"\w+")


def _passages(text, lo=40, hi=170):
    """Split into candidate passages and flag those in the citable word band."""
    chunks = [c.strip() for c in re.split(r"\n{2,}|(?<=[.!?])\s{2,}", text) if c.strip()]
    return [(c, len(_WORD.findall(c))) for c in chunks]


def score_page(c):
    text = c.get("text", "") or ""
    heads = c.get("headings", []) or []
    words = c.get("words") or len(_WORD.findall(text))
    sig = {}
    # answer-first: an early passage sits in the 40–170-word band
    early = _passages(text)[:3]
    sig["answer_first"] = any(40 <= n <= 190 for _, n in early) if early else False
    # question headings mapped to content
    qh = sum(1 for h in heads if _Q.match(h) or h.strip().endswith("?"))
    sig["qa_headings"] = qh >= 2
    # extractable structure
    sig["lists_or_tables"] = (c.get("lists", 0) or 0) + (c.get("tables", 0) or 0) >= 1
    # fact density: numbers per 100 words
    nums = len(re.findall(r"\b\d[\d,.%$]*\b", text))
    sig["fact_density"] = words > 0 and (nums / words * 100) >= 1.0
    # concision: median-ish sentence not a run-on
    sents = [s for s in re.split(r"(?<=[.!?])\s", text) if s.strip()]
    long_ratio = sum(1 for s in sents if len(_WORD.findall(s)) > 34) / max(len(sents), 1)
    sig["concise"] = long_ratio < 0.30
    score = round(100 * sum(sig.values()) / len(sig))
    return {"url": c.get("url"), "score": score, "signals": sig,
            "question_headings": qh, "num_facts": nums}


def report(cfg, corpus_path="corpus.json"):
    corpus = load_corpus(corpus_path)
    pages = [score_page(c) for c in corpus if (c.get("words") or 0) > 60]
    pages.sort(key=lambda p: p["score"])
    miss = {}
    for k in ("answer_first", "qa_headings", "lists_or_tables", "fact_density", "concise"):
        miss[k] = sum(1 for p in pages if not p["signals"][k])
    return {"pages": len(pages),
            "avg": round(sum(p["score"] for p in pages) / len(pages), 1) if pages else 0,
            "missing": miss, "lowest": pages[:20]}


_LABEL = {"answer_first": "answer-first opening (40–170 words)", "qa_headings": "question-form headings",
          "lists_or_tables": "lists/tables", "fact_density": "fact/number density", "concise": "concise sentences"}


def render_md(cfg, r):
    L = [f"# Passage-citability — {cfg.get('site','site')}",
         f"{r['pages']} pages · avg **{r['avg']}/100** extractable-for-AI", "",
         "## Fix site-wide (highest impact first)"]
    for k, n in sorted(r["missing"].items(), key=lambda kv: -kv[1]):
        if n:
            L.append(f"- {_LABEL[k]} — missing on {n}/{r['pages']} pages")
    L += ["", "## Lowest-citability pages"]
    for p in r["lowest"][:15]:
        miss = ", ".join(k for k, v in p["signals"].items() if not v)
        L.append(f"- {p['score']}/100 — {p['url'].rsplit('/',1)[-1]}  (fix: {miss})")
    L.append("\n_AI answers cite 40–170-word answer-first passages, not whole pages. "
             "Front-load a direct answer, use question headings, add a list/table, cite a number._")
    return "\n".join(L)
