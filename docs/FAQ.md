# FAQ & Troubleshooting

### How do I start on a brand-new site?
`mkdir my-site && cd my-site && seo-content-pipeline init --site https://…` — then edit
`config.json`, add keys to `.env`, and run `onboard`. One directory = one site.

### Do I need API keys to use it?
No. With zero credentials you get the full **Site Doctor**, E-E-A-T/topical-authority/
accessibility checks, schema generation, consolidation + internal-link recommenders, and —
when an AI agent drives it — written content. Wire **GSC + DataForSEO** (the two must-haves) to
add rank/CTR/gap/SERP data. Run `integrations` to see what each missing key unlocks.

### Does content drafting need an LLM API key?
Not when an **agent** drives the tool — the agent *is* the model and writes from the packet
`draft` returns. Set `llm.provider` to `anthropic`/`openai` (+ the key) only for unattended/
cron runs with no agent in the loop.

### Will my API keys leak if someone forks the repo?
No. `safety` (run first, and inside `init`) ships a committed `.env.example`, hardens
`.gitignore` to exclude `.env`/`config.json`/service-account JSON/`history/`/outputs, and
**leak-scans tracked files and the working tree** (`.gitignore` only protects *untracked*
files). Add the git hook with `safety --precommit` in a `pre-commit` script to block commits
containing secrets.

### `ingest` says "0 pages" / sitemap 404.
The default `/sitemap.xml` 404s on many sites. The tool **auto-discovers** the sitemap from
`robots.txt` — check that your site declares one there. You can also set the exact `sitemap`
URL in `config.json`.

### The audit flags lots of "orphans" — are they real?
On a **partial crawl** (small `max_pages`) the internal-link graph is incomplete, so pages
whose linkers weren't crawled look orphaned. Raise `max_pages` (e.g. 400+) for trustworthy
orphan/click-depth findings. Large crawls **checkpoint every 50 pages**, so they're safe to run
in the background.

### The audit says my site blocks AI crawlers — is that bad?
It's a **decision, not a bug.** Blocking GPTBot/ClaudeBot/PerplexityBot/Google-Extended via
`robots.txt Disallow: /` removes you from those AI answers (ChatGPT/Perplexity/AI Overviews).
Some sites do it deliberately (content protection). `logs` shows whether AI bots actually fetch
your pages. See [AI-Search.md](AI-Search.md).

### My site is a SPA / React app and the audit looks empty.
Client-rendered pages return near-empty HTML to a raw fetch (and to AI crawlers). The audit
flags likely-CSR pages. Install Playwright and set `render.enabled: true` in `config.json` to
render pages before auditing: `pip install playwright && playwright install chromium`.

### `decay` / `algo` return "need ≥2 snapshots."
They diff over time. Run `gsc` on a cadence (weekly) to build `history/` — after two runs,
decay and algorithm attribution work.

### Should I disavow toxic backlinks?
Almost certainly not. In 2026 SpamBrain auto-ignores spam, low authority ≠ toxic, and most
sites have an audit-hygiene problem, not a toxic-link problem. `toxicity` is deliberately
conservative and says so; only disavow on a manual action or documented negative SEO.

### How do I publish? Does it auto-publish?
`publish <post.json>` uses the configured connector. The default `file` connector writes a
Markdown file for a **git-PR** flow — "auto-publish = an automated PR," never a silent live
push. WordPress/Webflow/Ghost connectors post drafts. Keep a drip cadence; never mass-publish.

### How do I use it from an MCP client (or another CMS)?
`python -m seo_agent mcp` is a stdio MCP server exposing 30 tools. Register it as command
`python -m seo_agent mcp`; set `SEO_CONFIG=<path>` to point at a workspace. This is also how it
integrates with any CMS or client that speaks MCP.

### How does the tool stay current with Google changes?
`radar` watches Google's Search Status Dashboard and flags when the known-updates list
(`algo.py`) is stale; the monthly cadence in [BUILDLOOP.md](../BUILDLOOP.md) turns new updates
and shifts into tool changes.

### Is my data sent anywhere?
Only to the APIs you configure (DataForSEO, Google, your CMS, and — if enabled — an LLM
provider). The core (crawl, audit, index, content packets) is fully local. No telemetry.
