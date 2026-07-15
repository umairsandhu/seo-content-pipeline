# Onboarding — first run on a new site

The agent (you) runs this once when someone pulls the skill off the shelf, then
the recurring `run` loop takes over. Propose defaults, don't interrogate. **You
are the writer and the decision-maker** — the Python surfaces data and does the
deterministic work; you make the calls and write the content. Do the stages in
order — **fork-safety gates everything** — and land the result in `BASELINE.md`.

Quick path: `python -m seo_agent onboard` runs stages 1–5 deterministically and
writes `BASELINE.md`. Use the stages below to interpret and act on it.

---

## Stage 0 · Kickoff (one open prompt, then propose a config)
Ask one thing: *"What's the site, and what does the business want more of?"* Then
draft `config.json` from `config.example.json` and present it — don't quiz. Fill:
`site`, `sitemap`, `include` (blog/content prefixes), `competitors` (2–3), geo via
`dataforseo.location_name/language_name`, `cms.type`, `brand`. Confirm which creds
exist (GSC service-account, DataForSEO, a Google Cloud key for speed) — each is
optional and the pipeline degrades without it.

## Stage 1 · Fork-safety FIRST — `safety` (never skip)
`python -m seo_agent safety` (or it runs first inside `onboard`). It:
- writes a committed **`.env.example`** (placeholders only) and hardens `.gitignore`
  so `config.json`, `.env`, service-account JSON, `history/`, and outputs can never
  be committed;
- **leak-scans tracked files AND the working tree** (`.gitignore` only protects
  untracked files) and checks nothing secret is already git-tracked.

If the verdict is **not fork-safe**, stop and fix before any commit:
`git rm --cached <file>` for tracked secrets/config, rotate anything that leaked.
Offer to install the pre-commit hook (`safety.precommit_hook`) so it can't recur.
This protects the operator's keys in every fork — it is the whole point of doing
it first.

## Stage 2 · Repo / site analysis
If you have the repo: identify the CMS/framework, where content lives, and the
**render mode** — server-rendered/SSG is crawlable; heavy client-side rendering
(content only in JS) is a crawl risk, flag it. Note how publishing works (this is
how "auto-publish = a PR" maps). Website-only: `ingest` builds `corpus.json` from
the sitemap.

## Stage 3 · Site Doctor — `audit` (technical/on-page)
`python -m seo_agent audit` → `audit.md`. Reads the corpus + live sitemap/robots/
llms and reports, ordered the way to fix them:
- **Sitemap doctor** — 50k/50MB limits, sitemap-index use, per-URL 200/noindex,
  `lastmod` format + freshness (all-same-date ⇒ Google ignores it), coverage
  (orphans / pages missing from the sitemap), robots.txt reference.
- **robots.txt** reachable, references a sitemap, not `Disallow: /`.
- **llms.txt** — present? Not a Google ranking factor, but AI assistants
  (Perplexity/Claude/ChatGPT) use it. Offer `llmstxt` to generate one.
- **Metadata** — title/meta presence, length, **duplicates**; noindex-in-sitemap.
- **H1** presence/uniqueness · **canonical** present/self vs cross.
- **Dedup / cannibalization** (title-space TF-IDF clusters).
- **Content length & depth** (thin-page thresholds).
- **Internal linking** — orphans, under-linked pages, **click-depth from root**,
  unreachable pages, pillar reciprocity.
- **Structured data** (JSON-LD) coverage.

Read `audit.md` and **decide** the fix order: crawl/index → content → links.

## Stage 4 · Speed / Core Web Vitals — `speed`
`python -m seo_agent speed` on key templates. Field p75 targets (2026): **LCP <2.5s,
INP <200ms, CLS <0.1**. Field data needs `PAGESPEED_API_KEY` (one Google Cloud key,
free); without it you still get Lighthouse lab data. INP is the most-failed vital —
check it first.

## Stage 5 · Content & gap — `gsc` · `analyze` · `gap`
GSC striking-distance/low-CTR/decay + DataForSEO gaps + **competitor gap** (`gap`:
keywords 2–3 competitors rank for that you don't). **You decide** which to pursue.

## Stage 6 · Baseline, roadmap, and start fixing (propose-only PRs)
`onboard` writes `BASELINE.md` — the snapshot everything is measured against.
Then, with repo access and the user's go-ahead, **apply fixes as PRs — never
direct commits** (human merge gate). Good first PRs:
- add `llms.txt` (from `llmstxt`);
- fix sitemap `lastmod` / drop noindex+404 URLs from the sitemap;
- rewrite weak/duplicate titles + missing metas (you write them);
- inject internal links into orphan/under-linked pages (targets from `research`);
- add missing canonicals.
Keep a **drip cadence**; never mass-publish.

## Stage 7 · Cadence
Schedule `run` weekly and `run --monthly` monthly (cron or the `/schedule` skill).
Each run diffs against history + this baseline. Monthly: also update
`seo_agent/algo.py` UPDATES with new confirmed Google updates.
