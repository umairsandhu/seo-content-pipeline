# seo-content-pipeline

**A site-agnostic, end-to-end SEO operating system.** Point it at any domain and it takes
you from 0 to 100 — fork-safe onboarding, a technical Site Doctor, rank/CTR/backlink/trend
tracking, AI-Overview-aware opportunity ranking, log-file + AI-crawler analysis, content
drafting, multi-CMS publishing, and a single prioritized **action plan** of what to do next.

![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-%E2%89%A53.9-blue)
![deps](https://img.shields.io/badge/core%20deps-numpy%20%2B%20scikit--learn-orange)
![storage](https://img.shields.io/badge/storage-file--based%20(no%20DB)-lightgrey)
![mcp](https://img.shields.io/badge/MCP-ready%20(30%20tools)-purple)

No database. No server. Stdlib + `numpy`/`scikit-learn` at the core; every API is optional
and the whole thing **degrades gracefully** — the technical audit and content work run with
zero credentials. Drive it from the CLI, from any MCP client, or hand it to an AI agent that
writes the content itself.

```bash
pip install -e .                 # or: pipx install seo-content-pipeline
seo-content-pipeline init --site https://www.example.com   # bootstrap a workspace (any dir)
seo-content-pipeline onboard     # fork-safety → Site Doctor → baseline → BASELINE.md
seo-content-pipeline plan        # the co-pilot: ranked "what to do next"
```

> **One directory = one site.** `init` scaffolds a clean, site-agnostic workspace
> (`config.json` + `.env` + a hardened `.gitignore`) so anyone can start from scratch in a
> new terminal or session. It refuses to run inside the tool's own install directory.

**Or install as a Claude skill** (Claude then runs it and writes the content itself, no key):
```
/plugin marketplace add umairsandhu/seo-content-pipeline
/plugin install seo-content-pipeline@seo-content-pipeline
```
Three ways to run it — Python CLI, Claude plugin, or MCP server — see [PUBLISHING.md](PUBLISHING.md).

---

## Why this exists

Best-in-class SEO in 2026 is (a) technical hygiene, (b) content that earns and defends
rankings, and (c) staying visible as search shifts to AI answers. Most tools do slices of
this behind a subscription. This one does the whole loop, file-based and self-hostable, and
turns every signal into **one prioritized action list** — then keeps itself current with a
built-in build loop. It's designed to be driven by an AI agent end-to-end, but works
perfectly as a plain CLI.

## What you get (the command map)

| Group | Commands | Does |
|---|---|---|
| **Onboard** | `init` · `safety` · `integrations` · `onboard` | Bootstrap a workspace, guarantee no secret leaks, see the API matrix, build a baseline |
| **Plan** | **`plan`** | Fuse every signal into one ranked, deduped action list (`plan.md`) — the co-pilot |
| **Site Doctor** | `audit` · `geo` · `sitemap` · `speed` · `logs` · `schema` · `eeat` · `authority` · `report` · `llmstxt` | Technical + on-page + Core Web Vitals + log-file + E-E-A-T + topical-authority + **GEO/AEO readiness**; `report` = shareable HTML dashboard |
| **Observe** | `ingest` · `gsc` · `rank` · `trends` · `backlinks` · `toxicity` | Crawl the site (parallel); track rank/CTR/SERP-features/backlinks/emerging keywords over time |
| **Decide** | `research` · `discover` · `gap` · `aio` · `consolidate` · `inlinks` · `autolink` · `decay` · `algo` · `radar` | Find gaps, AI-Overview-adjust opportunities, plan consolidations + internal-link fixes, detect decay, attribute algo updates |
| **Produce** | `analyze` · `brief` · `draft` · `score` · `retitle` | SERP-grounded briefs, drafts (agent-written), comprehensiveness scoring, title/meta rewrites |
| **Publish** | `publish` · `mcp` | WordPress / Webflow / Ghost / git-PR connectors; a stdio MCP server (30 tools) |
| **Run** | `run [--monthly]` | Scheduled weekly/monthly digest → `digest.md` |

Full reference: **[docs/Commands.md](docs/Commands.md)**.

## The 0 → 100 path

`init` → wire GSC + DataForSEO (`integrations` shows what's missing) → `onboard` → fix the
Site Doctor's HIGH items → build content from `gap`/`discover` → track with `rank`/`gsc` →
refresh with `decay`/`aio` → stay AI-visible with `logs`/`llmstxt`. The full phased manual is
**[PLAYBOOK.md](PLAYBOOK.md)**; at any point, `plan` tells you the next best moves.

## How it works

Five layers, file-based, each degrading gracefully:

1. **Observe** — ingest the site (sitemap, auto-discovered from robots.txt), and track
   GSC/backlinks/rank/trends over time in `history/`.
2. **Decide** — cannibalization, gaps, striking-distance, content decay, algorithm-update
   attribution, AI-Overview-adjusted CTR.
3. **Produce** — SERP + People-Also-Ask-grounded briefs and drafts (**the agent writes them —
   no API key needed**; an optional headless model backs unattended runs).
4. **Publish** — one interface over WordPress/Webflow/Ghost/git-PR, plus an MCP server.
5. **Orchestrate** — scheduled `run` → digest, diffed against history and a **build loop**
   (`radar` watches Google's Search Status Dashboard).

Design + module map: **[docs/Architecture.md](docs/Architecture.md)**.

## Integrations

| Tier | Integration | Unlocks | Alternatives |
|---|---|---|---|
| must | **Google Search Console** | rank, CTR, decay, algo attribution | Bing Webmaster |
| must | **DataForSEO** | volume, SERP/PAA, backlinks, trends, competitor gap | Semrush · Ahrefs · SerpApi |
| recommended | PageSpeed / CrUX | Core Web Vitals | WebPageTest |
| recommended | Server logs | crawl budget + AI-crawler coverage | Cloudflare/Fastly export |
| recommended | JS rendering (Playwright) | accurate audit of SPA sites | DataForSEO on-page |
| optional | Anthropic / OpenAI | headless drafting (not needed with an agent) | agent-written (default) |
| optional | WordPress / Webflow / Ghost | publishing | git-PR file (default) |

`integrations` prints a live matrix of what's active, what's missing, and what each gap
costs. **Adding any new API is one entry** in `seo_agent/integrations.py`. Details:
**[docs/Integrations.md](docs/Integrations.md)**.

## Secrets & fork-safety

The repo is public, so `safety` (run first, and inside `init`) writes a committed
`.env.example`, hardens `.gitignore` to exclude every secret/working file, and **leak-scans
tracked files and the working tree** — `.gitignore` alone only protects untracked files. A
`--precommit` mode plugs into a git hook. Your keys can never leak from a fork.

## Documentation

- **[Getting Started](docs/Getting-Started.md)** — install → init → first run
- **[Command Reference](docs/Commands.md)** — every command, grouped
- **[Architecture](docs/Architecture.md)** — the five layers, design, module map
- **[Integrations](docs/Integrations.md)** — APIs, alternatives, adding your own
- **[Site Doctor](docs/Site-Doctor.md)** — every technical/on-page check
- **[AI Search (AEO/GEO)](docs/AI-Search.md)** — getting cited by ChatGPT/Perplexity/AI Overviews
- **[SEO Knowledge Base](docs/SEO-Knowledge-Base.md)** — glossary + 2026 best-practice map
- **[FAQ / Troubleshooting](docs/FAQ.md)** · **[Contributing / Extending](docs/Contributing.md)**
- Operating manuals: **[PLAYBOOK.md](PLAYBOOK.md)** (0→100) · **[BUILDLOOP.md](BUILDLOOP.md)**
  (staying current) · **[ONBOARDING.md](ONBOARDING.md)** (agent onboarding script)

## Contributing / extending

Add a Site-Doctor check, an API, or a CMS connector in one place each — see
[docs/Contributing.md](docs/Contributing.md). Everything is stdlib-first, deterministic, and
must degrade gracefully.

## License

MIT.
