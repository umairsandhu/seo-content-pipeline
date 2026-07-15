# Build loop — keeping this the best SEO tool in the world

SEO is a moving target: Google shipped **4,725 search changes in 2022** (~13/day) and
keeps landing named core/spam updates (March 2026 core, May 2026 core, June 2026 spam…).
A tool is best-in-class only if it *changes as the search landscape changes*. This is the
process that keeps it there.

**The loop in one line:** `monitor canonical sources → detect a signal → encode it as a
check/metric → validate on a golden test site → ship → benchmark vs best-in-class`.

The sensor is built in: **`python -m seo_agent radar`** watches Google's Search Status
Dashboard and flags when our own `algo.py` update knowledge goes stale.

---

## The three clocks

### Weekly — react to your own data
- `run` → decay, striking-distance, low-CTR, cannibalization diffs vs last week.
- `gsc` (snapshot, builds history), `backlinks` link-gap, competitor `gap`.
- **Act:** refresh decaying posts, `retitle` low-CTR pages, add internal links, draft the
  top gap. Ship as PRs (human merge gate).

### Monthly — react to Google + refresh the audit
- `radar` → new algorithm updates? Append confirmed ones to `algo.py` UPDATES.
- `algo` → attribute traffic shifts to updates within your snapshot window.
- `run --monthly` → trends/emerging keywords, backlink gap, gaps, algo impact.
- Re-run `audit` (Site Doctor) → technical drift (new orphans, thin pages, sitemap/CWV).
- **Act:** if an update coincides with a drop, diagnose against that update's theme
  (core = quality/relevance, spam = policy) and queue fixes.

### Quarterly — evolve the tool itself
- **Re-pull AI-search stats** (they have a short shelf-life — see Caveats). Re-tune any
  AIO-adjusted CTR model.
- **Benchmark** our output on a fixed *golden test site* against a best-in-class tool
  (Screaming Frog / Sitebulb / Ahrefs): what do they flag that we don't? Each miss becomes
  a roadmap item.
- **Ship one capability** off the roadmap below (must-haves first).
- **Re-research the open questions** (below) — the landscape may have moved.

---

## Canonical sources to monitor

Ground truth first, commentary second. `radar` follows the machine-readable ones; the rest
are human review (monthly, or on a volatility spike).

| Source | Best for | Cadence | Machine-followable |
|---|---|---|---|
| **Google Search Status Dashboard** — status.search.google.com | Authoritative dated incidents across Crawling/Indexing/Ranking/Serving | Real-time | ✅ (`radar`) |
| **Google Search Central blog** — developers.google.com/search/blog | Confirmed updates, new features, official best-practice | On release | ~ (scrape) |
| **Search Engine Roundtable** (Barry Schwartz) — seroundtable.com | Fastest confirmation + community chatter on updates | Daily | ~ (feed) |
| **Search Engine Land** — algorithm-updates library | Curated dated update history + analysis | On update | ~ |
| **Ahrefs blog** | Large-sample studies (e.g. AIO click-impact) | Weekly | — |
| **SparkToro** (Rand Fishkin) | Zero-click / clickstream reality checks | Monthly-ish | — |
| **Semrush Sensor / Mozcast / AccuRanker Grump** | SERP volatility "weather" — spikes = an update is live | Daily | ~ (some APIs) |
| **Kevin Indig — Growth Memo** | The best synthesis on AI-search direction (AEO/GEO) | Weekly | — |
| **Aleyda Solis — SEO FOMO** newsletter | Curated weekly firehose, well-filtered | Weekly | — |
| **Glenn Gabe, Lily Ray** | Deep core-update post-mortems | Per update | — |

Rule: a claim is actionable only when a **primary** source (Google) or a **large-sample
study** (Ahrefs/SparkToro) backs it — not a single vendor blog.

---

## How a monitored change becomes a tool change

1. **Detect** — `radar` or a source flags a change (update, new signal, new report).
2. **Classify** — is it (a) a new *check* the Site Doctor should run, (b) a new *metric* to
   track over time, (c) a *content-quality* signal, or (d) noise?
3. **Encode** — smallest change that captures it: a finding in `audit.py`, a snapshot kind
   in `history.py`, an entry in `algo.py`, a provider call. Keep it deterministic + degrade
   gracefully (the whole codebase's contract).
4. **Validate** — run it on the golden test site; confirm it fires on a known-positive and
   stays quiet on a known-negative. No false-positive floods.
5. **Ship** — PR, update the relevant `.md`, note it in the digest.
6. **Benchmark** — quarterly, check the change against how a best-in-class tool treats the
   same signal.

---

## Capability-gap roadmap (from the 2026 research)

Ranked by evidence strength + leverage. ✅ have · 🔨 build · 🔬 needs its own research pass.

### MUST-HAVE (verified 3-0, high leverage)
1. ✅ **AI-Overview-adjusted CTR model** — `aio.py` / `aio`. Encodes the verified position
   degradation table (pos1 −58 → pos10 −19%), detects AIO presence via SERP data, and
   re-ranks striking-distance by real AIO-aware upside. Re-pull the table quarterly.
2. 🔨 **AI-search / LLM visibility tracking.** Google's June 2026 GSC "Generative AI
   performance" report is the first-party feed — but currently UI-only, impressions-only,
   subset rollout, **no API yet**. Registered as `ai_search_visibility` (tier: future) —
   wire the moment an API ships; meanwhile `logs` AI-crawler coverage is the proxy.
3. ✅ **Server log-file analysis** — `logs.py` / `logs`. Parses access logs, classifies
   Google + AI crawlers (GPTBot/ClaudeBot/PerplexityBot…), reports crawl waste, crawl
   distribution, and AI-crawler coverage of indexable pages. (Crawl budget matters below
   1M pages too — the "only huge sites" claim was **refuted**.)
4. ✅ **JavaScript rendering** — `render.py` (optional Playwright backend, `render.enabled`).
   Renders SPA/CSR pages in headless Chromium before auditing so they aren't mis-reported.
   Always-on CSR heuristic (ingest sets `csr`) flags likely client-rendered pages even when
   rendering is off, so you know to enable it. Table-stakes across every top crawler.
5. ✅ **Rank + SERP-feature tracking over time** — `rank.py` / `rank`. Snapshots position +
   SERP features (AIO/snippet/PAA/video/shopping/local/knowledge-graph) per keyword and diffs
   run-over-run (moved up/down, features gained/lost).

All five verified must-haves shipped. Beyond the roadmap, now also built: the **action
engine** (`plan`), **schema** generation + validation, **content-comprehensiveness**
scoring (`score`), deeper audits (redirects, broken links, hreflang), and the **0→100
PLAYBOOK.md**.

The 🔬 frontier is now built too, each grounded in a 2026 research pass:
- **E-E-A-T** (`eeat`) — author bylines, dates, outbound citations, trust pages, HTTPS
  (the measurable signals AI Overviews cite; not a direct score).
- **Topical authority** (`authority`) — topic clusters + pillar/internal-link density.
- **Accessibility** (audit `a11y` + PSI a11y score) — alt text, `lang`, heading order
  (not a direct ranking factor, but the structure Google rewards).
- **Backlink toxicity** (`toxicity`) — deliberately conservative: 2026 reality is that
  disavow is rarely needed (SpamBrain auto-ignores spam; low authority ≠ toxic).
- **Recommenders** — `consolidate` (cannibalization → keep/redirect) and `inlinks`
  (reverse internal-link suggestions).

Still open (blocked / needs more evidence): AI-search visibility ingestion (waiting on a
GSC Generative-AI API), and a rigorous topical-authority/E-E-A-T *scoring model* beyond the
structural heuristics here.

**Adding any new API is one entry** in `integrations.py` (the registry): tier, env/config,
what it unlocks, alternatives. Onboarding, `.env.example`, and the capability matrix
(`integrations`) all read from it — so the skill stays self-configuring as providers change.

### NICE-TO-HAVE / breadth (round out the Site Doctor — thinner evidence, own research pass)
6. 🔬 **Topical-authority / entity-coverage + content-comprehensiveness scoring** (the
   Surfer/Clearscope/MarketMuse layer). We *find* gaps but don't *score* depth vs the SERP.
   No implementable methodology surfaced — research before building.
7. 🔬 **Schema generation + validation** (JSON-LD): we detect presence; generate + validate.
8. 🔬 **Redirect-chain + broken-link crawling**, **hreflang/i18n audits**,
   **backlink toxicity**, **accessibility**, **E-E-A-T signal** checks — all raised, none
   substantiated by the research; treat as open gaps, scope each on its own.

### Do NOT build (refuted this pass)
- "Crawl budget only matters above ~1M pages" — false; keep #3 broadly scoped.
- "Only Botify integrates logs natively / only cloud tools handle 1M+ pages" — false framing.
- Screaming Frog "AI prompts + embeddings in-crawl" — **unverified**; confirm before citing.

---

## Open questions — re-research quarterly
- Will Google expose the GSC Generative-AI report via **API** (with clicks/CTR/query)? That
  unlocks #2 fully.
- What concrete **scoring methodology** for topical authority / comprehensiveness / E-E-A-T?
- How to measure **AI-answer citation share** across engines (Google AIO/AI Mode, ChatGPT,
  Perplexity, Claude) — GSC only covers Google; server logs only show crawls, not citations.

## Caveats (from adversarial verification)
- **AI-search stats are directional and short-shelf-life** — figures vary by methodology
  (Ahrefs 58% vs Seer 61% vs Pew 46.7% vs Semrush prevalence ~16% vs SparkToro 20%+).
  Re-pull quarterly; don't hard-code a single number as truth.
- Evidence is strong on: AI-search click impact, log-file analysis, JS rendering,
  update-attribution. Everything in "nice-to-have" is **under-evidenced** — verify before
  investing.
