"""Integrations registry — the single, declarative source of truth for every API
the skill can use: what tier it is (must / recommended / optional), what env vars
or config it needs, what capabilities it unlocks, and the alternative providers
you could swap in. This is what makes the skill self-configuring / hands-off:

  - onboarding + `.env.example` are GENERATED from this list (register once →
    everything else knows), so adding an API is a one-entry change here;
  - `matrix()` reports what's active vs missing and what each gap costs you;
  - `missing_required()` tells onboarding what must be set before the tool is
    fully operational.

To add ANY new API: append an entry below and write a small provider function
that calls `providers.http_json(...)` (the generic authenticated HTTP primitive).
Nothing else in the codebase needs to change."""
import os

# tier: must (core data), recommended (big capability), optional (nice), future (not yet wireable)
INTEGRATIONS = [
    {"key": "gsc", "name": "Google Search Console", "tier": "must", "kind": "oauth-file",
     "purpose": "Real rank, CTR, impressions, decay, algorithm attribution",
     "env": [], "config": ["gsc_property", "gsc_credentials"],
     "unlocks": ["gsc", "decay", "algo", "striking-distance", "low-CTR", "onboarding baseline"],
     "options": ["Bing Webmaster Tools API (secondary engine)"],
     "docs": "https://developers.google.com/webmaster-tools/search-console-api-original"},
    {"key": "dataforseo", "name": "DataForSEO", "tier": "must", "kind": "api-basic",
     "purpose": "Keyword volume, SERP + People-Also-Ask, backlinks, trends, ranked keywords",
     "env": ["DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"], "config": [],
     "unlocks": ["discover", "gap", "trends", "backlinks", "brief SERP grounding",
                 "content-gap volumes", "AIO detection"],
     "options": ["Semrush API", "Ahrefs API", "SerpApi", "Google Ads Keyword Planner API"],
     "docs": "https://docs.dataforseo.com/v3/"},
    {"key": "pagespeed", "name": "Google PageSpeed / CrUX", "tier": "recommended", "kind": "api-key",
     "purpose": "Core Web Vitals — Lighthouse lab + real-user field data",
     "env": ["PAGESPEED_API_KEY"], "config": [],
     "unlocks": ["speed", "onboarding CWV"],
     "options": ["WebPageTest API", "CrUX BigQuery export"],
     "docs": "https://developers.google.com/speed/docs/insights/v5/get-started"},
    {"key": "logs", "name": "Server access logs", "tier": "recommended", "kind": "file",
     "purpose": "Real crawler behavior: crawl budget/waste + AI-crawler coverage (GPTBot/ClaudeBot/…)",
     "env": [], "config": ["logs.path"],
     "unlocks": ["logs", "crawl-budget", "AI-crawler coverage"],
     "options": ["Cloudflare/Fastly log export", "OnCrawl / JetOctopus log analyzers"],
     "docs": "https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget"},
    {"key": "render", "name": "JavaScript rendering", "tier": "recommended", "kind": "lib",
     "purpose": "Render SPA/CSR pages in headless Chromium before auditing (else they look empty)",
     "env": [], "config": ["render.enabled"],
     "unlocks": ["accurate audit of client-rendered sites"],
     "options": ["Playwright (default; pip install playwright && playwright install chromium)",
                 "DataForSEO on_page browser rendering", "a prerender service"],
     "docs": "https://playwright.dev/python/"},
    {"key": "anthropic", "name": "Anthropic (Claude)", "tier": "optional", "kind": "api-key",
     "purpose": "Headless content drafting (NOT needed when an agent drives the skill)",
     "env": ["ANTHROPIC_API_KEY"], "config": [], "when": ("llm.provider", "anthropic"),
     "unlocks": ["headless draft", "headless retitle"],
     "options": ["OpenAI", "agent-written (default — no key)"],
     "docs": "https://docs.claude.com/en/api"},
    {"key": "openai", "name": "OpenAI", "tier": "optional", "kind": "api-key",
     "purpose": "Headless content drafting (alternative to Anthropic)",
     "env": ["OPENAI_API_KEY"], "config": [], "when": ("llm.provider", "openai"),
     "unlocks": ["headless draft", "headless retitle"],
     "options": ["Anthropic", "agent-written (default — no key)"],
     "docs": "https://platform.openai.com/docs/api-reference"},
    {"key": "wordpress", "name": "WordPress", "tier": "optional", "kind": "api-basic",
     "purpose": "Publish drafts", "env": ["WP_USER", "WP_APP_PASSWORD"],
     "config": [], "when": ("cms.type", "wordpress"),
     "unlocks": ["publish"], "options": ["Webflow", "Ghost", "git-PR file (default)"],
     "docs": "https://developer.wordpress.org/rest-api/"},
    {"key": "webflow", "name": "Webflow", "tier": "optional", "kind": "api-key",
     "purpose": "Publish drafts", "env": ["WEBFLOW_TOKEN"],
     "config": [], "when": ("cms.type", "webflow"),
     "unlocks": ["publish"], "options": ["WordPress", "Ghost", "git-PR file (default)"],
     "docs": "https://developers.webflow.com/"},
    {"key": "ghost", "name": "Ghost", "tier": "optional", "kind": "jwt",
     "purpose": "Publish drafts", "env": ["GHOST_ADMIN_KEY"],
     "config": [], "when": ("cms.type", "ghost"),
     "unlocks": ["publish"], "options": ["WordPress", "Webflow", "git-PR file (default)"],
     "docs": "https://ghost.org/docs/admin-api/"},
    {"key": "ga4", "name": "Google Analytics 4", "tier": "recommended", "kind": "oauth-file",
     "purpose": "Organic sessions, conversions & REVENUE — the executive one-pager's business outcomes",
     "env": ["GA4_PROPERTY_ID"], "config": ["ga4_property_id"],
     "unlocks": ["ga4", "revenue attribution in the ledger", "executive one-pager"],
     "options": ["reuse the GSC service account (share it with the GA4 property, Viewer)"],
     "docs": "https://developers.google.com/analytics/devguides/reporting/data/v1"},
    {"key": "review_channels", "name": "Review & alert channels", "tier": "recommended", "kind": "webhook-or-api",
     "purpose": "Send review requests / digests / alerts to Slack, Mattermost, or WhatsApp; collect approvals",
     "env": ["SLACK_WEBHOOK_URL"], "config": ["review.channels"],
     "unlocks": ["review (multi-channel approve/changes)", "run --email", "anomaly alerts"],
     "options": ["MATTERMOST_WEBHOOK_URL", "WHATSAPP_TOKEN+WHATSAPP_PHONE_ID", "IMAP_* for email reply polling"],
     "docs": "https://api.slack.com/messaging/webhooks"},
    {"key": "bing", "name": "Bing Webmaster Tools", "tier": "optional", "kind": "api-key",
     "purpose": "Secondary search engine — rank/impressions on Bing (and ChatGPT search, which uses Bing)",
     "env": ["BING_WEBMASTER_API_KEY"], "config": [],
     "unlocks": ["bing performance (secondary engine)"],
     "options": ["GSC is the primary engine"],
     "docs": "https://learn.microsoft.com/en-us/bingwebmaster/getting-access"},
    {"key": "email", "name": "Email delivery", "tier": "recommended", "kind": "smtp-or-api",
     "purpose": "Auto-email PDF reports to stakeholders (daily / weekly / monthly cadence)",
     "env": ["SMTP_HOST"], "config": ["report.email_to"],
     "unlocks": ["report --email", "run --email (scheduled PDF delivery)"],
     "options": ["Resend (RESEND_API_KEY)", "SendGrid (SENDGRID_API_KEY)", "any SMTP host"],
     "docs": "https://resend.com/docs/send-with-smtp"},
    {"key": "perplexity", "name": "Perplexity API", "tier": "recommended", "kind": "api-key",
     "purpose": "AI-visibility tracking — mentions + citations in Perplexity answers",
     "env": ["PERPLEXITY_API_KEY"], "config": [],
     "unlocks": ["aivis (Perplexity)"],
     "options": ["OpenAI / Gemini / Anthropic for other engines", "DataForSEO for Google AI Overviews"],
     "docs": "https://docs.perplexity.ai/"},
    {"key": "gemini", "name": "Google Gemini API", "tier": "recommended", "kind": "api-key",
     "purpose": "AI-visibility tracking — mentions in Gemini answers",
     "env": ["GEMINI_API_KEY"], "config": [],
     "unlocks": ["aivis (Gemini)"],
     "options": ["GOOGLE_API_KEY works too", "OpenAI / Perplexity / Anthropic for other engines"],
     "docs": "https://ai.google.dev/"},
    {"key": "ai_search_visibility", "name": "GSC Generative AI performance", "tier": "future",
     "kind": "oauth-file",
     "purpose": "AI-Overview / AI-Mode impressions (June 2026). UI-only today — NO API yet; wire when it ships",
     "env": [], "config": [],
     "unlocks": ["ai-search visibility (pending API)"],
     "options": ["server logs for AI-crawler coverage (proxy, available now)", "aivis (live cross-engine tracking now)"],
     "docs": "https://developers.google.com/search/blog"},
]


def _get(cfg, dotted):
    cur = cfg
    for part in dotted.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


def active(cfg, it):
    if it["tier"] == "future":
        return False
    if not (it["env"] or it.get("config")):
        return False
    if it.get("when") and _get(cfg, it["when"][0]) != it["when"][1]:
        return False
    env_ok = all(os.environ.get(e) for e in it["env"])
    cfg_ok = all(_get(cfg, c) for c in it.get("config", []))
    return env_ok and cfg_ok


def matrix(cfg):
    out = []
    for it in INTEGRATIONS:
        missing = ([e for e in it["env"] if not os.environ.get(e)]
                   + [c for c in it.get("config", []) if not _get(cfg, c)])
        out.append({**it, "active": active(cfg, it), "missing": missing})
    return out


def missing_required(cfg):
    return [it for it in matrix(cfg) if it["tier"] == "must" and not it["active"]]


def env_example():
    """Generate .env.example from the registry (so it never drifts from the code)."""
    L = ["# Copy to .env and fill in. .env is gitignored — NEVER commit real values.",
         "# Generated from the integrations registry (seo_agent/integrations.py).",
         "# Leave a line blank to keep that capability disabled (everything degrades).", ""]
    for tier, label in [("must", "Required — core data"), ("recommended", "Recommended"),
                        ("optional", "Optional")]:
        seen = []
        for it in INTEGRATIONS:
            if it["tier"] != tier or not it["env"]:
                continue
            seen.append(f"# {it['name']}: {it['purpose']}")
            seen += [f"{e}=" for e in it["env"]]
        if seen:
            L += [f"# ── {label} ──"] + seen + [""]
    L += ["# GSC uses a service-account JSON file (set `gsc_credentials` in config.json), not env.",
          "# Content drafting needs NO key when an agent drives the skill (agent writes it).",
          "# Server logs: set `logs.path` in config.json (a file path, not a secret).",
          "# Optional switches (not secrets): SEO_EMBEDDINGS=1 · SEO_CONFIG=config.json"]
    return "\n".join(L) + "\n"


def render_md(cfg):
    m = matrix(cfg)
    L = ["# Integrations — capability matrix", ""]
    for tier, label in [("must", "Must-have"), ("recommended", "Recommended"),
                        ("optional", "Optional"), ("future", "Future")]:
        rows = [it for it in m if it["tier"] == tier]
        if not rows:
            continue
        L.append(f"## {label}")
        for it in rows:
            mark = "✅" if it["active"] else ("⏳" if tier == "future" else "⬜")
            L.append(f"- {mark} **{it['name']}** — {it['purpose']}")
            if it["missing"]:
                L.append(f"    - set: {', '.join(it['missing'])}")
            L.append(f"    - unlocks: {', '.join(it['unlocks'])}")
            if it.get("options"):
                L.append(f"    - alternatives: {', '.join(it['options'])}")
        L.append("")
    miss = missing_required(cfg)
    if miss:
        L.append("> ⚠ Missing must-have integrations: " + ", ".join(i["name"] for i in miss))
    return "\n".join(L)
