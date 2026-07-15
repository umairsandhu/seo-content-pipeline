# Playbook — 0 to 100 for any site

The end-to-end operating manual. `ONBOARDING.md` is Day 1; `BUILDLOOP.md` is how the
*tool* stays current; this is how you take a *site* from cold to compounding. At any
point, **`python -m seo_agent plan`** fuses every signal into the ranked next actions —
it's the co-pilot for every phase below. Apply changes as PRs (human merge gate).

---

## Phase 0 · Setup & fork-safety — *Day 1, ~15 min*
**Goal:** operational + safe.
- `safety` → writes `.env.example`, hardens `.gitignore`, leak-scans. **Must be fork-safe.**
- `cp config.example.json config.json`; set `site`, `competitors`, `brand`. `cp .env.example .env`.
- `integrations` → see which APIs are wired and what each unlocks. Wire the two must-haves:
  **GSC** (`gsc_credentials` + `gsc_property`) and **DataForSEO** (`.env`).
- **Done when:** `integrations` shows GSC + DataForSEO active and `safety` is green.

## Phase 1 · Technical foundation — *Week 1*
**Goal:** crawlable, indexable, correctly structured. Fix the plumbing before pouring content.
- `ingest` (auto-discovers the sitemap from robots.txt if needed).
- `audit` → Site Doctor. Fix in order: **crawl/index → content → links.**
  - crawl: robots.txt (incl. AI-crawler policy), sitemap health, JS-rendering/CSR, redirects.
  - index: canonical, noindex-in-sitemap, hreflang.
  - content: titles/meta length + duplicates, H1, thin pages.
  - links: broken internal links; (orphans/click-depth need a **full crawl** — raise `max_pages`).
- `schema <url>` → generate missing JSON-LD. `sitemap` → fix lastmod/coverage.
- **Done when:** no HIGH audit findings; sitemap clean; key templates render for crawlers.

## Phase 2 · Baseline & measurement — *Week 1–2*
**Goal:** know where you stand so you can prove movement.
- `onboard` → `BASELINE.md` (the snapshot everything is measured against).
- `gsc` (run a few times to build history) · `rank` (track positions + SERP features).
- `logs <access.log>` → is Googlebot crawling the right pages? Are **AI crawlers** seeing you?
- **Done when:** `BASELINE.md` exists and history has ≥2 GSC + rank snapshots.

## Phase 3 · Content engine — *Weeks 2–8*
**Goal:** win the queries you should own.
- Find: `discover <seed>` · `gap` (competitor gap) · `trends <seed>` (emerging) · `research <kw>`.
- Decide: **you** pick targets (commercial/local before informational; skip EXTEND — already covered).
- Write: `brief <kw>` → **you draft it** (`draft <kw>` gives the writing packet) → `score <kw> <url>`
  to check comprehensiveness vs the SERP → revise → `publish`.
- Link every new post to a pillar and 2–3 siblings (`research` gives link targets).
- **Done when:** a steady drip of published, deduped, internally-linked posts (never mass-publish).

## Phase 4 · Optimize & compound — *ongoing, weekly*
**Goal:** defend and grow what you have — usually higher ROI than net-new.
- `run` (weekly digest) → then `plan` for the ranked actions.
- `decay` → refresh slipping posts · `aio` → push AIO-adjusted striking-distance (don't chase
  queries an AI Overview caps) · `retitle` low-CTR pages · fix new orphans/thin pages.
- **Done when:** decaying pages are refreshed within a week; striking-distance queries trend up.

## Phase 5 · AI-search & scale — *ongoing, monthly*
**Goal:** stay visible as search shifts to AI answers, and widen coverage.
- `logs` AI-crawler coverage → are GPTBot/ClaudeBot/PerplexityBot fetching your best pages?
  If robots.txt blocks them, **decide deliberately** (it removes you from those AI answers).
- `llmstxt` → generate/refresh. Structured data + comprehensiveness = the AEO levers (Google:
  AI features ride the same core ranking signals — no separate track).
- `run --monthly` → trends, backlink gap, algo attribution. `radar` → append new Google updates
  to `algo.py`. Raise `max_pages` for full-site internal-linking analysis.
- **Done when:** monthly digest is clean, AI crawlers cover your priority pages, and the loop runs
  on a schedule (cron / `/schedule`).

---

### The daily/weekly/monthly rhythm
- **Weekly:** `run` → `plan` → ship the top 5 actions as PRs.
- **Monthly:** `run --monthly` → `radar` → re-`audit` → refresh `BASELINE` comparison.
- **Quarterly:** re-pull AI-search stats, benchmark vs a best-in-class tool, build the next
  roadmap capability (see `BUILDLOOP.md`).

**One rule above all:** let the data pick the *what*, let judgment pick the *whether*, ship
small and often, and measure against `BASELINE.md`.
