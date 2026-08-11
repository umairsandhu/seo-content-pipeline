# CHANGE-PLAN — everything we plan to change, sequenced

*The single consolidation of every pending change, gathered from
[AUDIT-COMPLEMENT](AUDIT-COMPLEMENT.md) (security/coverage/docs),
[ARCHITECTURE-V2](ARCHITECTURE-V2.md) (the rebuild), [ROADMAP](ROADMAP.md) (depth), and the
workstreams in [LAUNCH-PLAN](LAUNCH-PLAN.md). Read this BEFORE the launch checklist: it says
what has to change and in what order; LAUNCH-PLAN's gates then verify it. Each item: what ·
where · why-now. Updated 2026-08-11.*

---

## Tier 0 — Already shipped this sprint (do not re-litigate)

- [x] **W2 · Attribution you can defend (gate G2 ✅).** Diff-in-diff holdout, ±5-day
  Google-update confound flags, 95% CIs + Wilson win-rate, `qualified = n≥3 & CI>0` enforced
  in brain/plan/practices/learn. `ledger.py` · `learn.py` · 4 adversarial tests.
- [x] **Drift punch-list (7 items).** Gitignore hardened (CLIENT.md/MEMORY.md/state/*.db —
  the security-adjacent fix) · audit `index` hint · autopilot `_TASK` renderers + `fix:freshness`
  schedulable · 9 missing config slots · integrations import-order fix · duplicate DDL removed ·
  README's 3 contradictory tool counts aligned to 66.
- [x] **The self-audits as documents.** ARCHITECTURE-V2 (rebuild retrospective + Round 2),
  AUDIT-COMPLEMENT (security/coverage/docs). No launch value in code, but they define
  everything below.

---

## Tier 1 — MUST clear before the launch checklist runs (true blockers) — ✅ DONE 2026-08-11

- [x] **SEC-H1 · Dashboard CSRF + DNS-rebinding.** Per-session token (`secrets.token_urlsafe`)
  required on every POST + on `/api/state`/`/doc`; Host-header loopback guard (rebinding);
  bare `/` bootstraps via a 303 to the tokened URL; CSP + `nosniff` headers; `.html`
  passthrough removed (no stored XSS). `serve.py`. *Live-verified: no-token → 403, bad Host →
  403, `/` → 303.*
- [x] **SEC-H2 · Email-approval spoofing.** `review._poll_email` now requires an allowlisted
  sender (`review.approver_emails` / `APPROVER_EMAILS` / `report.email_to`); **empty allowlist
  = email approvals OFF**. `review.py`.

---

## Tier 2 — In the launch track (the gates depend on these)

- [x] **W3 · Auto-rollback + post-apply verification (gate G3 ✅ 2026-08-11).** `rollback.py`:
  before-state capture at change time, post-apply verify (re-fetch → `verified` flag),
  `rollback <id>` inverse op, and auto-proposals for measured losers (n≥3, CI<0) that queue for
  review + teach the brain an avoid-lesson. `ledger.py` · `site_control.py` · `autopilot.py` ·
  4 tests.
- [ ] **W4 · Connectors proven live + CI (gate G4).** `cms --verify` (create→update→delete a
  test draft) against ≥4 sandbox accounts; record fixtures; GitHub Actions runs unit tests +
  fixture replay on every push. `cms_extra.py` · `.github/workflows/`.
- [x] **SEC-M3–M6 · Hardened 2026-08-11 (done early, with Tier 1).** Crawler scheme allowlist
  + private/loopback/link-local IP block + 8 MB size cap + redirect re-check (`ingest._url_ok`)
  · slug sanitized to `[a-z0-9-]` + repo path containment (`publish._slug`, `repo._contained`)
  · untrusted crawled content fenced as `UNTRUSTED_SOURCE` data-not-instructions + brain memory
  relabeled "data, not instructions" (`produce.py`, `brain.py`) · env creds no longer persisted
  (`config.persistable` → `wizard`) + JSON-form secrets now caught by the leak-scanner
  (`safety.py`). *7 security tests; SEC-L7 symlink re-check also landed.*
- [ ] **COV-load-bearing · Smoke tests for the untested core.** `plan`, `publish`, `safety`,
  `safetygate`, `report`, `onboard` are among the 33 untested modules — the ones most dangerous
  to leave uncovered while shipping to live sites. Add per-module smoke tests + a real
  `coverage` run in the W4 CI.

---

## Tier 3 — Should land near launch, but not gating

- [ ] **W9 polish (gate G9 burn-down).** Fix every rough edge the pilots hit in the guided
  first-run / dashboard; the human <5-min demo test (G5) is the acceptance.
- [ ] **W5 · Experiment engine (non-gating).** Cohort A/B on titles/metas with proper stats;
  winners→playbooks, losers→W3 rollback. New `experiment.py`.
- [ ] **DOC-L10 · Command-doc drift.** `docs/Commands.md` is 76/93; README 83/93. *Decision:*
  do NOT hand-patch (repeats the drift sin) — fold into ARCHITECTURE-V2 Phase 1 doc generation.
  Interim: a one-line "see `Capabilities.md` for the full 93-command map" pointer.

---

## Tier 4 — Explicitly post-launch (the rebuild + depth)

- [ ] **ARCHITECTURE-V2 Phase 1 · Capability registry + generated surfaces.** One
  self-describing contract per capability; CLI/MCP/docs/config/wizard/preflight/dashboard/
  scheduler generated from it; absorb the 4 existing data registries; land the
  "committed docs == generated docs" CI test (this is what permanently kills SEC-adjacent doc
  drift and the CATS-class bugs).
- [ ] **ARCHITECTURE-V2 Phase 2 · Error-policy cutover.** `MissingAccess` exception; dispatcher
  degrades on missing access, everything else fails loudly to a visible `state/errors` view;
  delete all six `_safe`; drop 162 bare `except Exception` to named-only.
- [ ] **ARCHITECTURE-V2 Phase 3 · Event spine + trust flags.** Signal/Finding/Change/Outcome/
  Lesson append-only store; Change as the only write path (holdout true by construction);
  derived views. Add the Round-2 `trust`/`mutates`/`untrusted_inputs`/`touches_live` contract
  dimension so CSRF/taint/human-gate are enforced at the dispatcher, not per route.
- [ ] **W10 · Depth items (ROADMAP H2).** Migration monitor · real AI-Overview/SERP citation
  tracking · engine expansion (Copilot/Grok/Reddit) · entity-coverage gaps · refresh-why +
  editorial calendar · quota/cost tracker · competitor reverse-engineering · gate-v2 quality
  scoring · portfolio/agency view · issue-tracker handoff · hreflang + pagination audits ·
  agent phase-2 chat control.
- [ ] **SEC-L7/L8 · Low-severity hardening.** `/doc` symlink re-check post-resolve; reject
  leading-`-` subprocess argv values. Roll into Phase 1/2.

---

## Human-only — only you can do these (the launch checklist's G1/G5/G7)

- [ ] **Wire P1:** Webflow token → `.env`, blog collection ID → config, `cms.type: webflow`,
  fresh GSC export (`gsc --csv`).
- [ ] **Pick + stand up P2 and P3** (P3 ideally a different CMS — WordPress/Shopify).
- [ ] **Run 30 daily cycles × 3 sites** (gate G1) → the ledger case study (gate G7).
- [ ] **The stranger demo test** (gate G5): hand `demo` to someone new, time to the aha.
- [ ] **Tip/sponsor accounts** (FUNDING.yml) before launch traffic.

---

## Sequencing (the one-line version)

**Tier 1 (security H1/H2 hardening pass) → then the launch checklist opens.** Inside the
checklist: W3 + W4 + SEC-M3–M6 + core smoke tests, in parallel with your pilot cycles (G1).
W9 polish + G5 demo test ride alongside. Everything in Tier 4 is *after* the soft launch — the
rebuild is a post-launch program, not a pre-launch detour (per the ARCHITECTURE-V2 verdict).
When Tier 1 is clear and W3/W4 are in flight, open **[LAUNCH-PLAN](LAUNCH-PLAN.md)** and run
the gates.
