"""Snippet audit (offline) — what a Google snippet can quote from our pages.

Google builds a snippet from a page's visible text. Anything outside `data-nosnippet`
(valid on div, span and section) can be quoted. Two things go wrong in practice:

  markup    an embed/share box (a textarea or code block holding `<a href="...">...</a>`,
            an `<iframe`) reads as raw code in the result. superx.pk, 3 Nov 2026: the
            snippet quoted `superx.pk/stocks/FECM/">FECM share price</a> on SuperX</p`.
  boilerplate  the footer/legal text is visible, and the page's own text is short, so the
            footer is what is left to quote ("LEGAL. Privacy Policy").

Reads the fields `ingest.extract` stores (`snippet_markup`, `footer_text`, `main_text`);
a corpus from before LEARNINGS #36 lacks them and needs a re-ingest. Findings are grouped by
template (the first path section, as `template_family` reasons about titles), one finding
per template and kind, so a layout fix shows up as one line with a count."""
from urllib.parse import urlparse

from .audit import template_family

SHORT_WORDS = 80    # a page whose own text is shorter than this leaves the footer to the snippet


def _indexable(c):
    return c.get("status", 200) == 200 and "noindex" not in (c.get("robots") or "")


def template_of(url):
    """'/stocks/FECM/' → '/stocks/'; a page at the top level ('/about/') → '/ (top level)'."""
    parts = [p for p in urlparse(url).path.split("/") if p]
    return f"/{parts[0]}/" if len(parts) >= 2 else "/ (top level)"


def _group(pages):
    g = {}
    for c in pages:
        g.setdefault(template_of(c["url"]), []).append(c)
    return g


def scan(corpus, short_words=SHORT_WORDS):
    """{'stale': n pages without the fields, 'markup': {template: [pages]}, 'boiler': {...}}"""
    idx = [c for c in corpus if _indexable(c)]
    have = [c for c in idx if "snippet_markup" in c]
    markup = [c for c in have if c.get("snippet_markup")]
    boiler = [c for c in have if c.get("footer_text")
              and len((c.get("main_text") or c.get("text") or "").split()) < short_words]
    return {"pages": len(idx), "scanned": len(have), "stale": len(idx) - len(have),
            "markup": _group(markup), "boiler": _group(boiler)}


def _family(pages):
    titles = [c.get("title") or "" for c in pages[:40]]
    return len(pages) > 1 and template_family(titles)


def check(corpus, F, t=None):
    """Append `snippet` findings to F; return the scan summary."""
    t = t or {}
    r = scan(corpus, t.get("snippet_short_words", SHORT_WORDS))
    if r["pages"] and r["stale"] == r["pages"]:
        F.append({"cat": "snippet", "sev": "low", "url": corpus[0]["url"] if corpus else "",
                  "msg": "snippet check skipped: the corpus has no snippet fields — run `ingest` again"})
        return r
    for tpl, pages in sorted(r["markup"].items(), key=lambda kv: -len(kv[1])):
        ex = pages[0]["snippet_markup"][0].replace("\n", " ")
        F.append({"cat": "snippet", "sev": "med", "url": pages[0]["url"], "template": tpl,
                  "count": len(pages), "kind": "markup",
                  "msg": f"{len(pages)} pages under {tpl} show escaped markup as visible text "
                         f"(\"…{ex[:90]}…\") — a snippet can quote it as code. Put data-nosnippet on the "
                         "div, section or span that holds the embed/share box"
                         + (" (one template: fix it once in the layout)" if _family(pages) else "")})
    for tpl, pages in sorted(r["boiler"].items(), key=lambda kv: -len(kv[1])):
        ex = pages[0]["footer_text"][:70]
        F.append({"cat": "snippet", "sev": "low", "url": pages[0]["url"], "template": tpl,
                  "count": len(pages), "kind": "boilerplate",
                  "msg": f"{len(pages)} pages under {tpl} have under {t.get('snippet_short_words', SHORT_WORDS)} "
                         f"words of own text and a footer that a snippet can quote (\"{ex}…\") — put "
                         "data-nosnippet on the footer's legal block (a div or span inside <footer>)"
                         + (" (one template)" if _family(pages) else "")})
    return r
