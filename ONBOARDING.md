# Onboarding — the first-run journey for a new site

Every new site starts here. The rule is **one workspace = one site**, and a site
does not get a baseline until it clears the **readiness gate** (target set, secrets
safe, and the right data accesses wired in — or explicitly waived). This is what
makes the output trustworthy instead of a pile of false positives on a
half-configured crawl.

**You (the agent) are the writer and the decision-maker.** The Python surfaces data
and gates the flow; you make the calls and write the content. Do the stages in
order — **fork-safety and the readiness gate come before any analysis.**

```
init → preflight ─(gate)─→ onboard → BASELINE.md → run (weekly) / run --monthly
        ▲ blocks until the required accesses are wired in
```

---

## Stage 0 · New workspace, new site — `init`
`cd` to an **empty directory** (never the skill's install dir) and run:
```
python -m seo_agent init --site https://the-site.com
```
It scaffolds `config.json` + `.env` + a hardened `.gitignore` and runs fork-safety.
Then ask **one** open question — *"What's the site, and what does the business want
more of?"* — and fill `config.json` from `config.example.json`: `site`, `sitemap`,
`include` (content prefixes), `competitors` (2–3), `dataforseo.location_name/
language_name`, `cms.type`, `brand`. Propose it; don't interrogate.

## Stage 1 · The readiness gate — `preflight` (the journey's spine)
```
python -m seo_agent preflight        # a staged checklist + a 0–100 readiness score
```
It checks, and **blocks the baseline until the required items are green:**

| Stage | Required | Recommended |
|---|---|---|
| **A · Target site** | dedicated workspace · real domain · sitemap resolves | `include` sections · `competitors` |
| **B · Fork-safety** | secrets safe (gitignore + no tracked keys) | — |
| **C · Data & access** | **search performance (GSC or CSV)** · **market data (DataForSEO or alt)** | PageSpeed/CrUX · server logs · JS render |

For every gap it prints **exactly what to set** and **what it unlocks**, so onboarding
a new site is a guided journey, not guesswork. Walk the user through wiring each
required access:

- **Search performance — required.** Either share a **GSC service account**
  (`gsc_property` + `gsc_credentials`, read-only) **or**, if they can't grant API
  access, import an export: `gsc --csv <export.zip | dir | Queries.csv>` (a Google
  Sheet works too — download the workbook). Unlocks striking-distance, low-CTR,
  decay, algo attribution.
- **Market data — required.** `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` in `.env`
  (alts: Semrush / Ahrefs / SerpApi). Unlocks volume, difficulty, SERP/PAA, gaps,
  backlinks, trends. **DataForSEO bills per call** — check the balance and prefer
  bulk endpoints (see `docs/LEARNINGS.md`).
- **Recommended:** `PAGESPEED_API_KEY` (Core Web Vitals field data), `logs.path`
  (crawl budget + AI-crawler coverage), `render.enabled` (audit JS/SPA sites
  accurately — required *if* the site is client-rendered).

Run `integrations` for the full capability matrix. The gate is a floor, not a
ceiling — greener is better, and the recommended items each add a whole capability.

> A site can proceed without a required access via `onboard --degraded`, but say so
> loudly: the analysis will be partial (no striking-distance without search data, no
> difficulty/gaps without market data).

## Stage 2 · Fork-safety FIRST — `safety` (never skip)
Runs inside the gate, but understand it: it writes a committed **`.env.example`**
(placeholders only), hardens `.gitignore` so `config.json` / `.env` / service-account
JSON / `history/` / outputs can never be committed, and **leak-scans the tracked
files AND the working tree**. If **not fork-safe**, stop: `git rm --cached <file>`
for anything tracked, rotate anything that leaked, and offer the pre-commit hook.
This protects the operator's keys in every fork — the whole point of doing it first.

## Stage 3 · Baseline — `onboard`
Once the gate is green:
```
python -m seo_agent onboard          # ingest → audit → speed → gaps → BASELINE.md
```
It refuses to run if required accesses are missing (writes `SETUP.md` with the
remaining journey instead). When it clears, it produces **`BASELINE.md`** — the
snapshot every later run is measured against — plus `audit.md`.

**Detect the platform + render mode first.** Server-rendered/SSG is crawlable; a
heavily client-rendered site (content only in JS) looks empty to the raw crawler —
flag it and enable `render.enabled`. Note the CMS: attribute quirks matter (e.g.
Webflow emits `<meta content=… name=…>`, and dates/authors live in JSON-LD, not OG
meta — the ingester now handles both; see `docs/LEARNINGS.md`).

## Stage 4 · Read the baseline, decide the fix order
Read `audit.md` + `BASELINE.md` and **decide** the sequence: crawl/index → content
→ links. Typical Site Doctor findings: sitemap health (`lastmod`, orphans, noindex/
404 in sitemap), robots/llms.txt, titles/meta (missing/dup/length), H1 uniqueness,
canonical, **cannibalization** clusters, thin content, internal-linking (orphans,
click-depth), structured data, E-E-A-T (author/dates/trust pages), GEO/AEO readiness.
**Validate the headline numbers against live HTML before reporting** — the audit is
a first pass, not gospel (see LEARNINGS #6).

## Stage 5 · Start fixing — propose-only PRs, drip cadence
With repo access and the user's go-ahead, **apply fixes as PRs — never direct
commits** (human merge gate). Good first PRs: add `llms.txt`; fix sitemap `lastmod` /
drop noindex+404 URLs; rewrite weak/duplicate titles + missing metas (you write
them); inject internal links into orphan/under-linked pages; add canonicals;
consolidate cannibalized clusters (301s). **Never mass-publish** — keep a drip
cadence. Content generation is gated behind human review by design.

## Stage 6 · Cadence
Schedule `run` weekly and `run --monthly` monthly (cron or the `/schedule` skill).
Each run diffs against history + the baseline. Monthly: run `radar` and append any
new confirmed Google updates to `seo_agent/algo.py` UPDATES.

---

**The gate is the product.** A new site that hasn't wired in search + market data
isn't ready for analysis — walk the user through Stage 1 until `preflight` is green,
and only then spend time and API budget. See `docs/LEARNINGS.md` for the field notes
that keep each new run sharp, and `docs/ROADMAP.md` for where the tool is headed.
