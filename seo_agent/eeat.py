"""E-E-A-T signal audit. E-E-A-T is not a score Google exposes, but its signals
are measurable on-page — and ~85% of pages cited in AI Overviews carry several of
them. This checks the concrete, implementable ones: a named author, publish/
updated dates, outbound citations to primary sources, sitewide trust pages
(about/contact/editorial/privacy), and HTTPS. Output: per-page signal coverage +
site-level gaps. Deterministic, offline (reads corpus.json)."""
from urllib.parse import urlparse

from .index import load_corpus

TRUST_PAGES = ("about", "contact", "editorial", "privacy", "terms", "team", "author")


def _indexable(c):
    return c.get("status", 200) == 200 and "noindex" not in (c.get("robots") or "")


def report(cfg, corpus_path="corpus.json"):
    corpus = load_corpus(corpus_path)
    https = (cfg.get("site") or "").startswith("https")
    # Trust pages usually live at the site root (/about-us, /security), which the
    # content corpus (include-prefixed) excludes — so scan the whole sitemap too.
    paths = [urlparse(c.get("url", "")).path.lower() for c in corpus]
    try:
        from . import ingest
        sm = cfg.get("sitemap")
        if sm:
            paths += [urlparse(u).path.lower() for u in ingest.sitemap_urls(sm)]
    except Exception:
        pass
    allpaths = " ".join(paths)
    trust = {p: (("/" + p) in allpaths) for p in TRUST_PAGES}
    pages = []
    for c in corpus:
        if not _indexable(c):
            continue
        sig = {"author": bool(c.get("author")),
               "dated": bool(c.get("published") or c.get("modified")),
               "citations": (c.get("ext_links", 0) or 0) >= 2,
               "https": https}
        pages.append({"url": c["url"], "signals": sig, "score": sum(sig.values())})
    pick = lambda k: [p["url"] for p in pages if not p["signals"][k]]
    return {"pages": len(pages),
            "avg_signals": round(sum(p["score"] for p in pages) / len(pages), 1) if pages else 0,
            "https": https, "trust_pages": trust,
            "missing_trust": [p for p, ok in trust.items() if not ok],
            "no_author": pick("author"), "no_date": pick("dated"), "no_citations": pick("citations")}


def render_md(cfg, r):
    L = [f"# E-E-A-T signals — {cfg.get('site','site')}",
         f"{r['pages']} indexable pages · avg **{r['avg_signals']}/4** signals · "
         f"HTTPS: {'✓' if r['https'] else '✗ (fix first)'}", ""]
    if r["missing_trust"]:
        L.append(f"- ⚠ missing trust pages: {', '.join(r['missing_trust'])}")
    L += [f"- {len(r['no_author'])} pages have **no author byline** — add a named author + Person schema",
          f"- {len(r['no_date'])} pages have no publish/updated date",
          f"- {len(r['no_citations'])} pages cite <2 outbound sources — link primary sources", "",
          "_E-E-A-T is not a direct ranking score; these are the measurable on-page signals AI "
          "Overviews and quality raters look for. On YMYL pages add a reviewer block too._"]
    return "\n".join(L)
