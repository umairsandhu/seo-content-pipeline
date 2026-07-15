# Site Doctor

`audit` runs the full technical + on-page audit off `corpus.json` plus a live robots/llms/
sitemap fetch, and writes `audit.md` — findings ranked most-severe first, grouped, and ordered
the way to fix them: **crawl/index → content → links**. All deterministic and offline-capable;
speed/DataForSEO layer in when configured. Fixes are **proposed, not applied**.

## What it checks

### Crawl & indexing
- **Sitemap doctor** — ≤50k URLs / ≤50MB per file, sitemap-index use, per-URL status
  (200 vs 404/redirect/noindex), `lastmod` format + freshness (all-same-date ⇒ Google ignores
  it), coverage (orphans vs pages missing from the sitemap), robots.txt reference.
- **robots.txt** — reachable, references a sitemap, not `Disallow: /` under `User-agent: *`
  (group-aware), and — importantly — flags when it **blocks AI crawlers** (GPTBot/ClaudeBot/
  PerplexityBot/…), which removes you from AI answers.
- **llms.txt** — present? (offer to generate). Not a Google ranking factor, but AI assistants
  use it — see [AI-Search.md](AI-Search.md).
- **JavaScript rendering / CSR** — flags pages whose raw HTML is near-empty with a SPA mount
  marker (likely client-rendered → invisible to non-rendering crawlers, incl. AI bots). Enable
  `render.enabled` for an accurate audit of such sites.
- **Redirects** — sitemap/crawled URLs that redirect (point links + sitemap at the final URL).

### On-page / content
- **Metadata** — title/meta presence, length (title >60, meta >160), and **duplicates**.
- **H1** — presence, uniqueness, one-per-page; duplicate H1 across pages.
- **Canonical** — present, self vs cross (cross-canonical may de-index the page).
- **Content depth** — thin pages (< configurable word thresholds).
- **Cannibalization** — title-space TF-IDF clusters (also see `consolidate` for keep/redirect).
- **Structured data** — JSON-LD coverage across indexable pages (generate with `schema`).

### Links
- **Orphans** — indexable pages with no internal links pointing to them (aggregated).
- **Under-linked** — pages with < N inbound internal links.
- **Click depth** — pages > N clicks from the root; unreachable pages.
- **Broken internal links** — links to 4xx/5xx pages.

### Internationalization
- **hreflang** — pages that set hreflang without an `x-default`.

### E-E-A-T-adjacent & accessibility
- **E-E-A-T** (`eeat`) — named author, publish/updated dates, ≥2 outbound citations, sitewide
  trust pages (about/contact/editorial/privacy), HTTPS. *Measurable signals, not a score.*
- **Topical authority** (`authority`) — topic clusters + pillar presence + internal-link
  density (authority accrues at the cluster level).
- **Accessibility** — alt-text coverage, `<html lang>`, heading-order skips (not a direct
  ranking factor, but the structure Google rewards + image SEO). PageSpeed adds an a11y score.

## Reading the report
- **Fix HIGH first** (broken links, orphans, whole-site crawl blocks), then content, then
  linking. `plan` turns the findings into a prioritized action list with the command to run.
- On a **partial crawl** (small `max_pages`), orphan/click-depth findings are less reliable —
  the internal-link graph is incomplete. Raise `max_pages` for trustworthy link analysis.
- The audit **auto-discovers the sitemap** from robots.txt if the configured one 404s.

## Speed (`speed`)
PageSpeed Insights (Lighthouse **lab** LCP/CLS/TBT + performance & accessibility scores) plus
the CrUX API (real-user **field** p75 for LCP / INP / CLS). 2026 thresholds (p75): **LCP
< 2.5 s · INP < 200 ms · CLS < 0.1**. Field data needs `PAGESPEED_API_KEY`; without it you get
lab data only. INP is the most-failed vital — check it first.

## Log-file analysis (`logs`)
The only unsampled record of real crawler behavior, and the **only way to see AI crawlers**.
Parses Common/Combined logs (+ `.gz`), classifies Google + AI bots, and reports crawl waste,
crawl distribution, and — the killer signal — **which of your indexable pages no AI crawler
has fetched**. `--verify` reverse-DNS-checks Googlebot for spoofing.
