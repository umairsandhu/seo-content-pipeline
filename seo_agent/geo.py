"""GEO / AEO readiness score — how well the site is set up to be CITED by AI
answer engines (ChatGPT, Perplexity, Google AI Overviews). Google's line is that
AI features ride the same core ranking signals, so GEO ≈ SEO + one extra
requirement: EXTRACTABILITY (each passage liftable) + machine-trust signals.

Scores each indexable page across the levers the research identified:
  extractability — H1, structured headings, Q&A-form headings, lists/tables
  machine-readable — JSON-LD structured data
  trust (E-E-A-T) — named author, dates, ≥2 outbound citations
  access — AI crawlers not blocked (site-level), page renderable (not CSR)

Deterministic + offline (reads corpus.json). See docs/AI-Search.md."""
from .audit import _root_disallowers, AI_BOTS
from .index import load_corpus
from . import ingest

_QWORDS = ("how ", "what ", "why ", "when ", "where ", "which ", "who ", "can ", "is ", "do ", "does ")


def _indexable(c):
    return c.get("status", 200) == 200 and "noindex" not in (c.get("robots") or "")


def _ai_blocked(cfg):
    site = (cfg.get("site") or "").rstrip("/")
    try:
        txt = ingest._get(site + "/robots.txt")
    except Exception:
        return False
    blocked = _root_disallowers(txt)
    return any(a in b for b in blocked for a in AI_BOTS)


def page_score(c, ai_blocked):
    hs = [h.lower() for h in c.get("headings", [])]
    sig = {
        "h1": bool(c.get("h1")),
        "structured_headings": len(c.get("headings", [])) >= 3,
        "qa_headings": any("?" in h or h.startswith(_QWORDS) for h in hs),
        "lists_or_tables": bool(c.get("lists") or c.get("tables")),
        "schema": bool(c.get("jsonld")),
        "author": bool(c.get("author")),
        "dated": bool(c.get("published") or c.get("modified")),
        "citations": (c.get("ext_links", 0) or 0) >= 2,
        "ai_crawlable": not ai_blocked,
        "renderable": not c.get("csr"),
    }
    return round(100 * sum(sig.values()) / len(sig)), sig


def report(cfg, corpus_path="corpus.json"):
    corpus = [c for c in load_corpus(corpus_path) if _indexable(c)]
    ai_blocked = _ai_blocked(cfg)
    scored = [(c, *page_score(c, ai_blocked)) for c in corpus]
    avg = round(sum(s for _, s, _ in scored) / len(scored)) if scored else 0
    # which signals are most often missing (site-wide fix priorities)
    keys = scored[0][2].keys() if scored else []
    missing = {k: sum(1 for _, _, sig in scored if not sig[k]) for k in keys}
    worst = sorted(scored, key=lambda x: x[1])[:15]
    return {"pages": len(scored), "avg_score": avg, "ai_blocked": ai_blocked,
            "missing": dict(sorted(missing.items(), key=lambda kv: -kv[1])),
            "worst": [{"url": c["url"], "score": s,
                       "gaps": [k for k, v in sig.items() if not v]} for c, s, sig in worst]}


def render_md(cfg, r):
    L = [f"# GEO / AEO readiness — {cfg.get('site','site')}",
         f"{r['pages']} indexable pages · **{r['avg_score']}/100** average AI-citation readiness"
         + ("  ·  🔴 **AI crawlers are blocked** (you're opted out of AI answers)" if r["ai_blocked"] else ""),
         "", "## Most-missing signals (fix site-wide, highest impact first)"]
    labels = {"h1": "H1", "structured_headings": "≥3 headings", "qa_headings": "question-form headings (Q&A)",
              "lists_or_tables": "lists/tables", "schema": "JSON-LD schema", "author": "named author",
              "dated": "publish/updated date", "citations": "≥2 outbound citations",
              "ai_crawlable": "AI-crawler access", "renderable": "server-rendered (not CSR)"}
    for k, n in r["missing"].items():
        if n:
            L.append(f"- {labels.get(k, k)} — missing on {n}/{r['pages']} pages")
    L += ["", "## Lowest-readiness pages"]
    for p in r["worst"][:10]:
        L.append(f"- {p['score']}/100 — {p['url'].rsplit('/', 1)[-1] or p['url']}  (missing: {', '.join(p['gaps'][:4])})")
    L += ["", "_GEO ≈ SEO + extractability. Front-load answers, structure with Q&A headings, add "
          "FAQ/HowTo schema, keep AI crawlers unblocked, and strengthen E-E-A-T. See docs/AI-Search.md._"]
    return "\n".join(L)
