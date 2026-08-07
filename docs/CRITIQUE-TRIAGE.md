# External critique (GLM, 2026-07-30) — triage & response

An external deep-read called the tool "70% of the way to a standalone SEO agency —
breadth over depth." We verified every claim against the code. Verdict: **~60% of the
critique was correct and actionable, ~25% was already built (the reviewer missed it),
~15% conflicts with our local-first design and is rejected with reasons.** This doc is
the permanent record; unbuilt accepted items live in LAUNCH-PLAN **W10**.

## ✅ Correct → BUILT (same day, commit-linked)

| Critique | What shipped |
|---|---|
| consult evidence truncated at 6,000 chars | raised to 24,000 + forecast added to the pack |
| No scenario/ROI modeling | `consult.forecast()` — conservative/expected/upside monthly-clicks from striking-distance × CTR curve, assumptions stated |
| Binary equal-weight GEO scoring | `geo.WEIGHTS` — access (renderable, AI-crawlable ×2.0) > extraction (schema, Q&A ×1.5) > trust (author ×0.75); priorities = weight × missing count |
| No redirect-chain / canonical-chain / indexability matrix | new `indexability.py`: canonical chains, canonical→non-indexable, cross-domain canonicals, noindex+disallow conflict, noindex+canonical conflict, soft-404s, internal links to redirecting URLs, live hop-trace (loops, 302-as-permanent) — wired into `audit` |
| No mobile-first checks | viewport captured at ingest + `audit.mobile()` (PSI accessibility covers tap-targets/legibility via `speed`) |
| Speed samples "first 10 crawled" | `speed.sample_urls()` — homepage + top-GSC-clicks money pages + one page per template/section |
| No CWV history | `speed` now snapshots to `history/cwv/` + reports trend |
| Schema limited to 6 types | +HowTo, Product/Offer, LocalBusiness, Review/AggregateRating, Event, VideoObject, QAPage, Recipe, JobPosting, Course, SoftwareApplication (generators + validation) — and `schema.coverage()`: sitewide @type census + expected-type gaps per section |
| Thin content briefs | intent classifier (informational/commercial/transactional/local) + per-intent reader-state/must-haves/length + angle-&-UVP requirement in every assignment |
| Voice learning only reactive | new `voice.py` — measures the site's existing voice (sentence rhythm, person, contractions, heading style, titles) → brain preference → injected into every draft from day one |

## 📋 Correct → TRACKED (LAUNCH-PLAN W10)

Migration monitoring mode · post-apply verification (folds into W3) · entity coverage
gap analysis (topic → expected entities) · real AI-Overview/SERP citation tracking
(DataForSEO AIO item extraction, beyond synthetic prompts) · refresh-why depth ·
editorial calendar · multi-format briefs (landing/product/comparison) · API quota +
cost tracker · competitor reverse-engineering (structure, not just URLs) · deeper
portfolio view · issue-tracker handoff (Jira/Linear/GH Issues) · readability +
completeness scoring in the gate · hreflang depth · pagination/parameter audit.

## ❌ Wrong or already built (reviewer missed it)

| Claim | Reality |
|---|---|
| "No log file analysis depth" | `logs.py` exists: crawl budget, AI-crawler coverage, status distribution, bot frequency — wired into audit/journey |
| "No dashboard/reporting layer" | `serve` = 10-panel guided dashboard (+ inline approvals); `report --pdf --email` |
| "No A/B testing framework" | designed & tracked as W5 (experiment engine) before this critique |
| "No multi-site portfolio" | `projects.py` portfolio + readiness roll-up (depth improvements → W10) |
| "No alerting" | `anomaly --alert` pushes to Slack/Mattermost/WhatsApp/email; real-time is a non-goal for a local-first tool — cron cadence is the design |
| "No verification loop" | ledger follow-ups at +7/28/90d exist; *immediate* post-apply verification accepted → W3 |
| "Make JS rendering default-on" | **Rejected as stated** — Playwright-by-default breaks zero-dep install. Our version: CSR heuristic at ingest + a high-sev audit finding escalating `render.enabled` when CSR is detected (auto-render when Playwright is present) |
| "Transformer-based sentiment" | **Rejected** — no heavyweight ML deps in a stdlib-first tool. Agent-driven runs already get LLM-grade sentiment (the driving model judges); headless runs can use the configured `llm.provider`. A wordlist→provider upgrade is in W10 |

**The meta-lesson (LEARNINGS #24):** "shipped" must mean *deep enough for the role that
depends on it* — every capability row now needs a depth check, not an existence check.
