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

from . import (aio, analyze, audit, authority, backlinks, content_score, decay, eeat,
               geo, ingest, integrations, internal, logs, onboard, orchestrate, plan,
               produce, publish, rank, report, safety, schema, speed, trends)
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


TOOLS = [
    ("ingest", "Crawl the configured site's sitemap into corpus.json.",
     {"type": "object", "properties": {}}, _ingest),
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
