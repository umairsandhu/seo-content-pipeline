"""The consultant — a McKinsey/Google-caliber strategic SEO engagement in one command.
It assembles every signal the tool produces into one situation pack and reasons over
it as the STRATEGIST persona: where you are, what's really blocking growth, the 3–5
plays that matter, a sequenced 90-day + quarterly roadmap, projected impact, and risks.

Agent-native: returns the assembled evidence + the strategist brief for the agent to
write the strategy (Pyramid Principle: answer first). With `llm.provider` set it calls
a headless model. This is the tool's top-of-funnel "wow" deliverable. Site-agnostic."""
from . import personas, providers


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def situation(cfg):
    """Compact evidence pack — only the decision-relevant numbers, degrades per signal."""
    from . import analyze, audit, authority_flow, backlinks, citability, decay, entity, geo, history
    from .index import Index, load_corpus
    pack = {"site": cfg.get("site", ""), "brand": (cfg.get("brand", {}) or {}).get("name", ""),
            "competitors": cfg.get("competitors", [])}
    a = _safe(lambda: audit.report(cfg))
    if a:
        pack["technical"] = {"counts": a.get("counts"), "orphans": a.get("links", {}).get("orphans"),
                             "top_findings": [f["msg"] for f in a.get("findings", [])[:8]]}
    opp = _safe(lambda: analyze.gsc_opportunities(cfg))
    if opp:
        pack["gsc"] = {"striking": [(r["query"], round(r["position"], 1), r["impressions"])
                                    for r in opp["striking"][:12]],
                       "low_ctr": [(r["page"], r["impressions"], round(r["ctr"], 3)) for r in opp["low_ctr"][:8]]}
    pack["decay"] = _safe(lambda: {k: len(v or []) for k, v in (decay.detect(cfg) or {}).items()})
    pack["geo"] = _safe(lambda: {"avg": geo.report(cfg)["avg_score"]})
    pack["citability"] = _safe(lambda: {"avg": citability.report(cfg)["avg"]})
    en = _safe(lambda: entity.report(cfg))
    if en:
        pack["entity"] = {"wikidata": bool(en["wikidata"]), "sameAs": len(en["sameAs_present"]),
                          "salience": en["salience"]}
    pack["authority_flow"] = _safe(lambda: {"starved_pillars": len(authority_flow.report(cfg)["starved_pillars"])})
    pack["backlinks"] = _safe(lambda: backlinks.link_gap(cfg)[:8] if cfg.get("competitors") else None)
    pack["gaps"] = _safe(lambda: [g["keyword"] for g in analyze.competitor_gap(cfg, Index(load_corpus()))[:10]]
                         if cfg.get("competitors") else None)
    av = _safe(lambda: history.latest(cfg, "aivis"))
    if av and av.get("data"):
        rows = av["data"]
        pack["ai_visibility"] = {"brand_sov": round(sum(r.get("mentioned") for r in rows) / max(len(rows), 1), 2)}
    return pack


_BRIEF = (
    "Using ONLY the evidence pack below, produce a board-ready SEO growth strategy. Structure (Pyramid "
    "Principle — lead with the answer):\n"
    "1. **Executive summary** — the single biggest opportunity and the recommendation, in 3 sentences.\n"
    "2. **Situation** — where the site stands (demand captured vs available, technical health, authority "
    "vs competitors, AI-search visibility). Quantify.\n"
    "3. **Diagnosis** — the ROOT causes blocking growth (separate demand vs supply vs authority vs "
    "technical). Name what most people would get wrong here.\n"
    "4. **Strategy** — the 3–5 plays that matter, each with the mechanism (why it will rank/convert), the "
    "expected impact, and why it beats the alternatives. Kill everything else explicitly.\n"
    "5. **90-day roadmap + quarterly horizons** — sequenced, with owners and the success metric per play.\n"
    "6. **Projected impact** — a defensible traffic/▲ estimate with stated assumptions.\n"
    "7. **Risks & what would falsify the plan.**\n"
    "Be decisive, quantify, cite the pack's numbers, state assumptions, and refuse vague 'do more content' "
    "advice without a ranking mechanism.")


def run(cfg):
    pack = situation(cfg)
    import json
    prompt = _BRIEF + "\n\n## Evidence pack\n```json\n" + json.dumps(pack, indent=1)[:6000] + "\n```"
    out = providers.complete(prompt, system=personas.system("strategist", cfg=cfg),
                             cfg_llm=cfg.get("llm"))
    if out:
        return {"mode": "generated", "strategy": out, "pack": pack}
    return {"mode": "agent", "pack": pack,
            "packet": f"# SEO strategy engagement — {pack['site']}\n\n"
                      "Act as the STRATEGIST persona (top SEO strategy consultant + ex-Google Search "
                      "engineer). " + _BRIEF + "\n\n## Evidence pack\n```json\n"
                      + json.dumps(pack, indent=1)[:6000] + "\n```"}


def render_md(cfg, r):
    return r.get("strategy") or r.get("packet") or "_no data — run `ingest` + `onboard` first_"
