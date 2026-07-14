---
name: seo-content-pipeline
description: >-
  Turn any website into a prioritized SEO content plan. Ingests the site's own
  pages (via sitemap), finds internal cannibalization + linking opportunities,
  pulls Google Search Console performance (striking-distance queries, low-CTR
  pages) and DataForSEO keyword volume/SERP/suggestions, and outputs content
  recommendations + a deduped queue. Use when the user asks to audit a site's
  SEO, find content gaps, plan/prioritize blog content, spot cannibalization,
  or set up an automated content pipeline for a domain.
---

# SEO content pipeline

A site-agnostic engine. Point it at a domain; it never assumes a particular CMS.
Everything is file-based and lightweight (numpy + scikit-learn core; Google libs
only for the optional GSC step).

## Setup (once per site)
1. Copy `config.example.json` → `config.json` in the working dir and fill in
   `site`, `sitemap`, `include` (path prefixes to ingest, e.g. `["/blog/"]`),
   and optionally `pillars`, `gsc_property`, `gsc_credentials`, `dataforseo`.
2. Secrets via env, never in config:
   - DataForSEO: `export DATAFORSEO_LOGIN=… DATAFORSEO_PASSWORD=…`
   - GSC: a service-account JSON at `gsc_credentials`, with the property shared
     to that service account (read-only).
3. `pip install numpy scikit-learn` (+ `google-api-python-client google-auth` for GSC).

## Run
```bash
python -m seo_agent ingest                 # crawl sitemap → corpus.json
python -m seo_agent analyze \              # the main output → recommendations.md
        --keywords-file seeds.txt
python -m seo_agent discover "your seed"   # DataForSEO keyword ideas (trend/gap pull)
python -m seo_agent research kw1 kw2 …      # dedup gate + link targets per keyword
python -m seo_agent gsc                     # striking-distance + low-CTR (needs GSC)
python -m seo_agent brief "a keyword"       # live SERP → outline input
```

## What `analyze` returns (recommendations.md)
1. **Consolidate** — query-cannibalization clusters in the site's own content.
2. **Content gaps** — keywords with demand the site doesn't cover (the dedup gate
   drops anything already covered; ranks by volume + NOVEL/RELATED).
3. **Striking distance** — GSC queries at position 5–15 (one push from page 1).
4. **Low-CTR pages** — GSC pages with impressions but weak CTR (retitle targets).

Steps 3–4 appear only when GSC is configured; the rest work with just an ingest.

## How to drive it (agent)
- Confirm the target domain + which sections to ingest (the `include` prefixes).
- Run `ingest`, then `analyze` with a seed keyword list (or `discover` to build
  one from DataForSEO).
- Read `recommendations.md` and turn the top gaps into briefs (`brief <kw>`),
  then draft the posts. Keep to a drip cadence; never mass-publish.
- Degrade gracefully: no GSC → skip 3&4; no DataForSEO → gaps still rank by
  intent + the dedup verdict.

Notes: ingest is ~1s/page (network-bound); cap with `max_pages`. The similarity
backend is TF-IDF (strong on lexical cannibalization) — `index.build_vectorizer`
is the single swap-point for semantic embeddings.
