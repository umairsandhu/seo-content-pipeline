# ROADMAP — the future-savvy edition (2026 → 2027)

*Where search is going, what the competition charges for, and what we build next.
Grounded in the competitive scan of 2026-08 (Screaming Frog/Sitebulb/ContentKing ·
Surfer/Clearscope/MarketMuse · Profound/Peec/Otterly · Ahrefs/Semrush) and the external
depth audit ([CRITIQUE-TRIAGE](CRITIQUE-TRIAGE.md)). Launch execution lives in
[LAUNCH-PLAN](LAUNCH-PLAN.md); this doc is direction.*

## Where we stand (2026-08)

**Shipped and differentiated** — the closed loop no competitor has end-to-end:
audit → plan → expert crew writes → ships into 13 CMSs behind approval → holdout-measured
at +7/28/90d → self-learning brain (taste + playbooks + cross-site, opt-in) → guided local
dashboard. 80+ commands, 60 MCP tools, 74 tests, zero hosting.

**Competitive features we adopted (2026-08-08):** ContentKing-style **`sitediff`**
(crawl-to-crawl change tracking: noindex regressions, schema drops, content shrink → the
anomaly radar; daily cron = 24/7 monitoring, locally) · Sitebulb-style **why-it-matters +
how-to-fix hints** on every audit category · Profound-style **AI-referral analytics**
(`ga4` now splits out chatgpt/perplexity/gemini/copilot sessions — citations → visits) ·
Surfer-style term-gap scoring (already had it: `score`; now with a no-key corpus-relative
fallback) · **`diagnose`** (the one-command "why is traffic down?" differential no suite
ships) · **`agent`** (always-on daemon — the OpenClaw shape, scoped to SEO).

**Honest competitive position (revised after the devil's-advocate round):** we lead on
the **closed loop** (ship → measure vs holdout → learn → adapt: nobody has it end-to-end),
**AI-visibility from owned data** (aivis + AI referrals + AI-crawler logs), **local-first
monitoring** (sitediff + agent: logs and data never leave the machine — a moat no cloud
tool can copy), and **agent-native distribution** (63 MCP tools). We are honestly behind
on: raw crawl depth vs Screaming Frog (300+ checks, custom extraction), visualization vs
Sitebulb, live-editor UX vs Surfer/Clearscope, topic modeling vs MarketMuse, and we will
never have Ahrefs/Semrush's proprietary indexes — we wrap APIs for that data. Strategy:
lean into the loop, don't chase parity.

## Horizon 1 — Launch quality (now → day 30) · the LAUNCH-PLAN gates

Attribution you can defend (W2) · auto-rollback + post-apply verify (W3) · connectors
proven live + CI (W4) · pilots → the measured case study (W1/G7). *Nothing below matters
until these hold.*

## Horizon 2 — Professional depth (v1.x, next quarter) · from W10 + the scan

1. **Migration monitor** — pre/post inventory diff, redirect-map validation, traffic
   alerting. `sitediff` is the foundation; migrations are its highest-stakes use.
2. **Experiment engine** (W5) — cohort A/B on titles/metas with real stats; winners →
   playbooks, losers → rollback. Turns the ledger from observational to experimental.
3. **Real AI-Overview / AI-mode SERP tracking** — DataForSEO AIO item extraction per
   tracked keyword; correlate citations with citability signals (what actually earns them).
4. **Engine expansion for `aivis`** — Copilot, Grok, Reddit-AI, You.com (Peec tracks 8;
   our agent-mode makes engines nearly free to add).
5. **Entity coverage gaps** — topic → expected entities (SERP/Wikidata) vs what the corpus
   mentions; feeds briefs. The GEO gap nobody's tooling closes well yet.
5b. **Narrative monitoring & defense** — recurring themes (esp. negative) across `aivis`
   outputs → alert → counter-evidence page brief (real data) → refresh cadence (AI systems
   amplify sparse data; counter-citations displace it but decay without refreshing —
   LEARNINGS #27). Pairs with `zeroclick` branded-demand tracking.
6. **Refresh-why + editorial calendar** — decay diagnosis (intent shift vs staleness vs
   lost links) and a content pipeline view in `serve`.
7. **Agent phase 2: chat-first control** — reply "approve 3" / "status" / "diagnose" to the
   `agent` daemon from Slack/WhatsApp/email; the OpenClaw interaction model, SEO-only.
8. **Portfolio / agency view** *(promoted from H3 — agencies are the highest-LTV early
   adopters)* — cross-site roll-up in `projects`: readiness, wins, learnings, resource
   allocation across 5–50 workspaces.
9. **Brief → draft → score gate** — wire `score` into `crew` as a stage: drafts must clear
   term-coverage before the safety gate (the Surfer-loop, closed).
10. **Quota + cost tracker** — per-provider spend/backoff surfaced in the dashboard.
11. **Competitor reverse-engineering** — structure/schema/depth analysis of who outranks
    you, not just what they publish.
12. **Real-time MCP content editor** — live `score` feedback while writing, via the MCP
    server any editor can attach to.
13. *(parity, deprioritized)* visual crawl map · broken outbound links · spell-sweep —
    nice, but they differentiate nothing; uniqueness items above come first.

## Horizon 3 — Where search is actually going (2027 bets)

- **Agent analytics as a first-class channel.** Assistants don't just cite — they visit,
  compare, and transact. We already split AI referrals (`ga4`) and AI-crawler hits
  (`logs`); next: session-level agent behavior (which pages agents read before humans
  convert) and **agent-readable commerce** (Product schema + feeds tuned for shopping
  agents). Profound raised $96M at $1B to chase this — our local-first version rides on
  data the operator already owns.
- **GSC "Generative AI performance" API** — the moment Google ships it, wire it
  (registry entry already stubbed). First-party AI-impression data resets the whole
  GEO-tools market; being API-ready day one is a free win.
- **llms.txt + content licensing signals** — pay-per-crawl (Cloudflare), RSL, and
  AI-crawler licensing are becoming an operator decision. We generate llms.txt today;
  next: a `licensing` advisor (which bots to allow/block/charge, with traffic evidence
  from `logs` + `ga4` AI referrals).
- **Local-LLM mode** — headless drafting/sentiment via Ollama for operators whose clients
  forbid cloud LLMs. The stdlib-first design makes this a provider entry, not a rewrite.
- **The learning network** — opt-in cross-site store, one machine today. The 2027 version:
  agencies pool anonymized change-type outcomes across their own fleet ("retitles win 78%
  on e-commerce, 41% on SaaS") — the proprietary dataset no SaaS can copy, because it
  lives on operators' machines.
- **MCP-native distribution** — registries, the Claude skill marketplace, and
  agent-to-agent invocation (another agent hires ours for the SEO subtask). 60 tools is
  the moat; keep them boringly reliable.
- **Multimodal search surfaces** — video objects, image SEO depth, and voice-answer
  extractability as AI answers go multimodal.

## The v2 re-architecture (post-launch)

The full rebuild retrospective — the first architectural decision we'd change (one
capability registry, every surface generated), the evidence, the honest "couldn't have
known vs didn't want to know" split, and the 3-phase strangler migration — lives in
**[ARCHITECTURE-V2](ARCHITECTURE-V2.md)**. Execute after launch; the drift punch-list in
its appendix is same-day-fixable now.

## Operating principles (unchanged, load-bearing)

Local-first, no hosting, ever · every feature degrades without creds · human gate between
the tool and the live site · measure everything against a holdout · encode every lesson
(LEARNINGS #1–24) · "shipped" means role-deep (#24), and every capability names the
professional whose bar it must clear.
