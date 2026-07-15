# seo-content-pipeline — Wiki

A **site-agnostic, end-to-end SEO operating system**. File-based, no DB, no server; every API
optional; drivable from the CLI, an MCP client, or an AI agent. This wiki is the human-facing
knowledge base; the runtime specs live at the repo root (`SKILL.md`, `PLAYBOOK.md`, etc.).

## Start here
- **[Getting Started](Getting-Started.md)** — install, `init`, and your first run in 5 minutes.
- **[The 0→100 Playbook](../PLAYBOOK.md)** — the phased path from a cold site to a compounding engine.
- **[Command Reference](Commands.md)** — every command, grouped, with what it needs and returns.

## Understand it
- **[Architecture](Architecture.md)** — the five layers, design principles, module map, how it degrades.
- **[Integrations](Integrations.md)** — the API registry (must / recommended / optional), alternatives, and how to add any API in one entry.
- **[Site Doctor](Site-Doctor.md)** — every technical + on-page + E-E-A-T + accessibility check it runs.

## Grow with it
- **[AI Search (AEO / GEO)](AI-Search.md)** — how to get cited by ChatGPT, Perplexity, and Google AI Overviews, and how the tool supports it.
- **[SEO Knowledge Base](SEO-Knowledge-Base.md)** — a glossary and the 2026 best-practice map behind the tool's decisions.
- **[Build Loop](../BUILDLOOP.md)** — how the *tool itself* stays best-in-class as Google and AI search evolve.

## Run it your way
- **[FAQ / Troubleshooting](FAQ.md)** — common questions, gotchas, and error fixes.
- **[Contributing / Extending](Contributing.md)** — add a check, an API, or a CMS connector.

## One-line mental model
> `init` a workspace → wire GSC + DataForSEO → `onboard` for a baseline → run **`plan`** any
> time for the ranked next actions → apply as PRs → `run` on a schedule to compound.

Everything degrades: with **zero credentials** you still get the full technical Site Doctor,
content briefs, structured-data generation, and — when an agent drives it — written content.
