"""Content-refresh loop — closes the gap `decay` opens. Detecting decline isn't
enough; the value is diagnosing WHY and shipping an updated page. For a target URL
this diagnoses staleness (old year references, aging stats, intent drift vs the live
SERP, thin vs. current top results) and returns a **refresh packet** the agent (or a
headless LLM) rewrites from — then you re-publish and verify recovery next run.

Agent-native: returns `mode: "agent"` with the packet by default; no key needed.
Site-agnostic."""
import datetime
import re

from . import produce
from .index import load_corpus


def _page(corpus, url):
    u = url.rstrip("/")
    for c in corpus:
        if (c.get("url", "").rstrip("/") == u) or (c.get("final_url", "").rstrip("/") == u):
            return c
    return None


def diagnose(cfg, url, corpus_path="corpus.json"):
    corpus = load_corpus(corpus_path)
    page = _page(corpus, url)
    if not page:
        return {"error": f"{url} not in corpus — run `ingest` first"}
    text = page.get("text", "") or ""
    year = datetime.date.today().year
    signals = []
    # stale year references
    years = [int(y) for y in re.findall(r"\b(20\d\d)\b", text)]
    if years and max(years) < year - 1:
        signals.append(f"newest year referenced is {max(years)} (now {year}) — update dates/stats")
    tyrs = [int(y) for y in re.findall(r"\b(20\d\d)\b",
            (page.get('title') or '') + " " + " ".join(page.get('headings', [])))]
    if tyrs and max(tyrs) < year:  # ANY past year with no current one — "in 2025" is stale in 2026
        signals.append(f"title/heading says {max(tyrs)} — bump to {year}")
    # thin vs typical
    words = page.get("words") or len(text.split())
    if words < 700:
        signals.append(f"thin at {words} words — expand depth")
    # intent drift vs live SERP (needs DataForSEO; degrades to empty)
    kw = (page.get("title") or page.get("url", "").rsplit("/", 1)[-1].replace("-", " "))
    try:
        serp = produce.brief(cfg, kw)
    except Exception:
        serp = None
    paa = serp.get("questions", []) if serp else []
    missing_q = [q for q in paa if q and q.lower().split()[0] not in text.lower()][:6]
    if missing_q:
        signals.append("live SERP asks questions the page doesn't answer (see packet)")
    return {"url": page["url"], "words": words, "signals": signals,
            "questions_to_add": missing_q, "keyword": kw, "modified": page.get("modified")}


def packet(cfg, url, corpus_path="corpus.json"):
    d = diagnose(cfg, url, corpus_path)
    if d.get("error"):
        return d
    sig = "\n".join(f"- {s}" for s in d["signals"]) or "- (no obvious staleness — verify against the SERP)"
    q = "\n".join(f"- {x}" for x in d["questions_to_add"]) or "- (none / no SERP data)"
    md = (f"# Refresh assignment — {d['url']}\n\n"
          f"Target keyword: \"{d['keyword']}\" · current length: {d['words']} words · "
          f"last modified: {d.get('modified') or 'unknown'}\n\n"
          f"## Diagnosed staleness\n{sig}\n\n"
          f"## New questions to cover (from the live SERP)\n{q}\n\n"
          f"## Deliverable\nRewrite/expand the page: refresh dates & stats to the current year, add the "
          f"missing answers as question H2/H3s (front-load each answer for AI citation), deepen thin "
          f"sections, and keep the URL. Update `dateModified` in the Article schema. Then re-publish and "
          f"re-check rank next run.")
    return {"mode": "agent", "diagnosis": d, "packet": md}


def render_md(cfg, r):
    return r.get("packet") or f"_{r.get('error','no packet')}_"
