# 🚀 Launch Plan — the living dashboard

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
| G2 | Attribution shows min-n + confidence intervals + confound flags (W2) | ⬜ 🔒 |
| G3 | Negative changes get rollback proposals automatically (W3) | ⬜ 🔒 |
| G4 | ≥4 CMS connectors verified against live sandbox accounts + CI green (W4) | ⬜ 🔒 |
| G5 | `demo` gives a stranger the full aha in <5 min, zero keys (W6) | ⬜ 🔒 |
| G6 | Cross-site learning is opt-in with clear disclosure (W7) | ⬜ 🔒 |
| G7 | One public case study with real ledger numbers (≥30d) | ⬜ 🔒 |
| G8 | README claims audited — no superlative we can't screenshot | ⬜ |
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
- [ ] P1: Webflow token in, autonomy=approve, cron live, first 5 changes shipped
- [ ] P2: chosen + onboarded + cron live
- [ ] P3: chosen (different CMS) + onboarded + cron live
- [ ] All: GSC snapshot cadence confirmed (attribution needs it — LEARNINGS #19)
- [ ] Day 30: pull `ledger` + `learn` from all three → case-study draft (G7)

## W2 · Attribution you can defend (Gate G2)

*Why: the brain must not learn noise. Today's lift = change − holdout-median; harden it.*

- [ ] `ledger.follow_up`: capture holdout **before→after trend** per horizon (diff-in-diff, not level-diff)
- [ ] Minimum evidence: no playbook/lesson distilled below n≥3; UI shows "n<3 — collecting"
- [ ] Confidence: 95% CI on mean lift (t-interval; Wilson for win-rate) → stored + rendered everywhere lifts show
- [ ] Confound flag: change within ±5 days of a Google update (`algo`/`radar` timeline) → `confounded: true`, excluded from playbooks
- [ ] Seasonality guard: compare same-weekday windows (7d multiples already do this — assert + test)
- [ ] Tests: synthetic seasonal + confounded scenarios prove false playbooks are NOT created

## W3 · Auto-rollback (Gate G3)

*Why: an autonomous bot is only trustable if it can undo itself.*

- [ ] `ledger.record` captures a **before-state** snapshot (title/meta/content-hash) at change time
- [ ] `rollback <change_id>` command → inverse `site_control` op, autonomy-gated, logged as `rollback:<type>`
- [ ] Autopilot report phase: change measured **negative at +28d (CI excludes 0)** → auto-queue a rollback proposal (approve mode) / execute capped in auto mode
- [ ] Rolled-back types feed `brain` avoid-lessons automatically
- [ ] Test: synthetic negative change → rollback proposal appears in the queue

## W4 · Connectors proven live + CI (Gate G4)

*Why: "smoke-tested offline" is not a launch claim.*

- [ ] `cms --verify`: create draft "connector-verify" → update → delete → report pass/fail per configured CMS
- [ ] Sandboxes (all free): WordPress (docker) · Shopify dev store · Strapi (docker) · Notion · Contentful · Sanity — verify + record HTTP fixtures to `tests/fixtures/`
- [ ] Note per-CMS constraints honestly in `cms` output (e.g. Wix update is id-only)
- [ ] `.github/workflows/ci.yml`: unit tests + fixture replay on every push (no secrets in CI)
- [ ] README badge flips to real CI status

## W5 · Experiment engine v1 (not gating)

- [ ] `experiment.py`: cohort A/B on titles/metas — pick 2N striking-distance pages, randomize N to treatment, ship via `control`
- [ ] Stats: two-proportion z-test on CTR (impressions/clicks) at +14/+28d; sequential stop rule
- [ ] `experiment start|status|conclude`; winner → playbook (with real stats), loser → W3 rollback
- [ ] Surfaces in `serve` + digest

## W6 · 5-minute demo mode (Gate G5)

*Why: strangers quit at the first missing API key.*

- [ ] `python -m seo_agent demo`: scaffolds a demo workspace from bundled synthetic data (corpus + 3 months GSC history + a ledger with measured changes) — zero keys, zero network
- [ ] Instantly meaningful: `audit`, `plan`, `learn`, `brain`, `serve` all show real-looking output
- [ ] README quickstart becomes: `pip install … && python -m seo_agent demo` → "now point it at your real site"
- [ ] Timed test with someone who's never seen it: <5 min to the aha

## W7 · Cross-site learning → opt-in (Gate G6)

*Why: aggregating across clients without asking is the first angry issue.*

- [ ] `learning.share_cross_site` config (default: unset = OFF until asked)
- [ ] Wizard + onboard ask explicitly: "Share anonymized change-type stats across your workspaces? (only type × horizon aggregates, domain hashed) [y/N]"
- [ ] `learn.update_global` no-ops unless opted in; `learn` output shows share status
- [ ] Journey Stage D shows the setting; README + docs disclosure section
- [ ] Test: no global write without consent

## W8 · Launch execution (Gate G7, G8)

- [ ] Case study from the 3 pilots (real ledger screenshots, honest wins AND flat results)
- [ ] README claims audit — cut superlatives, show receipts (G8)
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
