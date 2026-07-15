# Integrations

Every external API is declared once in `seo_agent/integrations.py` — the single source of
truth. From that registry the tool **generates `.env.example`, drives onboarding, and reports
a live capability matrix** (`integrations`). Nothing is hardcoded elsewhere.

## The registry

| Tier | Integration | Auth | Unlocks | Alternatives |
|---|---|---|---|---|
| **must** | Google Search Console | service-account JSON (`gsc_credentials` + `gsc_property`) | rank, CTR, decay, algo attribution, striking-distance, low-CTR | Bing Webmaster Tools API |
| **must** | DataForSEO | `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` | volume, SERP + PAA, backlinks, trends, ranked keywords, competitor gap, AIO detection | Semrush · Ahrefs · SerpApi · Google Ads Keyword Planner |
| recommended | PageSpeed / CrUX | `PAGESPEED_API_KEY` (one Google Cloud key) | Core Web Vitals (lab + field) + accessibility | WebPageTest · CrUX BigQuery |
| recommended | Server access logs | `logs.path` (a file) | crawl budget/waste + AI-crawler coverage | Cloudflare/Fastly export · OnCrawl/JetOctopus |
| recommended | JavaScript rendering | `render.enabled` + `pip install playwright` | accurate audit of SPA/CSR sites | DataForSEO on-page render · a prerender service |
| optional | Anthropic (Claude) | `ANTHROPIC_API_KEY` (+ `llm.provider: anthropic`) | headless drafting | OpenAI · **agent-written (default, no key)** |
| optional | OpenAI | `OPENAI_API_KEY` (+ `llm.provider: openai`) | headless drafting | Anthropic · agent-written |
| optional | WordPress / Webflow / Ghost | `WP_USER`+`WP_APP_PASSWORD` / `WEBFLOW_TOKEN` / `GHOST_ADMIN_KEY` | publishing | git-PR file (default) |
| future | GSC Generative-AI performance | — | AI-search visibility | **blocked**: UI-only, no API yet — use `logs` AI-crawler coverage as the proxy |

Run `seo-content-pipeline integrations` for the live matrix — what's active, what's missing
(and the exact env/config to set), what each gap unlocks, and the alternatives.

## Secrets never leak
`.env.example` is generated from this registry (so it never drifts). `safety`/`init` gitignore
`.env`, `config.json`, the service-account JSON, `history/`, and every output, then leak-scan
tracked files **and** the working tree. See [FAQ → fork-safety](FAQ.md).

## Adding any new API (one entry)
1. Append an entry to `INTEGRATIONS` in `seo_agent/integrations.py` (tier, `env`/`config`,
   `unlocks`, `options`, `docs`).
2. Write a small provider function in `seo_agent/providers.py` using the generic primitive:

   ```python
   def my_metric(target):
       res = providers.http_json(
           "https://api.example.com/v1/metric",
           method="POST",
           headers={"Authorization": f"Bearer {os.environ.get('EXAMPLE_TOKEN')}"},
           body={"target": target},
       )
       return (res or {}).get("value")
   ```
3. That's it — `.env.example`, onboarding, and the capability matrix all pick it up. Wire a
   command/finding where it's used.

## Swapping a provider
DataForSEO's role (volume/SERP/backlinks) can be served by Semrush/Ahrefs/SerpApi — implement
the same provider functions against the new API and point the registry entry's `options` at
it. The rest of the pipeline is provider-agnostic.

## MCP server
`python -m seo_agent mcp` starts a stdlib **stdio JSON-RPC MCP server** exposing 30 tools
(`init`, `onboard`, `audit`, `plan`, `rank`, `logs`, `publish`, …). Register it in any MCP
client as command `python -m seo_agent mcp`; point it at a workspace with `SEO_CONFIG=<path>`.
This is also how the tool integrates with **any CMS or client that speaks MCP**.
