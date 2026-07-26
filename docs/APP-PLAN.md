# Distribution & Runtimes — local-first, no hosting

**Design decision: nothing is hosted.** The tool runs entirely on the user's own machine (or
their own CI/server). There is no SaaS, no central server, no vendor holding your Google
tokens. This keeps it private, compliant, and free to operate — and it's already true today.

## Three ways to run it — one engine
| Runtime | How | Best for |
|---|---|---|
| **Claude Code skill** | Install the skill; ask Claude to onboard/audit/plan/ship. Claude drives it and writes the content itself — no LLM key needed. | Anyone with Claude Code; non-technical operators |
| **Standalone CLI** | `pip install` → `python -m seo_agent <cmd>`; `serve` for the local dashboard; cron `autopilot --daily` | Developers, agencies with a machine/CI that stays on |
| **MCP server** | `python -m seo_agent mcp` → 52 tools in any MCP client / agent runtime | Embedding in another agent workflow |

All three share the same file-based workspace (`config.json`, `corpus.json`, `history/`,
`seo.db`, `state/`), the autonomy gate, the review queue, and the causal ledger. Switching
runtimes is just a different front door to the same local files.

## Running it on a cadence (locally)
The autopilot loop is designed to run daily/weekly — on **your** machine, not ours:
- **Cron / Task Scheduler:** `0 7 * * * cd ~/sites/acme && python -m seo_agent autopilot --daily --email`
- **CI (GitHub Actions / GitLab CI):** a scheduled workflow that runs `autopilot` and commits any PRs.
- **Claude Code:** the `/schedule` skill (scheduled cloud/local agent) can fire the loop.
- **Always-on box:** a cheap VPS *you* control (Hetzner/DO ~$5/mo) if you want 24/7 cadence
  without leaving your laptop on. Still your machine, not a vendor's.

The Planner sets each item's due-date and cadence, so a single daily `autopilot` run paces the
whole backlog; the local `serve` dashboard shows it and takes your approvals.

## Why local-only (the deliberate trade-off)
- **Privacy & compliance:** client GSC/GA4 tokens and site data never leave the operator's
  machine — no central warehouse, no vendor breach surface, no data-processing agreements.
- **Zero infra cost & ops:** nothing to run, scale, or secure on our side.
- **Distribution:** the open-source + Claude-skill + MCP channels are CAC-free; the license is
  a local key, not an account.
- **The trade-off we accept:** the daily loop only runs when the operator's machine/CI is on.
  For agencies that's a always-on box or CI; for individuals it's their laptop + cron or just
  running `plan`/`autopilot` on demand. That's the intended model — convenience over a hosted
  scheduler isn't worth becoming a data custodian.

## Multi-site / agency use — still local
`projects` manages many client site-folders from one machine; each stays a self-contained,
fork-safe workspace (one dir = one site). An agency runs the loop per client via cron/CI on its
own box and delivers white-label reports (Pro+ license). No multi-tenant server required — just
many local workspaces.

## Packaging
- **PyPI / pipx** — `pip install seo-content-pipeline` (core: numpy + scikit-learn; everything
  else stdlib/optional).
- **Claude skill / plugin** — install into Claude Code; the agent runs it.
- **MCP** — register `python -m seo_agent mcp` in any MCP client.
- **License key** (Pro/Agency/Enterprise) — sets `edition` locally to unlock white-label +
  commercial/reseller use + support. See [COMMERCIAL](../COMMERCIAL.md).

_No hosting is planned. If a hosted option is ever offered, it would be an optional convenience
for non-technical buyers — never a requirement, and never where the data must live._
