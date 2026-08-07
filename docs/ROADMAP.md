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
Surfer-style term-gap scoring (already had it: `score`; the scan confirmed parity).

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
6. **Refresh-why + editorial calendar** — decay diagnosis (intent shift vs staleness vs
   lost links) and a content pipeline view in `serve`.
7. **Quota + cost tracker** — per-provider spend/backoff surfaced in the dashboard.
8. **Competitor reverse-engineering** — structure/schema/depth analysis of who outranks
   you, not just what they publish.
9. **Sitebulb-style visual crawl map** — click-depth/link-graph SVG in `serve`.
10. **Broken outbound links + spell-sweep** — the last Screaming Frog parity items.

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

## Operating principles (unchanged, load-bearing)

Local-first, no hosting, ever · every feature degrades without creds · human gate between
the tool and the live site · measure everything against a holdout · encode every lesson
(LEARNINGS #1–24) · "shipped" means role-deep (#24), and every capability names the
professional whose bar it must clear.
