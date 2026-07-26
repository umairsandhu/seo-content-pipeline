# seo-content-pipeline

**The autonomous, closed-loop SEO operating system — runs entirely on your machine.** Point
it at any domain and it takes you 0→100: fork-safe onboarding, a technical Site Doctor,
rank/CTR/backlink/AI-search tracking, an expert strategy, content the agent writes, and — the
part no dashboard does — it **ships the fix (repo PR / CMS / browser), measures the impact
against a holdout, and learns**. Human-gated at every step.

![license](https://img.shields.io/badge/license-open--core-green)
![python](https://img.shields.io/badge/python-%E2%89%A53.9-blue)
![deps](https://img.shields.io/badge/core%20deps-numpy%20%2B%20scikit--learn-orange)
![storage](https://img.shields.io/badge/storage-file--based%20(no%20DB%2C%20no%20server)-lightgrey)
![mcp](https://img.shields.io/badge/MCP-52%20tools-purple)

**No hosting, no SaaS, no database.** Stdlib + `numpy`/`scikit-learn` at the core; every API is
optional and the whole thing **degrades gracefully** — the audit, strategy, drafts, AI-search
and plan run with zero credentials. Drive it from the **Claude Code skill**, the **CLI**, or any
**MCP client**.

## Install & run

**As a Claude Code skill** (Claude runs it and writes the content itself — no API key):
```
/plugin marketplace add umairsandhu/seo-content-pipeline
/plugin install seo-content-pipeline@seo-content-pipeline
```
Then just ask: *"onboard www.example.com"* → Claude runs the guided setup and takes it from there.

**As a standalone CLI:**
```bash
pip install numpy scikit-learn          # core; other APIs optional
python -m seo_agent init --site https://www.example.com   # bootstrap a workspace (any empty dir)
python -m seo_agent wizard              # guided, hand-holding setup (add keys to .env)
python -m seo_agent onboard             # fork-safety → Site Doctor → baseline → BASELINE.md
python -m seo_agent plan                # the co-pilot: ranked "what to do next"
python -m seo_agent serve               # live local dashboard at http://127.0.0.1:8787
```

**As an MCP server:** `python -m seo_agent mcp` → 52 tools in any MCP client.

> **One directory = one site.** `init` scaffolds a clean workspace (`config.json` + `.env` +
> hardened `.gitignore`) and runs fork-safety so keys can never leak. Everything — data, keys,
> reports, the change ledger — stays on your machine.

## The onboarding journey (gated, hand-held)

`init` → **`wizard`** (numbered, ✅/▶/○ status, the exact next step) → **`preflight`** (a 0–100
readiness gate that blocks the baseline until the required accesses are wired in) → **`onboard`**
(baseline) → **`plan`** / **`consult`**. Full script: **[ONBOARDING.md](ONBOARDING.md)**.

The gate asks for two things (both optional to *start*, required for depth):
- **Search performance** — a GSC service account, or import an export: `gsc --csv export.zip`.
- **Market data** — `DATAFORSEO_LOGIN`/`DATAFORSEO_PASSWORD` (or Semrush/Ahrefs).

## What you get — the command map

| Group | Commands | Does |
|---|---|---|
| **Onboard & Doctor** | `init` `wizard` `preflight` `onboard` `safety` `integrations` `audit` `sitemap` `speed` `logs` `schema` `renderdiff` `llmstxt` | Guided setup + fork-safety + the full technical/on-page/CWV/log/structured-data audit |
| **Observe** | `ingest` `gsc` `gsc --csv` `rank` `trends` `backlinks` `ctr` `ga4` | Crawl + track rank/CTR/SERP-features/backlinks; first-party CTR curve; GA4 organic revenue |
| **Decide** | **`plan`** **`consult`** `consolidate` `gap` `competitors` `aio` `pagerank` `decay` `algo` `authority` `eeat` `radar` | One ranked action list · McKinsey-level strategy · cannibalization/301 · competitor sitemap-delta · internal PageRank |
| **Produce** | `brief` `draft` `crew` `refresh` `retitle` `citability` `score` | SERP-grounded briefs & drafts by a multi-agent expert crew; decaying-page refreshes |
| **AI-search / GEO** | `aivis` `entity` `geo` `citability` | Citation share across ChatGPT/Perplexity/Gemini/AI Overviews · entity graph + Wikidata · passage-citability |
| **Control & review** | `control` `pr` `webtask` `autonomy` `review` `approve` `changes` `apply --approved` | Ship fixes via repo PRs / CMS / headless browser — autonomy-gated, human-approved on CLI/email/Slack/Mattermost/WhatsApp |
| **Measure & deliver** | `ledger` `explain` `anomaly` `report --pdf --email` `run --daily\|--monthly` `email` | Causal change ledger + holdout attribution · "why did /x drop?" · anomaly alerts · PDF reports |
| **Autonomy loop** | **`autopilot --daily\|--weekly\|--monthly`** **`serve`** | The 4-agent loop (Audit→Plan→Execute→Report) + the live local dashboard |
| **Scale & packaging** | `projects` `jobs` `edition` `mcp` | Multi-site (agency) portfolio · job queue · edition/entitlements · MCP server |

Full reference: **[docs/Capabilities.md](docs/Capabilities.md)** and **[docs/Commands.md](docs/Commands.md)**.

## The closed loop (why it's different)

Most tools stop at diagnosis. This one runs the whole loop, locally:

```
Diagnose → Decide → Produce → Ship → Measure → Learn ↻
 audit      plan      crew     pr/     ledger    plan (repeats
 anomaly    consult   draft    control  explain   proven wins)
```

- **It ships the fix, not a description** — a git PR that edits meta/schema/redirects, a CMS
  update, or a browser action — through a **human review gate** and your chosen **autonomy mode**
  (`manual` / `approve` / `auto`).
- **It proves what worked** — the causal **ledger** logs every change and attributes the outcome
  vs a **holdout of untouched pages**. `explain <url>` answers "why did this move?" with evidence.
- **Expert-grade** — outputs are written as named personas: a McKinsey-caliber strategist, a top
  technical SEO, an E-E-A-T writer.
- **AI-search native** — measures and optimizes your visibility in AI answers, not just blue links.

## The autonomous daily loop

`autopilot` runs four agent roles over a shared local blackboard (`state/`): **Audit** (situation)
→ **Planner** (a dated backlog with per-item cadence) → **Executor** (ships what's due, drip-capped,
through the safety + review gate) → **Analyst** (attribution + report). `serve` opens a live
dashboard to watch it and approve changes inline. Schedule it with cron / CI / the `/schedule`
skill — on *your* machine. See **[docs/AGENT-LOOP-PLAN.md](docs/AGENT-LOOP-PLAN.md)**.

## Safety & guardrails

- **Fork-safe secrets** — `safety` (run first, and inside `init`) writes `.env.example`, hardens
  `.gitignore`, and leak-scans the tree. Keys never leak.
- **Programmatic-content safety gate** — hard-blocks thin / near-duplicate / boilerplate pages
  before publish (Google's 2026 scaled-content enforcement).
- **Human-in-the-loop** — every content/fix output is proposed and applied as a reviewed PR;
  nothing structural ships without approval.
- **Local & private** — no server, no hosting; your data and keys stay on your machine.

## Integrations (all bring-your-own, all optional)

| Tier | Integration | Unlocks |
|---|---|---|
| must | **Google Search Console** (or a CSV export) | rank, CTR, decay, algo, striking-distance |
| must | **DataForSEO** (or Semrush/Ahrefs) | volume, SERP/PAA, backlinks, trends, gaps |
| recommended | PageSpeed/CrUX · GA4 · server logs · Playwright | CWV · organic revenue · crawl budget · JS rendering |
| recommended | Slack / Mattermost / WhatsApp / email · Resend/SendGrid/SMTP | review + digest + alert delivery |
| optional | OpenAI / Perplexity / Gemini / Anthropic | live AI-visibility tracking (`aivis`); headless drafting |
| optional | WordPress / Webflow / Ghost · GitHub (`gh`) | publishing / repo PRs (git-PR file is the default) |

`integrations` prints a live matrix of what's active/missing and what each unlocks.

## Documentation

- **[Capabilities](docs/Capabilities.md)** — ⭐ the complete step-by-step reference (every command, degradation matrix)
- **[Getting Started](docs/Getting-Started.md)** · **[Command Reference](docs/Commands.md)** · **[Onboarding](ONBOARDING.md)**
- **[Architecture](docs/Architecture.md)** · **[Integrations](docs/Integrations.md)** · **[Site Doctor](docs/Site-Doctor.md)** · **[AI Search](docs/AI-Search.md)**
- **[Agent Loop](docs/AGENT-LOOP-PLAN.md)** · **[Distribution & Runtimes](docs/APP-PLAN.md)** (local-only)
- Commercial: **[Pricing](docs/PRICING.md)** · **[Commercial license](COMMERCIAL.md)** · **[Product strategy](docs/PRODUCT-STRATEGY.md)**
- For the operator: **[Learnings](docs/LEARNINGS.md)** · **[Roadmap](docs/ROADMAP.md)** · **[Playbook](PLAYBOOK.md)** · **[Build loop](BUILDLOOP.md)**

## License

Open-core — the engine is free and open-source (see `LICENSE`). Commercial editions (Pro /
Agency / Enterprise) are **local licenses** for white-label + multi-site/commercial use +
support; see [COMMERCIAL.md](COMMERCIAL.md). No hosting, ever.
