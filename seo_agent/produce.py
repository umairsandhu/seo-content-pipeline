"""Layer 3 — Produce. Turn a keyword into a publish-ready article, and fix
on-page weaknesses. Everything is SERP + People-Also-Ask grounded and
internal-link aware.

Design: the Python does the deterministic work (fetch SERP, assemble the brief,
find internal-link targets, build the on-page checklist) and hands back a
**writing packet**. When the skill runs inside Claude — or any LLM harness —
the AGENT writes the article and makes the editorial calls from that packet; no
API key, no round-trip. Only for headless/cron runs (no agent in the loop) does
`providers.complete` call out, and only when `llm.provider` is set to
"anthropic" or "openai" with the matching key. `draft`/`retitle` therefore
return `mode: "agent"` by default (write it yourself) or `mode: "generated"`."""
from . import index as idxmod
from . import personas, providers

# The content writer operates at the top of the field — see personas.WRITER.
_SYSTEM = personas.WRITER


def brief(cfg, keyword):
    dfs = cfg.get("dataforseo", {})
    s = providers.serp(keyword, dfs.get("location_name"), dfs.get("language_name"))
    return {"keyword": keyword,
            "serp": s.get("organic", [])[:10],
            "questions": s.get("paa", []),
            "related": s.get("related", [])}


def _link_targets(cfg, keyword, corpus_path):
    try:
        idx = idxmod.Index(idxmod.load_corpus(corpus_path))
        return [p for p, _ in idx.link_targets(keyword, k=5)]
    except Exception:
        return []


def _assignment_md(cfg, kw, b, links):
    """The writing packet the agent authors the article from (also the LLM prompt)."""
    comp = "\n".join(f"- {o.get('title')} — {o.get('url')}" for o in b["serp"][:8]) or "- (SERP unavailable — no DataForSEO creds)"
    paa = "\n".join(f"- {q}" for q in b["questions"][:12]) or "- (none returned)"
    lnk = "\n".join(f"- {u}" for u in links) or "- (none — this may be a new pillar page)"
    brand = cfg.get("brand", {}).get("name", "the site")
    return (f"# Writing assignment — target keyword: \"{kw}\"\n\n"
            f"Site/brand: {brand} · {cfg.get('site','')}\n\n"
            f"## Beat these top-ranking competitors (be more useful and specific; do not copy)\n{comp}\n\n"
            f"## Answer these People-Also-Ask questions inside the article (use as H2/H3 where natural)\n{paa}\n\n"
            f"## Weave in contextual internal links to these existing pages (Markdown links)\n{lnk}\n\n"
            f"## Deliverable\n"
            f"- SEO title (≤60 chars, keyword near the front) as `# <title>` on line 1\n"
            f"- meta description (≤155 chars, one clear call to action) as `> meta: <text>` on line 2\n"
            f"- then the article body: front-load the answer, clear H2/H3, no fluff or keyword stuffing.")


def draft(cfg, keyword, corpus_path="corpus.json"):
    """Return {mode:"agent", assignment, …} for the agent to write from (default),
    or {mode:"generated", markdown} when a headless llm.provider is configured."""
    b = brief(cfg, keyword)
    links = _link_targets(cfg, keyword, corpus_path)
    assignment = _assignment_md(cfg, keyword, b, links)
    body = providers.complete(assignment, system=_SYSTEM, cfg_llm=cfg.get("llm", {}),
                              max_tokens=cfg.get("llm", {}).get("max_tokens", 8000))
    if body:
        return {"keyword": keyword, "mode": "generated", "internal_links": links,
                "markdown": body}
    return {"keyword": keyword, "mode": "agent", "internal_links": links,
            "brief": b, "assignment": assignment,
            "instruction": ("Write the full article now in your own output using this "
                            "assignment. You are the writer — do not call an external API.")}


def retitle(cfg, page, keyword="", current_title="", current_meta=""):
    """Rewrite the title tag + meta description for a low-CTR page (goal #5).
    Default mode:"agent" — the agent proposes the options; headless llm.provider
    fills them via the API."""
    task = (f"Rewrite the SEO title tag and meta description to lift CTR for this page.\n"
            f"URL: {page}\nTarget keyword: {keyword or '(infer from URL)'}\n"
            f"Current title: {current_title or '(unknown)'}\n"
            f"Current meta: {current_meta or '(unknown)'}\n\n"
            f"Give 3 distinct title options (≤60 chars, benefit-led, keyword near the front) "
            f"and 1 meta description (≤155 chars with a clear call to action). Return as plain "
            f"lines: 'Title 1: …', 'Title 2: …', 'Title 3: …', 'Meta: …'.")
    out = providers.complete(task, cfg_llm=cfg.get("llm", {}), max_tokens=800)
    if out:
        return {"page": page, "mode": "generated", "suggestions": out}
    return {"page": page, "mode": "agent", "task": task,
            "instruction": "Produce the 3 titles + 1 meta yourself now — you are the writer."}
