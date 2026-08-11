# 🚀 Launch Plan — the living dashboard

> **Read [CHANGE-PLAN](CHANGE-PLAN.md) first.** It consolidates every pending change
> (security, rebuild, depth) into sequenced tiers and names the two security blockers (H1/H2)
> that must clear *before* these gates run. This file verifies; CHANGE-PLAN scopes.


**This file is the source of truth.** Every agent updates its checkboxes here as work
lands (same PR). Launch fires only when every **Gate** row is ✅.
Companion visual: the Launch Dashboard artifact · Status legend: ⬜ todo · 🟨 in progress · ✅ done · 🔒 gate

**The strategy in one line:** run the tool as a *localized, Hermes-like agent* on **3 real
sites in parallel** (each workspace = its own brain, ledger, and autopilot), while 6
engineering workstreams harden the loop — soft-launch when the pilots have 30 days of
clean cycles, full case study at 90 days.

---

## Launch gates (the definition of done)

| # | Gate | Status |
|---|---|---|
| G1 | 3 pilot sites each ran ≥30 daily autopilot cycles without manual rescue | ⬜ 🔒 |
| G2 | Attribution shows min-n + confidence intervals + confound flags (W2) | ✅ 2026-08-11 |
| G3 | Negative changes get rollback proposals automatically (W3) | ✅ 2026-08-11 |
| G4 | ≥4 CMS connectors verified against live sandbox accounts + CI green (W4) | 🟨 code done (CI green + contract tests + `cms --verify`) — live sandbox runs = human |
| G5 | `demo` gives a stranger the full aha in <5 min, zero keys (W6) | 🟨 built + auto-tested — human timed test pending 🔒 |
| G6 | Cross-site learning is opt-in with clear disclosure (W7) | ✅ |
| G7 | One public case study with real ledger numbers (≥30d) | ⬜ 🔒 |
| G8 | README claims audited — no superlative we can't screenshot | ✅ (re-check at launch) |
| G9 | Hand-held first run: `start` → guided web dashboard showing steps, learned best practices, and documents to review (W9) | 🟨 built — polish during pilots 🔒 |
| — | *Nice-to-have, not gating:* experiment engine v1 (W5) | ⬜ |

---

## W1 · The 3-pilot program (the "real work," softened)

Each pilot is an **independent workspace** running the full loop locally — its own
`config.json`, `.env`, `state/`, brain, and ledger. One good cycle a day each; ~15 min of
human attention across all three. That's the whole ask.

| Pilot | Site | Workspace | CMS | Status |
|---|---|---|---|---|
| P1 | trellus.ai (running) | `~/seo-workspaces/trellus-ai` | Webflow | 🟨 needs WEBFLOW_TOKEN + daily cadence |
| P2 | *(pick: your own / a friend's / markaz.app)* | `~/seo-workspaces/<site2>` | ? | ⬜ |
| P3 | *(pick: a different CMS than P1/P2 — ideally WordPress or Shopify)* | `~/seo-workspaces/<site3>` | ? | ⬜ |

**Stand up a pilot (10 min):**
```bash
mkdir -p ~/seo-workspaces/<site> && cd ~/seo-workspaces/<site>
python -m seo_agent init --site https://<site>
python -m seo_agent wizard          # CMS + creds + autonomy=approve + delivery
python -m seo_agent onboard         # baseline
```
**Make it a daily Hermes-like agent (cron on your machine):**
```cron
30 8 * * *  cd ~/seo-workspaces/<site> && python -m seo_agent gsc && python -m seo_agent autopilot --daily >> autopilot.log 2>&1
0  9 * * 5  cd ~/seo-workspaces/<site> && python -m seo_agent report --pdf --email
```
- [ ] P1: Webflow token in, ~~autonomy=approve~~ ✅, cron live, first 5 changes shipped · workspace + `~/.seo-agent` now under **local-only git backup** (2026-07-30); cross-site sharing consented
- [ ] P2: chosen + onboarded + cron live
- [ ] P3: chosen (different CMS) + onboarded + cron live
- [ ] All: GSC snapshot cadence confirmed (attribution needs it — LEARNINGS #19)
- [ ] Day 30: pull `ledger` + `learn` from all three → case-study draft (G7)

## W2 · Attribution you can defend (Gate G2) — ✅ done 2026-08-11

*Why: the brain must not learn noise. Shipped before any pilot data accrued.*

- [x] Diff-in-diff confirmed + documented: lift = change's delta − holdout-median delta over the
      same window (seasonality/weekday/algorithm effects common to the site cancel; proven by the
      synthetic-seasonal null test: sitewide +50% surge → lift ≈ 0, no false playbook)
- [x] Minimum evidence: playbooks/lessons require n≥3; ⏳ "collecting" markers in learn/practices
- [x] 95% CI on mean lift (t-interval, small-n table) + Wilson lower bound on win-rate — stored per
      cell, rendered in `learn` (±), `plan` do-more, `practices`, brain playbook text
- [x] `qualified` = n≥3 AND CI excludes zero — enforced in brain.distill, plan do-more,
      practices evidence, learn recommendations (unqualified evidence can never recommend)
- [x] Confound flag: change within ±5d of a Google update (`algo.UPDATES`) → `confounded` column,
      EXCLUDED from all learning aggregates, surfaced in `learn` ("N follow-ups excluded")
- [x] Tests: consistent-wins-qualify · noisy-mean-does-NOT-qualify · seasonal-null ·
      confound-exclusion (4 new; demo upgraded to n=3 so the aha shows real CIs)

## W3 · Auto-rollback + post-apply verification (Gate G3) — ✅ done 2026-08-11

*Why: an autonomous bot is only trustable if it can undo itself.*

- [x] `ledger` captures a **before-state** (title/meta/H1) at change time + a `verified` flag;
      `site_control.change` snapshots the live page before meta/content ops (`rollback.capture`)
- [x] **Post-apply verification**: after a live meta/content change, re-fetch and confirm the new
      title/meta is present (`rollback.verify`) → the ledger row is marked verified 1/0, so a
      change that didn't land can't pollute attribution
- [x] `rollback <change_id>` command + MCP tool → inverse `site_control` op from the stored
      before-state, autonomy-gated, logged as `rollback:<type>`
- [x] Autopilot report phase: `rollback.proposals` finds change types measured **negative at
      +28d (n≥3, CI excludes 0)** → approve mode queues them for review, auto mode reverts
      (capped 2/cycle), manual reports; every one teaches the brain an **avoid-lesson**
- [x] Tests: capture+restore · refused-without-before-state · proposals-flag-losers-only ·
      autopilot-queues-in-approve-mode (4). Demo seeds a revertable loser.

## W4 · Connectors proven live + CI (Gate G4) — 🟨 code done 2026-08-11

*Why: "smoke-tested offline" is not a launch claim.*

- [x] `cms --verify` (+ MCP): create → update → delete a throwaway draft against the configured
      CMS's LIVE API, pass/fail per step (runs the real publish + site_control dispatch);
      degrades to a clear "not configured" per step
- [x] **Connector contract tests** — `cms_extra._http` is monkeypatched to capture each
      connector's request + feed a canned response, proving create/update/delete payload-shaping
      + response-parsing deterministically in CI (no secrets, no network)
- [x] `.github/workflows/ci.yml` — full suite on py3.9/3.11/3.12 + secret leak-scan on every
      push/PR; no secrets used (live verify runs on the operator's machine)
- [x] **Doc-drift guard** — every CLI command must appear in `docs/Capabilities.md` (now 93/93);
      build fails if a command ships undocumented
- [x] README CI badge (real Actions status)
- [ ] **HUMAN half (→ full G4 ✅):** create the free sandboxes (WordPress docker · Shopify dev ·
      Strapi docker · Notion · Contentful · Sanity), run `cms --verify` against each — only you
      can create the accounts (like G1's pilots)

## W5 · Experiment engine v1 (not gating)

- [ ] `experiment.py`: cohort A/B on titles/metas — pick 2N striking-distance pages, randomize N to treatment, ship via `control`
- [ ] Stats: two-proportion z-test on CTR (impressions/clicks) at +14/+28d; sequential stop rule
- [ ] `experiment start|status|conclude`; winner → playbook (with real stats), loser → W3 rollback
- [ ] Surfaces in `serve` + digest

## W6 · 5-minute demo mode (Gate G5) — ✅ built 2026-07-30

*Why: strangers quit at the first missing API key.*

- [x] `python -m seo_agent demo`: generates a synthetic workspace in code (17-page corpus with realistic flaws, 3 months GSC history, 4 measured changes — 2 wins, 1 modest, 1 honest loss, seeded brain) — zero keys, zero network; never clobbers a non-demo dir; its lesson store stays inside the folder
- [x] Instantly meaningful: `plan`, `learn` (+36 retitle, −18 refresh), `practices` (found→fixed→measured), `brain` (playbook + taste), dashboard all light up — verified live + regression-tested
- [x] README quickstart is now demo-first ("every claim you can verify yourself in 2 minutes")
- [ ] Timed test with someone who's never seen it: <5 min to the aha (the human half of G5)

## W7 · Cross-site learning → opt-in (Gate G6) — ✅ done 2026-07-30

*Why: aggregating across clients without asking is the first angry issue.*

- [x] `learning.share_cross_site` config — OFF until consented (`SEO_SHARE_LESSONS` env override); reading the store always allowed (operator's own machine)
- [x] Wizard asks in plain words ("only 'change type × lift' aggregates, domain hashed — no URLs/content/domains [y/N]")
- [x] `learn.update_global` no-ops without consent; `learn` output + journey Stage D show share status
- [x] Disclosure in LEARNINGS #18
- [x] Test: no global write without consent (file never created)

## W9 · Hand-held first run + guided dashboard (Gate G9)

*Why: install must hold your hand the way Hermes/Claude Code do — CLI useful, but a web
page opens, guides you, and shows everything: done work, learned best practices with real
examples, and every document to review. Strategy note (2026-07-30): keep working in the
trellus workspace first; the big standalone-install/workspace test comes after the loops
are proven.*

- [x] `start` command — one hand-held entry: setup status → guided dashboard, auto-opens the browser (helpful message in an empty folder)
- [x] Dashboard **Getting-started panel** — wizard steps ✅/▶/○, readiness score, the exact next command
- [x] Dashboard **Best-practices panel** — practices learned & applied HERE with live numbers (found → fixed → measured); `practices` CLI + MCP tool. Live on trellus: 400 lack answer-first, 43 stale titles, 23 encoded rules
- [x] Dashboard **Documents-to-review panel** — reports/drafts/change files viewable in-browser (`/doc`, whitelisted + traversal-guarded) + last-delivery/feedback status
- [x] `serve` auto-opens the browser (`--no-open` to skip)
- [ ] Polish during pilots: every rough edge P1–P3 hit goes here (this is the G9 burn-down)
- [ ] First-time-user test (part of G5's <5-min run): they never need the docs to know what to do next

## W10 · Depth hardening (from the external critique — docs/CRITIQUE-TRIAGE.md)

*An external audit (GLM, 2026-07-30) judged us "70% of a standalone agency — breadth
over depth." The correct fast items were built same-day (weighted GEO, indexability
matrix, 24k evidence + forecast, schema expansion, intent briefs, voice profile,
speed sampling/history — see triage doc). These are the remaining accepted items,
ordered by role impact. Non-gating, but each closes a named professional gap.*

- [ ] **Migration monitor** — `migrate baseline` / `migrate check`: pre/post URL inventory diff, redirect mapping validation, indexation + traffic alerting (highest-risk SEO events)
- [ ] **Post-apply verification** (→ merge into W3): after `apply`, re-fetch the page and confirm the change actually landed (title/meta/schema present) before the ledger logs it
- [ ] **Real AI-Overview citation tracking** — DataForSEO SERP AIO item extraction per tracked keyword (beyond synthetic prompt testing); correlate citations with citability signals
- [ ] **Entity coverage gaps** — topic → expected entity set (from SERP/Wikidata) vs entities the corpus actually mentions; feeds briefs
- [ ] **Refresh-why depth** — decaying page → diagnose cause (SERP intent shift, staleness, lost links, cannibalization) → specific update list, not just "refresh it"
- [ ] **Editorial calendar** — planned/in-production/review/published pipeline over the content queue, visible in `serve`
- [ ] **Multi-format briefs** — landing page, product page, comparison table templates alongside articles
- [ ] **API quota + cost tracker** — per-provider call counts, spend, backoff; surface in `serve` (LEARNINGS #13 generalized)
- [ ] **Competitor reverse-engineering** — sample competitor pages: structure, schema types, word depth, E-E-A-T signals vs ours
- [ ] **Gate v2: quality scoring** — readability + topical-completeness vs top SERP results (beyond pass/fail safety)
- [ ] **Portfolio depth** — cross-site prioritization + roll-up report in `projects`
- [ ] **Issue-tracker handoff** — export dispatched plan items to GitHub Issues/Jira/Linear
- [ ] **hreflang + pagination/parameter audits** — return-tag reciprocity, x-default, canonical-on-paginated, facet bloat

## W8 · Launch execution (Gate G7, G8)

- [ ] Case study from the 3 pilots (real ledger screenshots, honest wins AND flat results)
- [x] README claims audit — cut superlatives ("McKinsey-caliber" → specified expert personas), beta status line + verify-it-yourself demo block (G8; re-check at launch)
- [ ] Show HN draft: "local-first SEO agent that measures its own changes against a holdout" — lead with the ledger
- [ ] MCP registries (Smithery, PulseMCP, mcp.so) + awesome-claude-code lists
- [ ] r/ClaudeAI post · Indie Hackers build-log · 10 direct boutique-agency conversations
- [ ] Tip accounts live (FUNDING.yml uncommented) before the traffic arrives

---

## 🤖 The agent roster — who does what, and how to invoke them

Two kinds of agents: **operators** (the product running as a local Hermes-like agent, one
per pilot site — scheduled, not chatted with) and **builders** (Claude Code sessions in
`/Users/user/SEO`, one mission each). Every builder ends its mission by checking its boxes
in this file and running the suite.

### Operators (scheduled — the product itself)
| Agent | What it does | Invoke |
|---|---|---|
| Pilot Operator ×3 | Daily: snapshot GSC → autopilot cycle (audit→plan→execute→report) → queue for your review; learning + brain run automatically inside the cycle | the cron lines in W1 (or manually: `python -m seo_agent autopilot --daily`) |
| Reviewer (you) | 5 min/day per site: `serve` dashboard or `review` → approve/changes; replies teach the brain | `python -m seo_agent serve` → http://127.0.0.1:8787 |

### Builders (Claude Code missions — run from `/Users/user/SEO`)
| Agent | Mission | Invoke with |
|---|---|---|
| **Attribution Engineer** | W2, all boxes | `claude "Read docs/LAUNCH-PLAN.md workstream W2 and implement every unchecked box: diff-in-diff + min-n + CIs + confound flags in ledger.py/learn.py/brain.py, with the tests specified. Check the boxes, run the suite, commit."` |
| **Rollback Engineer** | W3 | `claude "Read docs/LAUNCH-PLAN.md W3 and implement auto-rollback end to end (before-state capture, rollback command, autopilot proposal wiring, tests). Check boxes, run suite, commit."` |
| **Connector Verifier** | W4 | `claude "Read docs/LAUNCH-PLAN.md W4: build cms --verify, run it against the sandbox accounts I've configured, record fixtures, add GitHub Actions CI. Check boxes, commit."` |
| **Experiment Engineer** | W5 | `claude "Read docs/LAUNCH-PLAN.md W5 and build experiment.py exactly as specified, with stats tests. Check boxes, run suite, commit."` |
| **DX Engineer** | W6 | `claude "Read docs/LAUNCH-PLAN.md W6 and build demo mode: bundled synthetic data + demo command + README quickstart. Time-target: aha in under 5 minutes. Check boxes, commit."` |
| **Privacy Engineer** | W7 | `claude "Read docs/LAUNCH-PLAN.md W7 and make cross-site learning opt-in with disclosure, exactly as specified, with the consent test. Check boxes, commit."` |
| **Launch Marshal** | W8 + weekly gate review | `claude "Read docs/LAUNCH-PLAN.md. Report gate status G1–G8 with evidence, update statuses, draft the next launch asset (case study / Show HN / registry listing), and tell me the single biggest blocker."` |

**Order of invocation (the coming days):**
- **Day 1:** stand up P2 + P3 (W1) · invoke **Privacy Engineer** (W7, small) then **DX Engineer** (W6)
- **Day 2–3:** **Attribution Engineer** (W2) — everything downstream depends on trustworthy numbers
- **Day 4:** **Rollback Engineer** (W3)
- **Day 5–7:** **Connector Verifier** (W4 — create sandbox accounts as you go) · pilots keep cycling daily
- **Week 2:** **Experiment Engineer** (W5) · **Launch Marshal** weekly from here
- **Day 30:** Launch Marshal compiles the case study → soft launch (G1–G6 must be ✅)
- **Day 90:** full case study update + the bigger push

_Rule for every builder agent: LEARNINGS.md #17–22 are standing constraints — never bypass
`personas.system(role, cfg)`, never skip the learning cycle, never stage secrets._
