# Plan — the autonomous agent loop + local dashboard

**Goal.** The skill hosts a **local web dashboard** that a crew of specialized agents
read and write, and a human oversees. Four agents run a **daily/weekly cadence the tool
itself schedules**: an **Audit** agent finds the situation and problems, a **Planner**
agent sets the dated way-ahead, an **Executing** agent ships the due work through
dedicated workflows, and an **Analyst/Reporting** agent measures and reports what
actually changed. Then it repeats.

This is a design + build plan. **~80% of the capability already exists as commands**
(`audit`, `plan`, `consult`, `crew`, `pr`, `control`, `review`, `ledger`, `explain`,
`run`, `anomaly`, `report`). What's new is a thin **coordination layer**: a shared state
model, a local server that renders it, and an orchestrator that runs the four roles on a
schedule.

---

## 1. Architecture — a blackboard, not a pipeline

The dashboard is a **shared blackboard**: every agent reads the current state, does its
job, and writes its output back. Humans watch and approve from the same surface. State
lives in the workspace (files + `seo.db`) — the agents and the web view are just
different readers of it.

```
                     ┌──────────────────────────────────────┐
                     │   Local dashboard  (http://localhost) │  ← humans watch + approve
                     │  Situation · Plan · Execution · Report│
                     └──────────────────────────────────────┘
                          ▲        ▲        ▲        ▲
        writes situation  │        │        │        │  writes report
             ┌────────────┘        │        │        └────────────┐
        ┌────────┐   plan   ┌────────┐  exec  ┌────────┐   ┌──────────────┐
        │ AUDIT  │ ───────▶ │PLANNER │ ─────▶ │EXECUTOR│──▶│ ANALYST /    │
        │ agent  │          │ agent  │        │ agent  │   │ REPORTER     │
        └────────┘          └────────┘        └────────┘   └──────────────┘
             ▲                                     │ human review gate │
             └───────────────  daily / weekly cadence  ◀───────────────┘
```

**Shared state (new `state/` + existing `seo.db`):**
| Artifact | Written by | Backed by |
|---|---|---|
| `state/situation.json` | Audit | `audit` + `anomaly` + `gsc` + `explain` |
| `state/plan.json` (dated items) | Planner | `plan` + `consult` + `consolidate` + `gap` + `competitors` |
| `state/executions.json` | Executor | `crew` / `pr` / `control` / `refresh` + `ledger` |
| `approvals.json` | Executor → human | existing autonomy/review queue |
| `state/reports/<date>.json` | Analyst | `ledger` (attribution) + `run` + `report` |

Nothing new to compute — the coordination layer **orchestrates existing commands** and
records their outputs to shared state.

---

## 2. The four agents (each a persona + a workflow over existing commands)

Each agent is a subagent driven by an expert persona we already ship (`personas.py`) and
a dedicated workflow of existing commands.

### Audit agent — "where are we, what's broken?"
- **Runs:** `ingest` (refresh crawl) → `audit` → `speed` → `anomaly` → `gsc`/`decay` →
  `explain` on any dropped money pages.
- **Persona:** Tech-SEO + Analyst.
- **Writes** `state/situation.json`: health score, ranked problems (with est. traffic
  impact), regressions since yesterday, and "what changed on the site/SERP."

### Planner agent — "what do we do, and when?"
- **Runs:** `plan` + `consult` (strategy) + `consolidate` + `gap` + `competitors`.
- **Persona:** Strategist (McKinsey/ex-Google).
- **Writes** `state/plan.json`: a backlog of **dated items** — each `{id, action, target,
  command, impact, effort, due_date, cadence, status}`. Crucially it **sets the cadence
  per item** (e.g. content refresh weekly, meta fixes now, competitor scan monthly) — this
  is the "recommended cadence our tool will plan."

### Executing agent — "ship what's due today"
- **Runs a daily loop:** load `plan.json` → select items whose `due_date ≤ today` and
  `status = ready` → execute each via its command (`crew article`, `pr`, `control`,
  `refresh`) → route through the **safety gate + autonomy/review** → on approval,
  `apply --approved` → mark item done + record to the **ledger** with the commit/URL.
- **Persona:** Tech-SEO + Writer (via `crew`).
- **Writes** `state/executions.json`: what shipped today, what's queued for review, what's
  scheduled for future dates (with timelines), what's blocked.
- **Dedicated workflows:** a content workflow (`crew article` → review → publish), a
  fix workflow (`audit --fix` → `pr` → review → merge), a refresh workflow (`decay` →
  `refresh` → review → publish). Each is a small `Workflow` script.

### Analyst / Reporting agent — "what changed, and did it work?"
- **Runs:** `ledger` (holdout attribution of everything shipped) + `explain` on movers +
  `run` (digest) + `report --pdf`.
- **Persona:** Strategist + Analyst.
- **Writes** `state/reports/<date>.json` and **delivers** via `channels` (email / Slack /
  Mattermost / WhatsApp): *what we did on which dates, what moved, the holdout-adjusted
  lift, what's next.* Feeds proven wins back into the Planner's prioritization (already
  wired: `plan` reads `ledger.attribution`).

---

## 3. The cadence — a self-scheduling daily/weekly loop

The Planner assigns each item a `cadence` and `due_date`; a scheduler fires the loop:

- **Daily (light):** Audit (regressions + anomalies) → Executor (ship items due today,
  respecting review) → Analyst (yesterday's attribution + a 3-paragraph digest). Maps to
  `run --daily` + the executor loop.
- **Weekly (standard):** full Audit → Planner re-plans the backlog and dates → Executor
  clears the week's due items → Analyst weekly report. Maps to `run` (weekly).
- **Monthly (deep):** competitor sitemap-delta, backlink gap, algo re-attribution,
  strategy refresh (`consult`), executive one-pager. Maps to `run --monthly`.

The cadence is **data-driven, not fixed**: the Planner sets faster cadence for volatile /
high-impact areas and slower for stable ones, and the Analyst's attribution adjusts it
(what's working gets more cycles).

---

## 4. The local dashboard (new: `serve`)

A new `serve` command starts a local web server (stdlib `http.server`, zero deps) that
renders the shared state as a live HTML dashboard — the surface both agents' outputs and
humans converge on.

- **Panels:** Situation (health + problems), Plan (the dated backlog + calendar/timeline),
  Execution (shipped / in-review / scheduled, with dates), Review queue (approve /
  request-changes inline), Reports (attribution + trend charts), Ledger (change → lift).
- **Live:** re-reads state on an interval; agents write state, the page reflects it.
- **Human actions:** approve / request-changes buttons post to a local endpoint that
  writes to `approvals.json` (same queue the CLI uses) — so the human gate is right there.
- **Reuses** every `render_md` we already have; the server wraps them in the dashboard
  shell (same styling as the brochure/report).
- **Read-only share:** export a static snapshot (`report --pdf`, or a static HTML bundle)
  for stakeholders who shouldn't touch the controls.

*(Local-only — the `serve` dashboard runs on your machine; multi-site agencies run one per
client via `projects` + cron/CI. No hosted version. See [Distribution & Runtimes](APP-PLAN.md).)*

---

## 5. Orchestration — how the agents actually run

Two supported modes, same roles:

- **Inside Claude Code (recommended):** an `autopilot` orchestration (a `Workflow`
  script) spawns the four agents as subagents in sequence each cycle, each adopting its
  persona, each calling the existing commands/MCP tools, writing shared state. The human
  approves in the dashboard or the chat. Best reasoning quality.
- **Headless / cron (standalone):** the `schedule` skill (or system cron) runs
  `seo_agent autopilot --daily|--weekly`, which executes the four-role loop with the
  configured `llm.provider` for any writing, and delivers reports via channels. Runs
  unattended between human check-ins.

Both write to the same state and dashboard, so you can start unattended and drop into the
dashboard to steer.

---

## 6. What to build (delta over what exists)

| Piece | Status | Effort |
|---|---|---|
| Expert personas, all 4 roles' commands, review gate, ledger, channels | ✅ exists | — |
| **`state/` model** — situation/plan/executions/report JSON (`state.py`) | ✅ **built** | S |
| **Dated plan items** — `autopilot.plan_phase` assigns `due_date` + `cadence` per item, merges across cycles | ✅ **built** | S |
| **`serve`** — local web dashboard (stdlib http.server) with the panels + inline approve/changes + Run-cycle | ✅ **built** | M |
| **`autopilot [--daily/--weekly/--monthly]`** — the 4-role loop (Audit→Plan→Execute→Report), drip-capped, ledger-closed | ✅ **built** | M |
| Executor dispatch — maps each due item to its command/task through the safety + review gate | ✅ **built** | S–M |
| Scheduler hook (`jobs.py` / cron / `schedule` skill) to fire `autopilot` on cadence | 🟡 use cron/`/schedule` today | S |

**Built 2026-07-21.** `python -m seo_agent autopilot --daily` runs a cycle; `serve` opens the
dashboard at `http://127.0.0.1:8787`. Also exposed as MCP tools (`autopilot`). The loop advances
items `planned → dispatched → done` (closing when the change lands in the ledger), respects the
`max_per_cycle` drip cap, and persists status across cycles. Cadence is driven locally by
cron / CI / the `/schedule` skill (no hosted scheduler); remaining polish = richer executor
sub-workflows.

**Sequence:** state model → dated plan items → `serve` dashboard → executor workflows →
`autopilot` orchestrator → scheduler. Roughly a 2–3 phase build; every piece is additive
and reuses the engine.

---

## 7. Guardrails (unchanged, enforced in the loop)
- The **human review gate** sits between Executor and any live change — daily automation
  never removes it for structural/destructive work (autonomy modes still apply).
- The **safety gate** blocks thin/duplicate content before publish.
- Every automated change is **logged to the ledger** for auditability and attribution.
- The dashboard is **local by default**; sharing is an explicit read-only export.

_The agents are new coordination; the muscle is the engine we already built. This plan
turns the commands into a self-running, human-supervised daily operation with one glass
pane._
