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
| 0 · Onboard | fork-safety (secrets never leak) + first-run baseline | `safety` `onboard` |
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
python -m seo_agent onboard                 # full first-run baseline → BASELINE.md
python -m seo_agent audit                   # Site Doctor → audit.md
python -m seo_agent sitemap                 # sitemap doctor only
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
python -m seo_agent report                   # shareable self-contained HTML dashboard → report.html
python -m seo_agent autolink                 # batch internal-link plan for under-linked pages
python -m seo_agent eeat                     # E-E-A-T signals (author/dates/citations/trust pages)
python -m seo_agent authority                # topical-authority clusters (pillar + link density)
python -m seo_agent consolidate              # cannibalization → keep-one / 301-redirect plan
python -m seo_agent inlinks <url>            # existing pages that should link to a target
python -m seo_agent toxicity                 # backlink toxicity review (conservative — see note)
python -m seo_agent gsc                     # striking-distance + low-CTR; snapshots history
python -m seo_agent decay                   # queries losing rank + pages losing clicks (needs ≥2 gsc runs)
python -m seo_agent trends "your seed"      # emerging / rising keywords
python -m seo_agent backlinks               # backlink profile / competitor link-gap
python -m seo_agent algo                    # attribute traffic shifts to Google updates
python -m seo_agent radar                    # watch Google Search Status; flag stale update knowledge

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
