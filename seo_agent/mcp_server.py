"""Layer 4 — MCP capability (goal #4). A stdlib-only stdio MCP server that
exposes the whole pipeline as tools, so Claude Desktop / Claude Code / any MCP
client can drive it — and publish to any CMS — without the pipeline's CLI.

Speaks JSON-RPC 2.0 over stdin/stdout (one JSON object per line), implementing
`initialize`, `tools/list`, and `tools/call`. No external deps.

Run:   python -m seo_agent mcp            (config from $SEO_CONFIG or ./config.json)
Register in an MCP client as command `python -m seo_agent mcp`."""
import json
import os
import sys

from . import (aio, aivis, analyze, anomaly, audit, authority, authority_flow, backlinks,
               citability, competitors, consult, content_score, crew, decay, eeat, entity, ga4,
               geo, ingest, integrations, internal, intl, ledger, local, logs, onboard, orchestrate,
               plan, produce, prospect, publish, rank, refresh, remediate, report, review, safety,
               schema, site_control, speed, trends, wizard)
from . import explain as explain_mod
from . import config as cfgmod
from .index import Index, load_corpus

PROTOCOL = "2025-06-18"


def _cfg():
    return cfgmod.load(os.environ.get("SEO_CONFIG", "config.json"))


# ── tool implementations: each returns a string ─────────────────────────────
def _ingest(a):
    return f"ingested {len(ingest.build(_cfg()))} pages → corpus.json"


def _analyze(a):
    cfg = _cfg()
    _, rep = analyze.report(cfg, a.get("keywords", []))
    open("recommendations.md", "w").write(analyze.render_md(cfg, rep))
    return analyze.render_md(cfg, rep)


def _discover(a):
    rows = analyze.discover(a["seed"], _cfg())
    return json.dumps(rows, ensure_ascii=False, indent=1) if rows else "no results (need DataForSEO creds)"


def _research(a):
    return json.dumps(analyze.content_gaps(Index(load_corpus()), a["keywords"], _cfg()),
                      ensure_ascii=False, indent=1)


def _brief(a):
    return json.dumps(produce.brief(_cfg(), a["keyword"]), ensure_ascii=False, indent=1)


def _draft(a):
    d = produce.draft(_cfg(), a["keyword"])
    # mode "agent" → hand the MCP client's model the writing packet to author from
    return d["markdown"] if d["mode"] == "generated" else d["assignment"]


def _gsc(a):
    opp = analyze.gsc_opportunities(_cfg())
    return json.dumps(opp, ensure_ascii=False, indent=1) if opp else "GSC not configured"


def _decay(a):
    return json.dumps(decay.detect(_cfg()), ensure_ascii=False, indent=1)


def _trends(a):
    return json.dumps(trends.scan(_cfg(), a["seeds"]), ensure_ascii=False, indent=1)


def _backlinks(a):
    return json.dumps(backlinks.link_gap(_cfg()), ensure_ascii=False, indent=1)


def _run(a):
    _, md = orchestrate.run(_cfg(), a.get("keywords", []), monthly=a.get("monthly", False))
    return md


def _publish(a):
    return json.dumps(publish.publish(_cfg(), a["post"]), ensure_ascii=False, indent=1)


def _safety(a):
    return json.dumps(safety.check(_cfg()), ensure_ascii=False, indent=1)


def _init(a):
    return json.dumps(onboard.init(site=a.get("site")), ensure_ascii=False, indent=1)


def _onboard(a):
    _, md = onboard.run(_cfg(), a.get("keywords", []))
    return md


def _audit(a):
    cfg = _cfg()
    rep = audit.report(cfg)
    return audit.render_md(cfg, rep)


def _speed(a):
    cfg = _cfg()
    urls = a.get("urls") or [c.get("final_url") or c["url"] for c in load_corpus()][:8]
    return json.dumps(speed.check(cfg, urls), ensure_ascii=False, indent=1)


def _gap(a):
    return json.dumps(analyze.competitor_gap(_cfg(), Index(load_corpus())), ensure_ascii=False, indent=1)


def _aio(a):
    cfg = _cfg()
    opp = analyze.gsc_opportunities(cfg)
    if not opp:
        return "GSC not configured"
    return aio.render_md(cfg, aio.annotate(cfg, opp["striking"]))


def _logs(a):
    cfg = _cfg()
    path = a.get("path") or cfg.get("logs", {}).get("path")
    if not path:
        return "no log path (pass `path` or set logs.path in config)"
    return logs.render_md(cfg, logs.analyze(cfg, path, verify=a.get("verify", False)))


def _integrations(a):
    return integrations.render_md(_cfg())


def _rank(a):
    cfg = _cfg()
    rows = rank.track(cfg, a.get("keywords"))
    return rank.render_md(cfg, rows, rank.movement(cfg))


def _plan(a):
    cfg = _cfg()
    return plan.render_md(cfg, plan.build(cfg))


def _schema(a):
    cfg = _cfg()
    return schema.generate(cfg, a["url"]) if a.get("url") else "\n".join(schema.missing(cfg)[:30])


def _score(a):
    return content_score.render_md(content_score.score(_cfg(), a["keyword"], a["url"]))


def _eeat(a):
    cfg = _cfg()
    return eeat.render_md(cfg, eeat.report(cfg))


def _authority(a):
    cfg = _cfg()
    return authority.render_md(cfg, authority.clusters(cfg))


def _consolidate(a):
    cfg = _cfg()
    return internal.render_md(cfg, internal.consolidation(cfg))


def _toxicity(a):
    return json.dumps(backlinks.toxicity(_cfg()), ensure_ascii=False, indent=1)


def _inlinks(a):
    return json.dumps(internal.inbound_suggestions(_cfg(), a["url"]), ensure_ascii=False, indent=1)


def _geo(a):
    cfg = _cfg()
    return geo.render_md(cfg, geo.report(cfg))


def _autolink(a):
    cfg = _cfg()
    return internal.render_link_plan(cfg, internal.link_plan(cfg))


def _report(a):
    return "wrote " + report.build(_cfg())


def _aivis(a):
    return aivis.render_md(_cfg(), aivis.run(_cfg()))


def _entity(a):
    return entity.render_md(_cfg(), entity.report(_cfg()))


def _citability(a):
    return citability.render_md(_cfg(), citability.report(_cfg()))


def _pagerank(a):
    return authority_flow.render_md(_cfg(), authority_flow.report(_cfg()))


def _refresh(a):
    return refresh.render_md(_cfg(), refresh.packet(_cfg(), a["url"]))


def _prospect(a):
    return prospect.render_md(_cfg(), prospect.run(_cfg()))


def _remediate(a):
    return remediate.render_md(_cfg(), remediate.plan(_cfg()))


def _intl(a):
    return intl.render_md(_cfg(), intl.report(_cfg()))


def _consult(a):
    return consult.render_md(_cfg(), consult.run(_cfg()))


def _crew(a):
    cfg = _cfg()
    p = crew.article(cfg, a["target"]) if a.get("kind", "article") == "article" else crew.change(cfg, a["target"])
    return crew.render_md(cfg, p)


def _wizard(a):
    return wizard.render_md(_cfg(), wizard.next_step(_cfg()))


def _control(a):
    ch = dict(a); op = ch.pop("op")
    return site_control.render_md(_cfg(), site_control.change(_cfg(), op, **ch))


def _ledger(a):
    return ledger.render_md(_cfg())


def _learn(a):
    from . import learn
    return learn.render_md(_cfg())


def _practices(a):
    from . import practices
    return practices.render_md(_cfg())


def _voice(a):
    from . import voice
    return voice.render_md(_cfg())


def _sitediff(a):
    from . import sitediff
    return sitediff.render_md(_cfg())


def _zeroclick(a):
    from . import zeroclick
    return zeroclick.render_md(_cfg())


def _tip(a):
    from . import tips
    return tips.render_md(_cfg())


def _diagnose(a):
    from . import diagnose
    return diagnose.render_md(_cfg())


def _sf(a):
    from . import sfimport
    cfg = _cfg()
    r = sfimport.import_csv(cfg, a["paths"]) if a.get("paths") else sfimport.auto_import(cfg)
    return sfimport.render_md(cfg, r)


def _repurpose(a):
    r = produce.repurpose(_cfg(), a["url"])
    return r.get("derivatives") or r.get("packet") or r.get("error", "")


def _brain(a):
    from . import brain
    if a.get("add"):
        brain.add(_cfg(), a.get("kind", "fact"), a["add"], source="manual")
    return brain.render_md(_cfg())


def _cms(a):
    from . import cms_extra
    return cms_extra.render_md(_cfg())


def _deliver(a):
    from . import deliver
    r = deliver.deliver(_cfg(), a.get("files") or ["report.pdf"], note=a.get("note", ""))
    return deliver.render_md(_cfg(), r)


def _feedback(a):
    from . import deliver
    import json as _json
    return _json.dumps(deliver.feedback(_cfg(), a["text"], about=a.get("about", "")))


def _explain(a):
    return explain_mod.render_md(_cfg(), explain_mod.explain(_cfg(), a["url"]))


def _review(a):
    cfg = _cfg()
    review.request(cfg)
    return review.status_md(cfg)


def _ga4(a):
    return ga4.render_md(_cfg(), ga4.organic(_cfg()))


def _competitors(a):
    return competitors.render_md(_cfg(), competitors.delta(_cfg()))


def _anomaly(a):
    return anomaly.render_md(_cfg(), anomaly.detect(_cfg()))


def _autopilot(a):
    from . import autopilot
    return autopilot.render_md(_cfg(), autopilot.cycle(_cfg(), cadence=a.get("cadence", "daily"), deliver=False))


TOOLS = [
    ("ingest", "Crawl the configured site's sitemap into corpus.json.",
     {"type": "object", "properties": {}}, _ingest),
    ("aivis", "AI-visibility: brand mentions + citations across ChatGPT/Perplexity/Gemini/AI Overviews.",
     {"type": "object", "properties": {}}, _aivis),
    ("entity", "Entity graph: Wikidata QID, sameAs profiles, Organization JSON-LD, brand salience.",
     {"type": "object", "properties": {}}, _entity),
    ("citability", "Passage-citability — how extractable each page is for AI answers.",
     {"type": "object", "properties": {}}, _citability),
    ("pagerank", "Internal PageRank / authority flow — starved pillars + link hoarders.",
     {"type": "object", "properties": {}}, _pagerank),
    ("refresh", "Content-refresh packet for a URL (diagnose staleness → rewrite → verify).",
     {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, _refresh),
    ("prospect", "Link-acquisition prospects from the competitor backlink gap.",
     {"type": "object", "properties": {}}, _prospect),
    ("remediate", "Ordered, human-gated remediation plan from the audit.",
     {"type": "object", "properties": {}}, _remediate),
    ("intl", "hreflang / international validation.",
     {"type": "object", "properties": {}}, _intl),
    ("consult", "McKinsey/Google-level SEO growth strategy from all signals.",
     {"type": "object", "properties": {}}, _consult),
    ("crew", "Multi-agent crew brief: research→write→tech-SEO→publish (article) or diagnose→plan→apply (change).",
     {"type": "object", "properties": {"kind": {"type": "string", "enum": ["article", "change"]},
                                       "target": {"type": "string"}}, "required": ["target"]}, _crew),
    ("wizard", "Guided onboarding — the next best setup step with handholding.",
     {"type": "object", "properties": {}}, _wizard),
    ("control", "Full site control: create/update_meta/update_content/delete/redirect (autonomy-gated).",
     {"type": "object", "properties": {"op": {"type": "string"}, "id": {"type": "string"},
                                       "url": {"type": "string"}, "title": {"type": "string"},
                                       "description": {"type": "string"}}, "required": ["op"]}, _control),
    ("ledger", "Change log + causal attribution (before/after vs a holdout of untouched pages).",
     {"type": "object", "properties": {}}, _ledger),
    ("learn", "What's working — impact of changes by day/week/month + cross-site 'best change types'.",
     {"type": "object", "properties": {}}, _learn),
    ("practices", "Best practices learned & applied on this site — found → fixed → measured, with live numbers.",
     {"type": "object", "properties": {}}, _practices),
    ("voice", "Measure the site's existing brand voice → stored in the brain → every future draft matches it.",
     {"type": "object", "properties": {}}, _voice),
    ("sitediff", "What changed on YOUR site between crawls — noindex regressions, meta/schema/content drift (24/7 monitoring via cron).",
     {"type": "object", "properties": {}}, _sitediff),
    ("zeroclick", "Zero-click KPIs: the impressions-vs-clicks alligator, branded-demand trend, and the shipped-vs-moved correlation view.",
     {"type": "object", "properties": {}}, _zeroclick),
    ("tip", "Today's sourced SEO tidbit — the tool teaches while it works (library fed by new talks/studies).",
     {"type": "object", "properties": {}}, _tip),
    ("diagnose", "Site-level 'why is traffic down?' — ranked differential diagnosis across ledger, sitediff, Google updates, zero-click erosion, decay, anomalies.",
     {"type": "object", "properties": {}}, _diagnose),
    ("sf", "Import Screaming Frog exports (Internal:All CSV/zip/dir) — bootstrap or enrich the corpus + cross-check crawlers; no paths = auto-import sf-exports/.",
     {"type": "object", "properties": {"paths": {"type": "array", "items": {"type": "string"}}}}, _sf),
    ("repurpose", "One article → zero-click derivatives: no-link LinkedIn post, X thread, newsletter section, quotable stat (voice-aware).",
     {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, _repurpose),
    ("brain", "Continuous self-learning memory: client taste, proven playbooks, lessons (auto-injected into every persona).",
     {"type": "object", "properties": {"add": {"type": "string"},
                                       "kind": {"type": "string", "enum": ["fact", "lesson", "preference", "playbook"]}}}, _brain),
    ("cms", "Every CMS connector (WordPress/Webflow/Ghost/Shopify/Contentful/Strapi/Sanity/HubSpot/Drupal/Joomla/Wix/Notion) + required env vars.",
     {"type": "object", "properties": {}}, _cms),
    ("deliver", "Send deliverables to the client via email and/or their Google Drive folder; logs the delivery for the feedback loop.",
     {"type": "object", "properties": {"files": {"type": "array", "items": {"type": "string"}},
                                       "note": {"type": "string"}}}, _deliver),
    ("feedback", "Record the client's reaction to delivered work — distills into the brain as taste for all future output.",
     {"type": "object", "properties": {"text": {"type": "string"}, "about": {"type": "string"}},
      "required": ["text"]}, _feedback),
    ("explain", "Diagnose why a page's traffic changed — vs our change log, GSC trend, and Google updates.",
     {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, _explain),
    ("review", "Send queued changes/drafts to reviewers (CLI/email/Slack/Mattermost/WhatsApp) + show status.",
     {"type": "object", "properties": {}}, _review),
    ("ga4", "GA4 organic sessions, conversions & revenue (business outcomes).",
     {"type": "object", "properties": {}}, _ga4),
    ("competitors", "Monthly competitor sitemap delta — what they newly published.",
     {"type": "object", "properties": {}}, _competitors),
    ("anomaly", "Anomaly/regression radar — indexation drops, traffic cliffs, rank drops, AI-Overview appearance.",
     {"type": "object", "properties": {}}, _anomaly),
    ("autopilot", "Run one autonomous cycle: Audit → Plan (dated) → Execute (dispatch due, gated) → Report.",
     {"type": "object", "properties": {"cadence": {"type": "string", "enum": ["daily", "weekly", "monthly"]}}}, _autopilot),
    ("analyze", "Full SEO report (cannibalization, gaps, GSC) → recommendations.md.",
     {"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}}}, _analyze),
    ("discover", "DataForSEO keyword ideas for a seed.",
     {"type": "object", "properties": {"seed": {"type": "string"}}, "required": ["seed"]}, _discover),
    ("research", "Dedup verdict + internal-link targets for keywords.",
     {"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}}, "required": ["keywords"]}, _research),
    ("brief", "SERP + People-Also-Ask outline for a keyword.",
     {"type": "object", "properties": {"keyword": {"type": "string"}}, "required": ["keyword"]}, _brief),
    ("draft", "Write a full SERP-grounded article draft for a keyword (needs ANTHROPIC_API_KEY).",
     {"type": "object", "properties": {"keyword": {"type": "string"}}, "required": ["keyword"]}, _draft),
    ("gsc", "Google Search Console striking-distance + low-CTR opportunities.",
     {"type": "object", "properties": {}}, _gsc),
    ("decay", "Content decay: queries losing rank + pages losing clicks (needs GSC history).",
     {"type": "object", "properties": {}}, _decay),
    ("trends", "Emerging / rising keywords for seeds.",
     {"type": "object", "properties": {"seeds": {"type": "array", "items": {"type": "string"}}}, "required": ["seeds"]}, _trends),
    ("backlinks", "Backlink gap — referring domains to pursue for outreach.",
     {"type": "object", "properties": {}}, _backlinks),
    ("run", "Full weekly/monthly orchestration run → digest.md.",
     {"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}, "monthly": {"type": "boolean"}}}, _run),
    ("publish", "Publish a post via the configured CMS connector.",
     {"type": "object", "properties": {"post": {"type": "object"}}, "required": ["post"]}, _publish),
    ("safety", "Fork-safety check: write .env.example, harden .gitignore, leak-scan the repo.",
     {"type": "object", "properties": {}}, _safety),
    ("init", "Bootstrap a fresh site-agnostic workspace (config.json + .env + fork-safety).",
     {"type": "object", "properties": {"site": {"type": "string"}}}, _init),
    ("onboard", "Run the first-time onboarding (fork-safety → audit → speed → gaps) → BASELINE.md.",
     {"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}}}, _onboard),
    ("audit", "Site Doctor: sitemap/robots/llms.txt, metadata, H1, canonical, dedup, content depth, internal links.",
     {"type": "object", "properties": {}}, _audit),
    ("speed", "Core Web Vitals (PageSpeed lab + CrUX field) for key URLs.",
     {"type": "object", "properties": {"urls": {"type": "array", "items": {"type": "string"}}}}, _speed),
    ("gap", "Competitor content gap — keywords 2–3 competitors rank for that you don't.",
     {"type": "object", "properties": {}}, _gap),
    ("aio", "AI-Overview-adjusted CTR: re-rank striking-distance queries by real AIO-aware upside.",
     {"type": "object", "properties": {}}, _aio),
    ("logs", "Server log-file analysis: Google/AI-crawler hits, crawl waste, AI-crawler coverage.",
     {"type": "object", "properties": {"path": {"type": "string"}, "verify": {"type": "boolean"}}}, _logs),
    ("integrations", "API capability matrix: what's active/missing, what each unlocks, alternatives.",
     {"type": "object", "properties": {}}, _integrations),
    ("rank", "Track positions + SERP features (AIO/snippet/PAA/video/shopping) over time + movement.",
     {"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}}}, _rank),
    ("plan", "The co-pilot: fuse every signal into one ranked 'what to do next' action plan.",
     {"type": "object", "properties": {}}, _plan),
    ("schema", "Generate JSON-LD (BlogPosting/Organization/Breadcrumb) for a URL, or list pages missing it.",
     {"type": "object", "properties": {"url": {"type": "string"}}}, _schema),
    ("score", "Content comprehensiveness: score a page vs SERP competitors; surface missing subtopics.",
     {"type": "object", "properties": {"keyword": {"type": "string"}, "url": {"type": "string"}},
      "required": ["keyword", "url"]}, _score),
    ("eeat", "E-E-A-T signal audit: author bylines, dates, citations, trust pages, HTTPS.",
     {"type": "object", "properties": {}}, _eeat),
    ("authority", "Topical-authority structure: topic clusters, pillar presence, internal-link density.",
     {"type": "object", "properties": {}}, _authority),
    ("consolidate", "Consolidation plan: which cannibalizing page to keep, which to 301-redirect.",
     {"type": "object", "properties": {}}, _consolidate),
    ("toxicity", "Backlink toxicity review (conservative — disavow is rarely needed in 2026).",
     {"type": "object", "properties": {}}, _toxicity),
    ("inlinks", "Reverse internal-link recommender: existing pages that should link to a target URL.",
     {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, _inlinks),
    ("geo", "GEO/AEO readiness score: extractability, schema, AI-crawler access, E-E-A-T per page.",
     {"type": "object", "properties": {}}, _geo),
    ("autolink", "Batch internal-link plan: for under-linked pages, which pages should link to them.",
     {"type": "object", "properties": {}}, _autolink),
    ("report", "Generate a shareable self-contained HTML dashboard (report.html).",
     {"type": "object", "properties": {}}, _report),
]
_DISPATCH = {name: fn for name, _, _, fn in TOOLS}


def _handle(req):
    m, rid = req.get("method"), req.get("id")
    if m == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
            "serverInfo": {"name": "seo-content-pipeline", "version": "1.0"}}}
    if m in ("notifications/initialized", "notifications/cancelled"):
        return None
    if m == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": [
            {"name": n, "description": d, "inputSchema": s} for n, d, s, _ in TOOLS]}}
    if m == "tools/call":
        p = req.get("params", {})
        fn = _DISPATCH.get(p.get("name"))
        if not fn:
            return {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32601, "message": f"unknown tool {p.get('name')}"}}
        try:
            text = fn(p.get("arguments", {}) or {})
            return {"jsonrpc": "2.0", "id": rid,
                    "result": {"content": [{"type": "text", "text": text}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": rid,
                    "result": {"isError": True, "content": [{"type": "text", "text": f"error: {e}"}]}}
    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": f"unknown method {m}"}}


def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            resp = _handle(json.loads(line))
        except Exception as e:
            resp = {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32700, "message": f"parse error: {e}"}}
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
