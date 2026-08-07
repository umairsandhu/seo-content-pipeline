# seo-content-pipeline

**The autonomous, closed-loop SEO operating system — runs entirely on your machine.** Point
it at any domain and it takes you 0→100: fork-safe onboarding, a technical Site Doctor,
rank/CTR/backlink/AI-search tracking, an expert strategy, content the agent writes, and — the
part dashboards don't do — it **ships the fix straight into your CMS (13 connectors) or as a
repo PR, measures the impact against a holdout at day/week/month, and learns**: what worked
here, what worked across every site it has ever touched (anonymized), and how *you* like
your work delivered. Human-gated at every step.

![license](https://img.shields.io/badge/license-open--core-green)
![python](https://img.shields.io/badge/python-%E2%89%A53.9-blue)
![deps](https://img.shields.io/badge/core%20deps-numpy%20%2B%20scikit--learn-orange)
![storage](https://img.shields.io/badge/storage-file--based%20(no%20DB%2C%20no%20server)-lightgrey)
![mcp](https://img.shields.io/badge/MCP-59%20tools-purple)
![tests](https://img.shields.io/badge/tests-71%20passing-brightgreen)

**No hosting, no SaaS, no database.** Stdlib + `numpy`/`scikit-learn` at the core; every API is
optional and the whole thing **degrades gracefully** — the audit, strategy, drafts, AI-search
and plan run with zero credentials. Drive it from the **Claude Code skill**, the **CLI**, or any
**MCP client**.

> **Status: beta.** A 3-site pilot is running now; the measured case study (real ledger
> numbers) lands with v1. Until then, every claim you can verify yourself in 2 minutes:

```bash
pip install numpy scikit-learn
python -m seo_agent demo        # builds a full synthetic workspace — zero keys, zero network
cd seo-demo && python -m seo_agent start   # the guided dashboard opens in your browser
```

## What's inside (the 60-second tour)

- 🩺 **Site Doctor** — full technical/on-page/CWV/structured-data/log audit, plus AI-search
  readiness (GEO score, passage citability, entity graph, `llms.txt`).
- 🧭 **A co-pilot that decides** — `plan` ranks everything by impact×confidence÷effort;
  `consult` writes a McKinsey-grade strategy from your actual data.
- ✍️ **An expert crew that produces** — researcher → strategist → writer → editor → tech-SEO
  personas turn SERP + People-Also-Ask data into answer-first, citable drafts.
- 🚀 **Hands that ship** — create/update/delete straight into **WordPress, Webflow, Ghost,
  Shopify, Contentful, Strapi, Sanity, HubSpot, Drupal, Joomla, Wix, Notion** — or a git-PR
  file flow with zero creds. Every change goes through a safety gate + your review.
- 📏 **Proof, not vibes** — a causal change ledger measures every shipped change vs a holdout
  of untouched pages at **+7 / +28 / +90 days**.
- 🧠 **A brain that never forgets** — outcomes distill into *proven playbooks*, client
  feedback distills into *taste*, both are auto-injected into every prompt, and an anonymized
  cross-site store means every new site cold-starts from everything learned before.
- 📬 **Delivery + feedback loop** — reports go to your client by email or straight into their
  Google Drive folder; their replies are captured and learned from.
- 🤖 **A 4-agent autopilot** — Audit → Plan → Execute → Report on a daily/weekly cadence,
  with a live local dashboard (`serve`) for inline approvals.

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

**As an MCP server:** `python -m seo_agent mcp` → 57 tools in any MCP client.

> **One directory = one site.** `init` scaffolds a clean workspace (`config.json` + `.env` +
> hardened `.gitignore`) and runs fork-safety so keys can never leak. Everything — data, keys,
> reports, the change ledger — stays on your machine.

## How you actually use it — three modes

**1 · Try it (5 minutes, zero keys).** `python -m seo_agent demo` builds a synthetic
workspace with measured wins and one honest loss, then `start` opens the guided dashboard.
You'll see exactly what the loop does before connecting anything real.

**2 · Point it at your site (~20 minutes).** In an empty folder:
```bash
python -m seo_agent init --site https://your-site.com
python -m seo_agent start        # the dashboard opens and walks you through every step
```
The dashboard's **Getting-started panel** shows your setup as numbered steps with the exact
next command; `config` shows every setting slot with a hint (drop your GSC key file in the
folder and it's auto-detected — preflight even tells you which service-account email to
invite). No Search Console API? `gsc --csv <export.zip>` imports a normal export.

**3 · Let it run (15 min of your attention per day).** Two cron lines make it a local,
self-improving agent:
```cron
30 8 * * *  cd ~/sites/your-site && python3 -m seo_agent gsc && python3 -m seo_agent autopilot --daily
0  9 * * 5  cd ~/sites/your-site && python3 -m seo_agent report --pdf && python3 -m seo_agent deliver report.pdf
```
Every morning it audits, plans, and queues changes **behind your approval**; you approve or
decline in the dashboard (your notes teach it your taste); the ledger measures every shipped
change against a holdout at +7/+28/+90 days; `learn` and `practices` show what's actually
working. What it looks like two weeks in:

```
| change type | day (+7) | week (+28) | month (+90) | wins |
|-------------|---------:|-----------:|------------:|-----:|
| retitle     | +11 (n2) |   +36 (n2) |          —  | 100% |
| update_meta |  +5 (n1) |   +12 (n1) |          —  | 100% |
| refresh     |  -9 (n1) |   -18 (n1) |          —  |   0% |
▶ Do more of: retitle (+36, this-site) · Rethink: refresh (measurably not working here)
```

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
| **Control & review** | `control` `pr` `cms` `webtask` `autonomy` `review` `approve` `changes` `apply --approved` | Ship fixes via repo PRs / **13 CMS connectors** / headless browser — autonomy-gated, human-approved on CLI/email/Slack/Mattermost/WhatsApp |
| **Measure & deliver** | `ledger` `explain` `anomaly` `report --pdf --email` `run --daily\|--monthly` `email` `deliver` `feedback` | Causal change ledger + holdout attribution · "why did /x drop?" · anomaly alerts · PDF reports · **email/Google-Drive client delivery + the feedback loop** |
| **Learn** | **`learn`** **`brain`** | Impact of every change at day/week/month + cross-site "what works" · self-learning memory: client taste + proven playbooks, injected into every prompt |
| **Autonomy loop** | **`autopilot --daily\|--weekly\|--monthly`** **`serve`** | The 4-agent loop (Audit→Plan→Execute→Report) + the live local dashboard |
| **Scale & packaging** | `projects` `jobs` `edition` `mcp` | Multi-site (agency) portfolio · job queue · edition/entitlements · MCP server |

Full reference: **[docs/Capabilities.md](docs/Capabilities.md)** and **[docs/Commands.md](docs/Commands.md)**.

## The closed loop (why it's different)

Most tools stop at diagnosis. This one runs the whole loop, locally:

```
Diagnose → Decide → Produce → Ship → Deliver → Measure → Learn ↻
 audit      plan      crew     pr/      deliver   ledger     learn + brain
 anomaly    consult   draft    control  (email/   explain    (playbooks, taste,
                               13 CMSs   Drive)   +7/28/90d   cross-site)
```

- **It ships the fix, not a description** — a git PR that edits meta/schema/redirects, a CMS
  update, or a browser action — through a **human review gate** and your chosen **autonomy mode**
  (`manual` / `approve` / `auto`).
- **It proves what worked** — the causal **ledger** logs every change and attributes the outcome
  vs a **holdout of untouched pages**. `explain <url>` answers "why did this move?" with evidence.
- **It learns continuously** (Hermes-style observe→distill→reuse→refine) — measured wins become
  **proven playbooks**, client feedback becomes **taste**, and both are auto-injected into every
  prompt. An **anonymized cross-site store** (only change-type × horizon aggregates, keyed by a
  domain hash) means lesson #1 from site A makes site B better on day one.
- **Expert personas** — outputs are written by deliberately-specified expert prompts (strategist,
  technical SEO, E-E-A-T writer, editor), sharpened further by what the brain has learned about
  your site and your taste.
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
| optional | WordPress · Webflow · Ghost · Shopify · Contentful · Strapi · Sanity · HubSpot · Drupal · Joomla · Wix · Notion · GitHub (`gh`) | publish + update/delete live content / repo PRs (git-PR file is the default; `cms` shows every connector + its env vars) |
| optional | Google Drive (service account or rclone) | drop deliverables straight into the client's folder (`deliver`) |

`integrations` prints a live matrix of what's active/missing and what each unlocks.

## Documentation

- **[Capabilities](docs/Capabilities.md)** — ⭐ the complete step-by-step reference (every command, degradation matrix)
- **[Getting Started](docs/Getting-Started.md)** · **[Command Reference](docs/Commands.md)** · **[Onboarding](ONBOARDING.md)**
- **[Architecture](docs/Architecture.md)** · **[Integrations](docs/Integrations.md)** · **[Site Doctor](docs/Site-Doctor.md)** · **[AI Search](docs/AI-Search.md)**
- **[Agent Loop](docs/AGENT-LOOP-PLAN.md)** · **[Distribution & Runtimes](docs/APP-PLAN.md)** (local-only)
- Commercial: **[Pricing](docs/PRICING.md)** · **[Commercial license](COMMERCIAL.md)** · **[Product strategy](docs/PRODUCT-STRATEGY.md)**
- For the operator: **[Learnings](docs/LEARNINGS.md)** · **[Roadmap](docs/ROADMAP.md)** · **[Playbook](PLAYBOOK.md)** · **[Build loop](BUILDLOOP.md)**

## FAQ — the questions that decide whether you'll trust it

**Where does my data go?** Nowhere. No server, no telemetry, no SaaS — corpus, keys,
history, and the change ledger live in a folder on your machine. Cross-workspace learning
(anonymized change-type stats) is **opt-in** and stays on your disk too.

**Do I need API keys?** No — the audit, GEO score, plan, drafts, and dashboard run with
zero credentials. Keys add depth: GSC (or just a CSV export) for real demand data,
DataForSEO (~sub-cent per call, bring-your-own) for volumes/SERPs.

**Does it publish AI slop?** It can't, by design: a safety gate hard-blocks thin/duplicate/
boilerplate content, every change routes through your **approval queue**, and the ledger
measures each shipped change against a holdout — negative patterns become explicit
"rethink" guidance instead of being repeated.

**Will it work on my JS-heavy site?** The crawler detects client-side rendering and tells
you; enable Playwright rendering (`render.enabled`) for full CSR sites.

**What does it cost to run?** The engine is free. Typical real-world spend is a few
dollars/month of DataForSEO for a small site — you pay them directly.

**Is it production-ready?** Beta — a 3-site pilot is running now and the measured case
study ships with v1. The [launch plan](docs/LAUNCH-PLAN.md) with its gates is public.

## 💰 Pricing — free engine, paid commercial license

The **entire engine is free** (every command, the autopilot, the dashboard). Paid tiers are
**local licenses** for professional use — nothing is ever locked in the core:

| | Open | Pro $149/yr | Agency $599/yr | Enterprise |
|---|---|---|---|---|
| Full engine, autopilot, dashboard, 59 MCP tools | ✅ | ✅ | ✅ | ✅ |
| Sites | 1 (personal) | 10 | unlimited | unlimited |
| White-label reports · commercial/client use | — | ✅ | ✅ | ✅ |
| Reseller rights (deliver under your brand) | — | — | ✅ | ✅ |
| Priority support · custom connectors · done-for-you | — | — | — | ✅ |

Details + how to buy: **[docs/PRICING.md](docs/PRICING.md)** · license terms:
[COMMERCIAL.md](COMMERCIAL.md). Agencies: the demo is the sales pitch — run `demo`, then
imagine the ledger on your client's site.

## ☕ Support this project

This is an independent, open-core project — no VC, no SaaS, everything runs on *your*
machine. If it saved you hours, won you rankings, or replaced a paid tool:

- ⭐ **Star the repo** — it's how other people find it.
- 🗣 **Share it** — a post, a Slack message, a "this exists" to one SEO friend.
- 🐛 **Open an issue / PR** — real-site war stories make the tool sharper (see
  [docs/LEARNINGS.md](docs/LEARNINGS.md)).
- 💸 **Tip / sponsor** — click the **Sponsor** button at the top of the repo (or see
  `.github/FUNDING.yml`). One-off tips and recurring sponsorships both welcome; they fund
  more connectors, deeper AI-search tracking, and support.
- 🏢 **Using it commercially?** The right way to say thanks is a [Pro or Agency
  license](docs/PRICING.md) — white-label reports, multi-site, priority support.

<!-- Once your tip accounts exist, you can also add badges here, e.g.
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-☕-yellow)](https://buymeacoffee.com/yourhandle)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-tip-red)](https://ko-fi.com/yourhandle)
[![Sponsor](https://img.shields.io/badge/GitHub-Sponsor-ea4aaa)](https://github.com/sponsors/umairsandhu)
-->

## License

Open-core — the engine is free and open-source (see `LICENSE`). Commercial editions (Pro /
Agency / Enterprise) are **local licenses** for white-label + multi-site/commercial use +
support; see [COMMERCIAL.md](COMMERCIAL.md). No hosting, ever.
