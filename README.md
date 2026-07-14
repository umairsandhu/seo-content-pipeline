# seo-content-pipeline

A **site-agnostic**, lightweight SEO content engine. Point it at any domain and it
produces a prioritized content plan — no CMS coupling, no database, no server.

It ingests the site's own pages (via sitemap), then fuses four signals:

1. **Cannibalization** — query-clusters in the site's own corpus to consolidate.
2. **Content gaps** — keywords with demand the site doesn't already cover (a dedup
   gate drops anything already ranked/written).
3. **Striking distance** — GSC queries at position 5–15 (one nudge from page 1).
4. **Low-CTR pages** — GSC pages with impressions but weak clickthrough (retitle).

Output: `recommendations.md` + a deduped, ranked queue.

## Quick start
```bash
cp config.example.json config.json     # edit: site, sitemap, include prefixes
export DATAFORSEO_LOGIN=…  DATAFORSEO_PASSWORD=…      # optional (volumes/SERP)
pip install numpy scikit-learn                       # + google libs for GSC

python -m seo_agent ingest                           # sitemap → corpus.json
python -m seo_agent analyze --keywords-file seeds.txt   # → recommendations.md
```

## Config (`config.json`)
| key | meaning |
|---|---|
| `site` / `sitemap` | domain + sitemap URL (sitemap defaults to `<site>/sitemap.xml`) |
| `include` / `exclude` | path prefixes to ingest / substrings to skip |
| `max_pages` | ingest cap (ingest is ~1s/page) |
| `pillars` | hub URLs to prefer as internal-link targets |
| `gsc_property` | `sc-domain:example.com` or the URL-prefix property |
| `gsc_credentials` | path to a Google service-account JSON (property shared to it, read-only) |
| `dataforseo` | `{location_name, language_name}` for volume/SERP |

Secrets never go in the config — DataForSEO via env, GSC via the service-account file.

## Commands
`ingest` · `analyze` · `discover <seed>` · `research <kw…>` · `gsc` · `brief <kw>`
(see `SKILL.md` for details).

## Design
File-based; TF-IDF cosine for similarity (`index.build_vectorizer` is the swap-point
for semantic embeddings). Providers degrade gracefully — the core (ingest + dedup +
gaps) runs with zero credentials; GSC and volume data layer in when configured.
