# SEO Knowledge Base

The concepts and 2026 best-practice map behind the tool's decisions. Every claim here is
grounded in the research passes that shaped the codebase (sources at the bottom).

## The 2026 best-practice map
Best-in-class SEO is three things at once:
1. **Technical hygiene** — crawlable, indexable, correctly rendered and structured.
2. **Content that earns + defends** — comprehensive, authoritative, well-interlinked.
3. **AI-search visibility** — cited in AI answers, which now intercept a large share of clicks.

Google's stance ties them together: AI features ride the **same core ranking + quality
systems**, so there's no separate "AI SEO" track — just SEO done well, plus extractability.

## Glossary (the levers the tool acts on)

**Crawl budget** — how many URLs a search engine fetches from your site in a period. Waste it
on 404s/params/low-value URLs and important pages get crawled less. *Signal:* server logs
(`logs`). Matters below 1M pages too (the "only huge sites" claim is a myth).

**Index budget** — the pages Google deems worth *keeping* in the index. In 2026, managing what
gets retained is as important as what gets crawled. *Signal:* GSC coverage; thin/duplicate
pruning (`audit` content + `consolidate`).

**Rendering** — Google renders JS in two waves (can delay indexing days–weeks); AI bots render
JS worse than Googlebot. Content that only appears after JS may be invisible. *Signal:* CSR
detection (`audit`); `render.enabled`.

**Canonicalization** — telling engines the authoritative URL for duplicate/near-duplicate
content. Cross-canonicals can de-index a page. *Signal:* `audit` canonical check.

**Cannibalization** — multiple pages competing for the same query, splitting authority.
*Signal:* `audit` duplicate + `consolidate` (keep-one / 301-redirect).

**Core Web Vitals** — real-user experience at the 75th percentile: **LCP < 2.5 s** (load),
**INP < 200 ms** (responsiveness — replaced FID; the most-failed vital), **CLS < 0.1** (visual
stability). *Signal:* `speed` (lab + field).

**Structured data (schema.org / JSON-LD)** — machine-readable page facts. Foundational in
2026, not polish; FAQ/HowTo/Article help AI inclusion. *Signal:* `schema` (generate + validate).

**Internal linking & topical authority** — authority accrues at the **cluster** level: a
pillar page linking to members, members linking back and to each other. *Signal:* `authority`
(density + pillar) and `inlinks` (who should link where).

**E-E-A-T** (Experience, Expertise, Authoritativeness, Trust) — not a score Google exposes, but
its **signals are measurable**: named authors + credentials, dates, citations to primary
sources, trust pages, HTTPS. ~85% of AI-Overview-cited pages carry several. *Signal:* `eeat`.

**hreflang / i18n** — language/region targeting; needs an `x-default` and reciprocal tags.
*Signal:* `audit` hreflang.

**Backlinks & toxicity** — links still matter for authority, but in 2026 **disavow is rarely
needed**: SpamBrain auto-ignores spam, and low authority ≠ toxic. Only disavow on a manual
action or documented negative-SEO event. *Signal:* `backlinks` (gap) + `toxicity` (conservative).

**Striking distance** — queries at positions ~5–15: one push from page 1. But discount by
**AI-Overview presence** — an AIO caps the clicks a #1 earns. *Signal:* `gsc` + `aio`.

**Content decay** — pages losing rank/clicks over time; refreshing usually beats net-new.
*Signal:* `decay` (needs GSC history).

**Algorithm updates** — Google ships named core/spam updates (and ~13 changes/day). Attribute
traffic shifts to them. *Signal:* `algo` + `radar` (watches the Search Status Dashboard).

**AEO / GEO** — optimizing to be cited by answer/generative engines. SEO + extractability. See
[AI-Search.md](AI-Search.md).

## Fix order (why the Site Doctor is ordered this way)
Crawl/index blockers first (nothing else matters if pages can't be crawled/indexed) → content
signals (titles, dedup, depth, schema) → internal linking (orphans, clusters) → then optimize
(decay, striking-distance, CTR). `plan` encodes this priority automatically.

## Canonical sources to follow
Ground truth first: **Google Search Central blog** and the **Search Status Dashboard**
(dated core/spam updates across Crawling/Indexing/Ranking/Serving). Then **Search Engine
Roundtable** (fastest confirmation), **Search Engine Land** (update library), large-sample
studies from **Ahrefs** and **SparkToro**, and syntheses from **Kevin Indig (Growth Memo)** and
**Aleyda Solis (SEO FOMO)**. `radar` follows the machine-readable ones; the rest are monthly
human review. Full cadence in [BUILDLOOP.md](../BUILDLOOP.md).

## Sources
Core Web Vitals thresholds — [web.dev](https://web.dev/articles/defining-core-web-vitals-thresholds).
Sitemaps — [Google](https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps).
llms.txt reality — [Search Engine Journal](https://www.searchenginejournal.com/googles-says-its-fine-to-use-llms-txt-for-ai-seo/579608/).
AI-Overview click impact — [Ahrefs](https://ahrefs.com/blog/ai-overviews-reduce-clicks-update/) ·
[Search Engine Land](https://searchengineland.com/google-zero-click-searches-2026-study-479717).
Log-file analysis — [Search Engine Land](https://searchengineland.com/guide/log-file-analysis).
E-E-A-T — [Ranking Lens](https://blog.rankinglens.com/eeat-checklist-2026).
Topical authority — [Digital Applied](https://www.digitalapplied.com/blog/seo-content-clusters-2026-topic-authority-guide).
Disavow in 2026 — [Editorial.link](https://editorial.link/disavow-backlinks/).
Accessibility & SEO — [SearchAtlas](https://searchatlas.com/blog/accessibility-a11y-seo-ranking-factor-2026/).
GEO/AEO — [Growth Memo](https://www.growth-memo.com/p/state-of-ai-search-optimization-2026).
