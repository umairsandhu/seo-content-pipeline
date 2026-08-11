---
name: seo-content-pipeline
description: >-
  End-to-end SEO automation for any website. Ingests the site (sitemap), tracks
  rank/CTR/backlinks/trends over time, finds cannibalization + linking + content
  gaps, detects decaying content, attributes traffic shifts to Google algorithm
  updates, drafts SERP-grounded articles and rewrites titles/metas, publishes to
  WordPress/Webflow/Ghost/git-PR, exposes everything over MCP, and runs scheduled
  weekly/monthly digests. Includes a guided first-run onboarding with fork-safe secret
  setup (.env.example + .gitignore + leak-scan so keys never leak) and a technical Site
  Doctor (sitemap health, robots.txt, llms.txt, metadata/titles, H1, canonical, dedup,
  content depth, internal-linking/orphans/click-depth, Core Web Vitals, structured data).
  Use to onboard a site, audit SEO, plan/write/refresh blog content, spot cannibalization,
  build backlinks, track SERPs, or stand up an automated pipeline.
---

# SEO content pipeline

A site-agnostic SEO engine across five layers. Point it at a domain; it never
assumes a CMS. File-based and lightweight (numpy + scikit-learn core; Google libs
only for GSC; everything else is stdlib/urllib). Everything **degrades
gracefully** — the core runs with zero credentials, and each capability layers in
as you add creds.

**First run on a new site → follow `ONBOARDING.md`** (or `python -m seo_agent onboard`).
It runs **fork-safety first** (so the operator's keys can never leak from a fork),
then the Site Doctor, speed, and gap analysis into `BASELINE.md`.

**The 0→100 path is `PLAYBOOK.md`** (setup → technical → baseline → content → optimize →
AI-search). At any point, **`python -m seo_agent plan`** fuses every signal into the ranked
"what to do next" — the co-pilot for the whole journey.

| Layer | What it does | Commands |
|---|---|---|
| 0 · Onboard | fork-safety + **gated readiness journey** (blocks until the right accesses are wired in) → first-run baseline | `safety` `preflight` `onboard` |
| 0 · Doctor | technical/on-page audit: sitemap·robots·llms.txt·meta·H1·canonical·dedup·links·speed | `audit` `sitemap` `speed` `llmstxt` |
| 1 · Observe | ingest site; track GSC/backlinks/trends over time (`history/`) | `ingest` `gsc` `backlinks` `trends` |
| 2 · Decide | cannibalization, gaps, striking-distance, decay, algo attribution | `research` `discover` `decay` `algo` |
| 3 · Produce | SERP-grounded briefs, full drafts, title/meta rewrites | `analyze` `brief` `draft` `retitle` |
| 4 · Publish | one interface → WordPress / Webflow / Ghost / git-PR; MCP server | `publish` `mcp` |
| 5 · Orchestrate | weekly/monthly run → `digest.md` (what changed, what to do) | `run [--monthly]` |

Full docs/wiki: `README.md` + `docs/` (Getting-Started, Commands, Architecture,
Integrations, Site-Doctor, AI-Search, SEO-Knowledge-Base, FAQ, Contributing).

## Setup (once per site)
0. **`python -m seo_agent init --site https://…`** — bootstrap a site-agnostic
   workspace: scaffolds `config.json` + `.env` + a hardened `.gitignore` and runs
   fork-safety. One directory = one site; it refuses to run in the install dir.
1. Edit `config.json` (`site`, `include`, `competitors`, `gsc_property`,
   `gsc_credentials`, `dataforseo`, `cms`) and add any creds to `.env` (auto-loaded;
   no key needed for content — the agent writes it). `integrations` shows what's missing.
2. Secrets via env, never in config:
   - DataForSEO (volumes/SERP/backlinks/trends): `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`
   - GSC: a service-account JSON at `gsc_credentials`, property shared read-only
   - Publishing: `WP_USER`+`WP_APP_PASSWORD` / `WEBFLOW_TOKEN` / `GHOST_ADMIN_KEY`
   - Content drafting needs **no key when run inside Claude/an agent** — you write it
     (see below). A key (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, with `llm.provider`)
     is only for headless/cron runs with no agent in the loop.
3. `pip install numpy scikit-learn` (+ `google-api-python-client google-auth` for GSC).

## Run
```bash
# Onboarding / Site Doctor (first run)
python -m seo_agent safety                  # fork-safety: .env.example, .gitignore, leak-scan
python -m seo_agent integrations            # API capability matrix (what's active/missing/unlocked)
python -m seo_agent preflight               # onboarding readiness gate: staged checklist + 0–100 score
python -m seo_agent onboard                 # gated first-run baseline → BASELINE.md (--degraded to skip the gate)
python -m seo_agent audit                   # Site Doctor → audit.md
python -m seo_agent sitemap                 # sitemap doctor only
python -m seo_agent sitediff                # what changed on YOUR site between crawls (noindex regressions, meta/schema drift) — cron = 24/7 monitoring
python -m seo_agent zeroclick               # zero-click KPIs: impressions-vs-clicks alligator, branded-demand trend, shipped-vs-moved correlation
python -m seo_agent repurpose <url>         # one article → no-link LinkedIn post + X thread + newsletter section + quotable stat (voice-aware)
python -m seo_agent tip                     # today's sourced SEO tidbit (auto-appears once/day after commands + on the dashboard; "tips": false to disable)
python -m seo_agent diagnose                # "why is traffic down?" — ranked differential: self-inflicted / Google update / zero-click erosion / decay / anomalies
python -m seo_agent agent [--background|--install|--status|--stop]  # ALWAYS-ON mode: heartbeat + instant alerts + daily cycle + weekly report (+ weekly SF pull if agent.sf_crawl). --background detaches; --install = launchd, survives reboots
python -m seo_agent profile [--apply]       # auto-understand the site: platform fingerprint, CSR detection (auto-enables JS rendering), scale, robots — fixes the crawler's capabilities
python -m seo_agent interview               # 6-question business interview → CLIENT.md + brain seeds (strategist/writer know the business day one)
# Identity files (OpenClaw pattern — read every session, operator-editable): SOUL.md (persona) ·
# AGENTS.md (operating instructions) · CLIENT.md (business model) · MEMORY.md (auto-curated) · memory/ (daily journal)
python -m seo_agent sf [--csv <export>] [--crawl]  # OPTIONAL Screaming Frog bridge (import/cross-check) — the native crawler needs nothing: sitemap or spider mode, own crawl_depth + inlinks
python -m seo_agent speed                   # Core Web Vitals (PageSpeed lab + CrUX field)
python -m seo_agent logs access.log[.gz]    # log-file analysis: crawl waste + AI-crawler coverage
python -m seo_agent aio                      # re-rank striking-distance by AI-Overview-adjusted CTR
python -m seo_agent llmstxt                  # generate an llms.txt from the corpus
python -m seo_agent gap                      # competitor content gap

# Plan (the co-pilot — run any time)
python -m seo_agent plan                     # ranked "what to do next" → plan.md

# Observe / Decide
python -m seo_agent ingest                 # sitemap → corpus.json
python -m seo_agent rank                     # track positions + SERP features over time
python -m seo_agent schema <url>             # generate JSON-LD structured data
python -m seo_agent score "<kw>" <url>       # content comprehensiveness vs SERP competitors
python -m seo_agent geo                      # GEO/AEO readiness — how citable by AI answer engines
python -m seo_agent report [--pdf]           # shareable self-contained HTML dashboard → report.html (+ report.pdf via headless browser)
python -m seo_agent autolink                 # batch internal-link plan for under-linked pages
python -m seo_agent eeat                     # E-E-A-T signals (author/dates/citations/trust pages)
python -m seo_agent authority                # topical-authority clusters (pillar + link density)
python -m seo_agent consolidate              # cannibalization → keep-one / 301-redirect plan
python -m seo_agent inlinks <url>            # existing pages that should link to a target
python -m seo_agent toxicity                 # backlink toxicity review (conservative — see note)
python -m seo_agent gsc                     # striking-distance + low-CTR; snapshots history
python -m seo_agent gsc --csv <path|dir|zip> # import a GSC CSV / Sheet export when API access isn't possible
python -m seo_agent decay                   # queries losing rank + pages losing clicks (needs ≥2 gsc runs)
python -m seo_agent trends "your seed"      # emerging / rising keywords
python -m seo_agent backlinks               # backlink profile / competitor link-gap
python -m seo_agent algo                    # attribute traffic shifts to Google updates
python -m seo_agent radar                    # watch Google Search Status; flag stale update knowledge

# AI search / GEO (2026) & advanced
python -m seo_agent aivis                     # AI-visibility: mentions + citations across ChatGPT/Perplexity/Gemini/AIO (agent-mode w/o keys)
python -m seo_agent entity                    # entity graph: Wikidata QID + sameAs + Organization JSON-LD + brand salience
python -m seo_agent citability                # passage-citability: how extractable each page is for AI answers
python -m seo_agent ctr                       # first-party position→CTR curve from your own GSC
python -m seo_agent pagerank                  # internal PageRank / authority-flow — starved pillars + hoarders
python -m seo_agent intl                      # hreflang / international validation
python -m seo_agent local                     # local SEO — NAP consistency + LocalBusiness schema
python -m seo_agent refresh <url>             # content-refresh packet (diagnose staleness → rewrite → verify)
python -m seo_agent prospect                  # link-acquisition prospects from the competitor backlink gap
python -m seo_agent renderdiff <url>          # rendered-vs-raw DOM diff (what a raw crawl misses on JS sites)
python -m seo_agent remediate                 # ordered, human-gated remediation plan from the audit
python -m seo_agent gate <post.json>          # programmatic safety gate (thin/near-dup/boilerplate/schema) — also enforced on publish
python -m seo_agent jobs                       # durable job queue (SQLite)
python -m seo_agent projects [add <name> <dir>] # multi-site portfolio + readiness roll-up (agency)

# Expert brain, full control & delivery
python -m seo_agent consult                    # McKinsey/Google-level growth strategy from every signal
python -m seo_agent crew article "<kw>"        # multi-agent: research→strategy→write→edit→tech-SEO→publish (gated)
python -m seo_agent crew change "<goal>"       # multi-agent: diagnose→plan→apply a site change (gated)
python -m seo_agent wizard [--interactive]     # guided, hand-holding onboarding (next best step)
python -m seo_agent autonomy                    # show mode (manual/approve/auto) + pending approvals
python -m seo_agent control <change.json>      # full site control: create/update/delete/redirect (autonomy-gated)
python -m seo_agent apply --approved           # execute the approval queue
python -m seo_agent webtask <task.json>        # physical web control via Playwright / computer-use MCP
python -m seo_agent email [--pdf <path>]       # email the PDF report to report.email_to
python -m seo_agent run --daily|--monthly [--email]  # scheduled digest at 3 cadences; --email auto-sends the PDF

# Autonomous loop + local dashboard
python -m seo_agent demo                       # 5-min zero-key demo: full synthetic workspace (corpus + history + measured changes)
python -m seo_agent config [--fix]             # every setting slot + hint, ✅/⬜ filled status; --fix adds missing slots (values kept)
python -m seo_agent start                      # THE hand-held entry: status + guided web dashboard (auto-opens the browser)
python -m seo_agent autopilot --daily          # 4-agent cycle: Audit→Plan(dated)→Execute(gated)→Report → state/
python -m seo_agent serve [--port 8787] [--no-open]  # dashboard: getting-started guide, situation/plan/execution, best practices (learned+applied here), documents to review, inline approvals
python -m seo_agent practices                  # best practices learned & applied on this site — found → fixed → measured
python -m seo_agent ledger                      # every change → holdout-adjusted attribution
python -m seo_agent rollback [<change_id>]      # list measured-loser rollback proposals, or revert one to its captured before-state (auto-proposed each cycle)
python -m seo_agent learn [--notify]           # what worked best by day/week/month + cross-site knowledge (auto-runs each cycle)
python -m seo_agent brain [--add "…" --kind fact|lesson|preference|playbook]  # self-learning memory: client taste + proven playbooks (auto-injected into every persona)
python -m seo_agent voice                      # measure the site's existing brand voice → every future draft matches it from day one
python -m seo_agent explain <url>              # why did this page's traffic change?

# Client delivery + the feedback (taste) loop
python -m seo_agent cms [--verify]             # every CMS connector + required env vars; --verify live round-trips (create→update→delete a throwaway draft) the configured CMS
python -m seo_agent deliver report.pdf [--note "…"]   # email + Google Drive delivery to the client (logged)
python -m seo_agent feedback "their reply" [--about "…"]  # client reaction → learned as taste → future output matches them

# Decide / Produce
python -m seo_agent analyze --keywords-file seeds.txt   # → recommendations.md
python -m seo_agent research kw1 kw2 …      # dedup verdict + internal-link targets
python -m seo_agent brief  "a keyword"      # live SERP + PAA outline
python -m seo_agent draft  "a keyword"      # writing packet → the agent writes the article
python -m seo_agent retitle https://…/page --keyword "…"   # task → the agent writes 3 titles + meta

# Publish / Orchestrate
python -m seo_agent publish post.json       # publish via the configured CMS connector
python -m seo_agent run --monthly           # full run → digest.md
python -m seo_agent mcp                      # start the MCP server (stdio)
```

## What each output is
- **recommendations.md** (`analyze`): consolidate (cannibalization) · content gaps ·
  striking-distance · low-CTR pages.
- **digest.md** (`run`): decaying queries/pages · striking-distance · low-CTR ·
  cannibalization · (monthly) rising keywords · content gaps · backlink gap · algo impact.
- **history/** — dated JSON snapshots (`gsc_queries`, `gsc_pages`, `trends`). This is
  what makes decay/algo/emerging work; run `gsc` (and `trends`) on a cadence to build it.

## How to drive it (agent)
**You (the agent running this skill) are the writer and the decision-maker.** The Python
surfaces data and does the deterministic work; you write the prose and make the editorial
and strategic calls. `draft`/`retitle` return a writing packet (`mode: "agent"`) — author
the article/titles directly in your output, don't shell out to an API.
1. Confirm the domain + `include` prefixes; run `ingest`, then `gsc` (start building history).
2. For content: `discover`/`trends` → **you decide** which gap to pursue → `brief`/`draft`
   for the packet → **you write it** → `publish` (default `file` connector writes a Markdown
   file for a git PR — "auto-publish = an automated PR"; never mass-publish, keep a drip cadence).
3. For maintenance: `decay` to find posts slipping → `retitle` low-CTR pages (you write the
   options) → add internal links from `research` link-targets.
4. Monthly: `run --monthly` for the digest; then **update `seo_agent/algo.py` UPDATES**
   with any new confirmed Google updates (that IS the monthly algo-tracking task).
5. Degrade gracefully: no DataForSEO → gaps rank by intent + verdict; no GSC → skip
   decay/striking/low-CTR. Content generation never needs a key when an agent drives the
   skill; set `llm.provider` to `anthropic`/`openai` only for unattended cron runs.

## Integrations (self-configuring)
`seo_agent/integrations.py` is the registry of every API the skill can use — GSC and
DataForSEO (must-have), PageSpeed/CrUX and server logs (recommended), Anthropic/OpenAI and
the CMS connectors (optional), each with its tier, env/config, what it unlocks, and
**alternative providers** (Semrush/Ahrefs/SerpApi for DataForSEO, etc.). `.env.example`,
onboarding, and the `integrations` capability matrix are all generated from it — so
**adding any new API is one entry here** plus a small provider fn using
`providers.http_json`. Run `integrations` to see what's active, what's missing, and what
each gap costs you.

## Staying #1 (the build loop)
`BUILDLOOP.md` defines how the tool keeps up with Google + AI search: canonical sources to
monitor, a weekly/monthly/quarterly cadence, and a prioritized capability roadmap. The
sensor is `radar` (watches Google's Search Status Dashboard, flags when `algo.py` UPDATES
is stale). Monthly: run `radar`, append confirmed updates to `algo.py`, re-run `audit`.

## Scheduling (Layer 5)
`run` is one invocation; schedule it with cron or the `/schedule` skill — weekly
(`run`) for decay + linking + striking-distance, monthly (`run --monthly`) for
trends + backlinks + algo + gaps. Persisted history makes each run a diff vs the last.

## MCP (Layer 4, goal: use any CMS / any client)
`python -m seo_agent mcp` is a stdio MCP server exposing `ingest, analyze, discover,
research, brief, draft, gsc, decay, trends, backlinks, run, publish` as tools. Register
it in any MCP client as command `python -m seo_agent mcp` (config via `SEO_CONFIG`).

## Notes
- Ingest is ~1s/page (network-bound); cap with `max_pages`.
- Similarity backend is TF-IDF (strong on lexical cannibalization). Set `SEO_EMBEDDINGS=1`
  + `pip install fastembed` to swap the body-space to semantic embeddings
  (`index.build_vectorizer` / `index._embed_backend` are the swap points).
- Providers are real but were smoke-tested offline — the DataForSEO field-parsing and
  GSC service-account path may need a small tweak on first live run.
