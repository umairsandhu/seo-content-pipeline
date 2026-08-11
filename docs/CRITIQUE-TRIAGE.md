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

---

# Round 2 — devil's advocate (2026-08-08) — triage & response

## ✅ Correct → BUILT same day

| Point | What shipped |
|---|---|
| `content_score` dead-ends without DataForSEO | corpus-relative fallback: scores vs your own most-related pages (offline, `mode: "corpus-relative"`), prefers crawled copy over live fetch |
| No site-level "why is traffic down?" | new **`diagnose`** — ranked differential diagnosis wiring ledger + sitediff + Google-update timeline + zero-click alligator + decay + anomaly radar, each cause with evidence, confidence, and the next command |
| The moat is the loop; make it always-on | new **`agent`** daemon (OpenClaw shape, SEO-only): one long-running local process — heartbeat, instant high-sev channel alerts, daily autopilot cycle, weekly report delivery; restart-safe; replaces the cron lines |
| Parity claim overstated | positioning rewritten in ROADMAP (below) — we lead on the closed loop + AI-visibility + local-first monitoring; we are honestly behind on crawl depth (Screaming Frog), visualization (Sitebulb), editor UX (Surfer), topic modeling (MarketMuse), and proprietary indexes (Ahrefs/Semrush) |
| Portfolio mis-timed at H3 | promoted to H2; parity features (visual crawl map, spell-sweep) demoted below no-competitor-does-this items |

## ❌ Stale — already exists (round 2 reviewed an old snapshot)

Content brief generator → **`brief`** (SERP+PAA+intent+intake, 2026-08). Per-URL traffic
diagnostic → **`explain <url>`**. Schema *generation* → **`schema <url>`** (11+ types).
Internal-linking engine → **`autolink`/`inlinks`/`pagerank`** sculpt plans. Cannibalization →
**`consolidate`**. Log-file analysis → **`logs`** (crawl budget + AI bots). Backlink gap →
**`backlinks`** (link_gap). Content gap → **`gap`**. Topic clusters → **`authority`**.
Title/meta rewriter → **`retitle`**. SERP-feature tracking → **`rank`** (features captured).
Intent classification → in `brief`. CWV trend → `speed` history. Zero-click integration →
`zeroclick` + now `diagnose`. JS audit → `render.enabled` wired into ingest (opt-in by design).

## 📋 Accepted → tracked (H2 reorder)

Brief→draft→**score gate** in `crew` · real-time MCP content editor · SERP-feature
*opportunity mapping* · hreflang wired into audit CATS · redirect-map *planner* (sitediff
monitors; migration mode plans) · chat-first control of the `agent` daemon (phase 2).

**Meta-lesson:** external reviews keep auditing snapshots, not HEAD — keep this triage
doc current so the next reviewer starts from reality.

---

# Round 3 — the self-audit (2026-08-11)

We turned the audit inward: a full drift/fragmentation inventory of our own architecture
(~52 parallel registries, 93 commands documented in 4–5 drifting places, 6 incompatible
`_safe` helpers, 162 bare exception handlers — and four drifted pairs the audit itself
discovered). The verdict, the honest "couldn't have known vs didn't want to know" split,
and the v2 blueprint live in **[ARCHITECTURE-V2](ARCHITECTURE-V2.md)**.

**Round 3b — the complementary audit (2026-08-11).** The round-3 inventory was one lens
(static architecture); we then ran the three it skipped — a security attack-surface map, a
coverage measurement (33/85 modules untested), and an exact doc-content diff — in
**[AUDIT-COMPLEMENT](AUDIT-COMPLEMENT.md)**. Two HIGH security findings (dashboard CSRF,
email-approval spoofing) gate any public launch and need a `/security-review` hardening pass.
The re-asked rebuild verdict (registry-first survives, sharpened with a trust dimension) is
the **Round 2 addendum** in ARCHITECTURE-V2.
