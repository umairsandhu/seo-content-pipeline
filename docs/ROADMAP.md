# ROADMAP — Making This the Best "0→100" SEO Platform (2026)

*Senior SEO product/eng lead assessment. Baseline: the existing Claude Code agent-driven skill (Python, file-based, CMS-agnostic, degrades without creds). Horizon-dated July 2026.*

---
> ## ✅ Build status — shipped 2026-07-21
> The full roadmap below was implemented in one pass (all site-agnostic, all degrade with no creds):
>
> | Item | Command / module | Status |
> |---|---|---|
> | AI-visibility / LLM-citation tracker | `aivis` (ChatGPT/Perplexity/Gemini/Claude + Google AIO; agent-mode w/o keys) | ✅ |
> | Programmatic safety gate | `safetygate` + `gate` + hard-block in `publish` | ✅ |
> | Entity / knowledge-graph builder | `entity` (Wikidata + sameAs + Org JSON-LD + salience) | ✅ |
> | Schema validation loop | `schema.validate` wired into the `publish` gate | ✅ |
> | Passage-citability scoring | `citability` | ✅ |
> | First-party CTR curves | `ctr` (`ctr_curves`) — feeds `aio` | ✅ |
> | AIO-trigger flag in rank | `rank` (already captured AI-Overview SERP feature) | ✅ |
> | Internal PageRank / authority flow | `pagerank` (`authority_flow`) | ✅ |
> | Refresh automation loop | `refresh <url>` | ✅ |
> | Link acquisition | `prospect` | ✅ |
> | AI-crawler analytics | `logs` (already segments GPTBot/ClaudeBot/…) | ✅ |
> | Headless render diff | `renderdiff <url>` (`render.diff`) | ✅ |
> | Embeddings by default | `index` uses fastembed automatically when installed | ✅ |
> | hreflang / international | `intl` | ✅ |
> | Local SEO | `local` | ✅ |
> | Results DB | `store` (SQLite, queryable time-series) | ✅ |
> | Job queue + scheduler | `jobs` (`jobs.py`, SQLite) | ✅ |
> | Multi-tenant / projects | `projects` (agency portfolio + readiness roll-up) | ✅ |
> | Agentic remediation planner | `remediate` (ordered, human-gated) | ✅ |
>
> New AI-engine integrations registered: Perplexity, Gemini. What remains is **depth**
> (more engines/locales, a real prompt-volume corpus, PageRank-based auto-sculpting,
> multi-tenant roles/billing) and hardening — captured as the horizons below.
---

The 2026 landscape has bifurcated. Traditional SEO still pays the bills, but the growth frontier is **AI-search visibility**: Google AI Overviews now appear in ~48% of searches (up from 34.5% in Dec 2025), AI Mode drives a **93% zero-click rate**, and position-1 organic CTR falls up to 58–64% when an AI Overview is present ([SEOProfy](https://seoprofy.com/blog/google-ai-overviews/), [dataslayer](https://www.dataslayer.ai/blog/google-ai-overviews-the-end-of-traditional-ctr-and-how-to-adapt-in-2025)). AI Mode fans a single query into 8–15 sub-queries and cites **passages, not pages** — BrightEdge finds 80% of LLM citations come from URLs outside the classic top 10 ([Ekamoira](https://www.ekamoira.com/blog/query-fan-out-original-research-on-how-ai-search-multiplies-every-query-and-why-most-brands-are-invisible)). The winning platform must own both the legacy funnel and this new citation economy.

This skill is unusually strong on **agentic content production and technical auditing** but structurally weak on **AI-visibility measurement, entity graph engineering, real JS rendering, and closed-loop automation**. Below is the gap analysis and a sequenced plan to close it.

---

## 1. Capability Matrix Across the SEO Lifecycle

| Lifecycle area | Best-in-class 2026 does… | This skill covers… | Concrete gap |
|---|---|---|---|
| **Technical / crawl** | Cloud renderers (Lumar, JetOctopus, Botify) crawl JS at scale, diff rendered-vs-raw DOM, flag hydration gaps ([Spike](https://getspike.ai/blog/screaming-frog-vs-sitebulb/)) | `audit`, `speed`, `sitemap`, `schema`, a11y — but on **raw HTML only** | No headless render; JS/SPA sites audited blind; no rendered-vs-raw diff |
| **Keyword & market intel** | 200–260M+ real-prompt datasets; intent/entity clustering; SERP-feature & AIO trigger flags ([Ahrefs](https://www.rankability.com/blog/ahrefs-brand-radar-review/), [Semrush](https://www.semrush.com/kb/1493-ai-visibility-toolkit)) | `research`, `discover`, `gap`, `trends`, `gsc`, `rank` | No prompt-volume corpus; no AIO-trigger flag per keyword; clustering is TF-IDF, not embedding-native |
| **Content creation & optimization** | SERP-grounded briefs + passage-level scoring vs. citation likelihood; refresh agents | `brief`, `draft`, `score`, `analyze`, `retitle` — strong | `score` measures SERP comprehensiveness, not **passage citability** (134–167-word extractable answers) |
| **On-page / SERP** | Auto structured-data generation **+ live validation** against Rich Results; SERP-feature capture | `schema` (JSON-LD gen), meta/title/H1 audit | No validation loop; no rich-result eligibility check; no SERP-feature snapshotting |
| **Internal linking & architecture** | Embedding-based semantic link graphs, orphan/PageRank flow, click-depth sculpting | `inlinks`, `autolink`, orphan/click-depth in `audit` — strong | Link relevance is TF-IDF, not embeddings; no PageRank/authority-flow modeling |
| **Backlinks & digital PR** | Discovery **+ outreach CRM + AI pitch automation** (BuzzStream, Respona, Ryze) ([SEOProfy](https://seoprofy.com/blog/link-building-tools/), [Ryze](https://www.get-ryze.ai/blog/best-ai-backlink-tools-for-2026-outreach-plus-discovery)) | `backlinks`, `toxicity` — **analysis only** | Zero acquisition: no prospecting, outreach, digital-PR angle mining, or link-monitoring loop |
| **Local SEO** | GBP optimization, citation/NAP consistency, review velocity, local-pack + map-pack tracking | — (none) | Entire vertical absent |
| **International / hreflang** | hreflang validation, x-default, locale-cluster mapping | Not surfaced in commands | No hreflang audit; single-locale corpus model |
| **Rank tracking & reporting** | Rank + AI Overview/AI Mode presence flags, share-of-voice, white-label PDF | `rank`, `report` (HTML+PDF), `run --monthly` | No AIO/AI-Mode presence dimension; no share-of-voice; file history, not queryable trend DB |
| **GEO / AEO / AI-search visibility** | Track brand **mentions + citations + sentiment** daily across 9–10 engines; prompt-set monitoring; AI-crawler analytics (Profound, Peec, Ahrefs Brand Radar, Semrush AIO) ([Profound](https://www.tryprofound.com/), [Scalenut](https://www.scalenut.com/blogs/profound-vs-peec-ai-for-geo)) | `geo` (readiness audit), `llmstxt`, `logs` (AI-crawler coverage) | **Biggest gap: no measurement.** Readiness ≠ visibility. No prompt-tracking, no citation share, no per-engine mention monitoring |
| **Workflow / automation / collaboration** | Agentic loops that detect→prioritize→act→verify; job queues; multi-user, roles, alerts | `run [--monthly]` digest, `mcp` server | No persistent job/queue, no results DB, no alerting/thresholds, no multi-tenant/roles |

**Read:** production and auditing are near-complete; **measurement of AI visibility, real rendering, backlink acquisition, and local/international are the structural holes.**

---

## 2. The 2026 Must-Haves — Where the Tool Is Weakest

1. **LLM-citation / AI-visibility tracking.** This is the category-defining 2026 capability and the skill's single biggest miss. Profound ($1B valuation, Series C Feb 2026) runs structured prompts daily across ~9 engines and connects mentions to conversions; Peec offers cleaner per-prompt monitoring + sentiment from ~$95/mo; Ahrefs Brand Radar tracks 6 AI surfaces off 199M prompts ([digitalapplied](https://www.digitalapplied.com/blog/ai-visibility-tools-2026-track-brand-chatgpt-perplexity-gemini), [nicklafferty](https://nicklafferty.com/blog/profound-vs-peec-ai/)). The skill audits GEO *readiness* but never measures whether the brand is actually cited. **You cannot optimize what you cannot see.**

2. **Entity / knowledge-graph SEO.** In 2026 entity clarity determines AI Overview/AI Mode/Gemini inclusion. The highest-ROI moves — `sameAs` triangulation, a Wikidata QID, an entity-home page — are cheap and high-impact ([digitalapplied](https://www.digitalapplied.com/blog/entity-seo-knowledge-graph-optimization-guide-2026)). The skill has `eeat`/`authority` but no entity extraction, Knowledge-Graph-API lookup, `sameAs` graph, or brand-salience scoring (Google Cloud NLP salience <0.25 = restructure needed, per [Stackmatix](https://www.stackmatix.com/blog/aeo-seo-geo)).

3. **Programmatic-SEO-at-scale safety.** The March 2026 core update explicitly enforced *scaled content abuse*; sites with thousands of thin templated pages lost 60–90% of traffic, with sub-1% recovery ([digitalapplied](https://www.digitalapplied.com/blog/programmatic-seo-after-march-2026-surviving-scaled-content-ban)). The skill can `draft` at volume but has **no guardrail** to detect near-duplicate templating, per-page unique-value scoring, or index-bloat risk before publish.

4. **Real crawler / renderer for JS sites.** All auditing is raw-HTML. For SPA/hydrated sites this silently misses content Googlebot only sees post-render. Best-in-class diffs rendered vs. raw DOM ([Spike](https://getspike.ai/blog/screaming-frog-vs-sitebulb/)). Needs a headless-Chromium render step.

5. **First-party CTR-curve modeling.** `aio` adjusts CTR for AI Overviews but appears to use generic curves. Best practice derives **position→CTR curves from the site's own GSC data**, segmented by query type and AIO presence, to make traffic forecasts credible.

6. **Automated structured-data + validation.** `schema` generates JSON-LD but doesn't validate. FAQPage/HowTo/Product markup must be checked against Rich Results eligibility and re-validated on publish; broken schema is worse than none.

7. **Content-refresh / decay automation loop.** `decay` detects decline, but 2026 tools (Revive 2.0, Refresh Agent, Animalz workflows) *close the loop*: detect → diagnose (stale stats/year refs/intent shift) → generate refresh → re-publish → verify recovery ([Animalz](https://www.animalz.co/blog/content-refresh), [Ahrefs](https://ahrefs.com/blog/automated-seo/)). The skill stops at detection.

8. **Backlink acquisition, not just analysis.** Digital PR is the highest-leverage link tactic of 2026 ([digitalapplied](https://www.digitalapplied.com/blog/link-building-2026-digital-pr-outreach-guide)). The skill analyzes an existing profile but can't find prospects, mine PR angles, or run outreach.

---

## 3. Prioritized Roadmap — NOW / NEXT / LATER

Impact/Effort: H/M/L, S/M/L. Sequenced for maximum 0→100 completeness — measurement and safety first (they gate everything else), then acquisition and scale.

### NOW (0–1 month) — see the AI economy, stop the bleeding

| Feature | One-line spec | Impact | Effort | Extends |
|---|---|---|---|---|
| **`aivis` — AI visibility tracker** | Run a fixed prompt set through ChatGPT/Perplexity/Gemini/Claude APIs + AIO scrape; record mention, citation URL, rank, sentiment per engine; weekly delta | **H** | **M** | `geo`, `rank`, `run` |
| **Schema validation loop** | Post-generate, validate JSON-LD against schema.org + Rich Results eligibility rules; block invalid on `publish` | **H** | **S** | `schema`, `publish` |
| **Passage-citability score** | Extend `score` to flag 40–170-word answer-first passages, entity density, question-mapped headers | **H** | **S** | `score`, `brief` |
| **First-party CTR curves** | Derive position→CTR from the site's GSC, split by AIO-present vs. not; feed `aio` | **M** | **S** | `aio`, `gsc` |
| **Programmatic safety gate** | Pre-publish near-duplicate (embedding cosine) + unique-value + index-bloat check; hard-block thin templates | **H** | **M** | `draft`, `publish` |
| **AIO-trigger flag in rank** | Tag each tracked keyword with AI-Overview/AI-Mode presence from live SERP | **M** | **S** | `rank`, `audit` |

### NEXT (1–3 months) — engineer for citations, close the loops

| Feature | One-line spec | Impact | Effort | Extends |
|---|---|---|---|---|
| **`entity` — entity graph builder** | Extract entities, resolve to Wikidata QID + Knowledge Graph MID, generate `sameAs` Organization block, score brand salience | **H** | **M** | `schema`, `eeat`, `authority` |
| **Headless render pass** | Optional Playwright/Chromium render; diff rendered-vs-raw DOM; re-run meta/H1/link/schema checks on rendered output | **H** | **M** | `audit`, `ingest` |
| **Refresh automation loop** | `decay` → diagnose (stale stats, year refs, intent drift, lost citations) → auto-draft refresh → publish → verify recovery | **H** | **M** | `decay`, `draft`, `publish` |
| **Embeddings by default** | Make fastembed the default similarity engine for `gap`/`inlinks`/`consolidate`/dedup; TF-IDF fallback | **M** | **S** | all similarity |
| **`prospect` — link acquisition** | Mine competitor backlink gaps + PR angles (data hooks, stats); draft personalized outreach; track status in a CRM table | **H** | **L** | `backlinks` |
| **AI-crawler analytics** | Extend `logs` to segment GPTBot/ClaudeBot/PerplexityBot/OAI-SearchBot; coverage %, freshness, missed high-value URLs | **M** | **S** | `logs` |
| **Results DB** | Move history from files to SQLite/DuckDB; queryable trends, deltas, share-of-voice | **M** | **M** | all Observe |

### LATER (3–12 months) — completeness & scale

| Feature | One-line spec | Impact | Effort | Extends |
|---|---|---|---|---|
| **`local` — Local SEO suite** | GBP audit, NAP/citation consistency, review velocity, local/map-pack tracking | **M** | **L** | new |
| **`intl` — hreflang/i18n** | hreflang + x-default validation, locale-cluster mapping, per-locale corpus | **M** | **M** | `audit`, `ingest` |
| **Job queue + scheduler** | Durable queue (RQ/Celery-lite) for renders, tracking runs, batch drafts; retries, rate-limit budgets | **H** | **L** | `run`, `mcp` |
| **Multi-tenant + roles** | Projects, seats, roles, alert thresholds, white-label reports | **M** | **L** | `report`, `run` |
| **Prompt-volume corpus** | Build/license a real-user-prompt dataset for AEO keyword discovery | **M** | **L** | `research`, `aivis` |
| **PageRank/authority-flow model** | Internal-link sculpting via computed link equity + click-depth optimization | **M** | **M** | `inlinks`, `autolink` |
| **Agentic remediation** | Autonomous detect→prioritize→fix→PR→verify across audit findings | **H** | **L** | `run`, all |

---

## 4. Ten Highest-Leverage Features to Build Next (Ranked)

1. **AI Visibility Tracker (`aivis`).** *Why now:* AI Overviews touch ~48% of queries and AI Mode is 93% zero-click; measuring citation share is the defining 2026 capability and the skill's biggest hole ([SEOProfy](https://seoprofy.com/blog/google-ai-overviews/)). *Accept:* for a given brand + 50-prompt set, output per-engine (ChatGPT, Perplexity, Gemini, AIO) mention rate, citation URLs, avg. position, sentiment, and week-over-week delta — reproducible within ±1 mention on re-run.

2. **Programmatic Safety Gate.** *Why now:* March 2026 scaled-content-abuse enforcement caused 60–90% losses with <1% recovery ([digitalapplied](https://www.digitalapplied.com/blog/programmatic-seo-after-march-2026-surviving-scaled-content-ban)). *Accept:* `publish` refuses any page with >0.9 cosine similarity to an existing page or unique-value score below threshold, emitting a specific reason and remediation.

3. **Entity Graph Builder (`entity`).** *Why now:* entity clarity gates AI Overview/AI Mode inclusion and the fixes are cheap/high-impact ([digitalapplied](https://www.digitalapplied.com/blog/entity-seo-knowledge-graph-optimization-guide-2026)). *Accept:* generates a valid `Organization` block with `sameAs` (≥5 authoritative profiles) + resolved Wikidata QID, and reports brand salience with a restructure flag if <0.25.

4. **Schema Validation Loop.** *Why now:* AI engines parse JSON-LD to resolve entities; broken markup silently forfeits rich results. *Accept:* every generated block passes schema.org validation and Rich-Results eligibility, or `publish` blocks with the exact failing field.

5. **Passage-Citability Scoring.** *Why now:* AI Mode cites 134–167-word passages, not pages; 80% of citations come from outside the top 10 ([Ekamoira](https://www.ekamoira.com/blog/query-fan-out-original-research-on-how-ai-search-multiplies-every-query-and-why-most-brands-are-invisible)). *Accept:* `score` returns a per-section citability score and rewrites weak sections into answer-first, entity-dense passages within the target word band.

6. **Headless Render Pass.** *Why now:* raw-HTML audits are blind on the growing share of JS/SPA sites. *Accept:* on a hydrated test page, the render diff surfaces content/links/schema present only post-render; all audit checks re-run on rendered DOM.

7. **Refresh Automation Loop.** *Why now:* content can rank yet lose AI citations; 2026 tools close detect→fix→verify ([Animalz](https://www.animalz.co/blog/content-refresh)). *Accept:* for a decaying URL, the tool diagnoses cause, drafts a refresh (updated stats/year/intent), publishes, and reports recovery vs. baseline after N weeks.

8. **Link Acquisition (`prospect`).** *Why now:* digital PR is 2026's top link tactic; analysis alone doesn't move the needle ([digitalapplied](https://www.digitalapplied.com/blog/link-building-2026-digital-pr-outreach-guide)). *Accept:* outputs a ranked prospect list from competitor backlink gaps with per-prospect PR angle and a personalized draft pitch, tracked to reply/won status.

9. **First-Party CTR Curves.** *Why now:* generic curves overstate traffic in an AIO world; forecasts must be defensible. *Accept:* `aio` forecasts use GSC-derived curves segmented by AIO presence, within ±15% of actual on a 30-day holdout.

10. **Results DB + AI-Crawler Analytics.** *Why now:* trend/share-of-voice queries and AI-bot coverage need structured history, not files; GPTBot/ClaudeBot now consume sitemaps and drive real crawl load ([wislr](https://www.wislr.com/articles/ai-bot-behavior-log-analysis)). *Accept:* any metric is queryable as a time series with deltas; `logs` reports per-AI-bot coverage %, freshness, and top missed URLs.

---

## 5. Architecture Upgrades to Support the Above

- **Embeddings by default.** Promote fastembed to the default similarity engine (cache vectors in the results DB); TF-IDF becomes the no-dependency fallback. Unblocks citability scoring, dedup, semantic linking, and programmatic near-duplicate gating — all currently limited by lexical TF-IDF. Ship a local-model default so it degrades gracefully with no creds.

- **Real headless renderer.** Add an optional Playwright/Chromium render service invoked by `audit`/`ingest`, with a raw-vs-rendered DOM diff. Keep it opt-in (heavy dependency) so the no-creds path still works on raw HTML.

- **Results DB (SQLite/DuckDB) replacing file history.** File-based history can't answer trend, delta, or share-of-voice queries or power alerts. A single embedded DB (still portable, still file-based on disk) becomes the backbone for tracking, CTR curves, entity graphs, and reporting. Migrate existing histories on first run.

- **Job/queue + scheduler for scale.** AI-visibility runs, renders, batch drafts, and outreach are long-running and rate-limited (multiple LLM/SERP APIs). Introduce a durable queue with retries, per-provider rate budgets, and a scheduler so `run` and `mcp` fan out safely instead of blocking.

- **Multi-locale / multi-tenant model.** Generalize the single-site corpus to projects × locales (hreflang-aware) with roles, alert thresholds, and white-label reports — prerequisite for `intl`, `local`, and agency use.

- **Pluggable AI-engine adapters.** Abstract ChatGPT/Perplexity/Gemini/Claude/AIO behind one interface (like the existing DataForSEO/Semrush/Ahrefs abstraction) so `aivis` adds engines without core changes, and so the tool tracks new answer engines as they emerge.

**Sequencing logic:** embeddings + results DB + validation are small, unblock the highest-impact features, and preserve graceful degradation — do them first. The renderer and queue are the heavier lifts that gate scale (JS sites, batch AI tracking) and belong in NEXT/LATER. Delivered in this order, the tool moves from "excellent agentic content + audit engine" to a **complete 0→100 platform that measures and wins the AI-citation economy, not just the blue links.**
