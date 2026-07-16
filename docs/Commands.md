# Command Reference

Run as `seo-content-pipeline <cmd>` (installed) or `python -m seo_agent <cmd>`. Global flag:
`--config <path>` (default `config.json`). Every command degrades gracefully when its APIs
aren't configured. Legend — **needs**: GSC · DFS (DataForSEO) · PSI (PageSpeed key) · logs ·
none.

## Onboard & setup
| Command | Needs | Does |
|---|---|---|
| `init [--site URL]` | none | Bootstrap a site-agnostic workspace: `config.json` + `.env` + hardened `.gitignore` + fork-safety. Refuses to run in the install dir. |
| `safety [--precommit]` | none | Write `.env.example`, harden `.gitignore`, leak-scan tracked files + working tree. `--precommit` = git-hook mode (exit 1 on secrets). |
| `integrations` | none | Capability matrix: which APIs are active/missing, what each unlocks, alternatives. |
| `onboard [--keywords-file f]` | none+ | Full first run (fork-safety → Site Doctor → speed → gaps) → `BASELINE.md`. |

## Plan (the co-pilot)
| Command | Needs | Does |
|---|---|---|
| **`plan`** | none+ | Fuse every signal (Site Doctor, GSC, decay, gaps, cannibalization, orphans, E-E-A-T, clusters, AI-crawler policy) into one ranked, deduped action list → `plan.md`. |

## Site Doctor (technical + on-page)
| Command | Needs | Does |
|---|---|---|
| `ingest` | none | Crawl the site (sitemap → `corpus.json`); auto-discovers the sitemap from robots.txt; JS-renders when `render.enabled`. |
| `audit` | none | Full Site Doctor → `audit.md` (see [Site-Doctor.md](Site-Doctor.md)). |
| `sitemap` | none | Sitemap doctor only (limits, lastmod, coverage, redirects). |
| `speed` | PSI | Core Web Vitals — Lighthouse lab + CrUX field + accessibility score. |
| `logs <access.log[.gz]> [--verify]` | logs | Log-file analysis: Google + AI crawlers, crawl waste, AI-crawler coverage. `--verify` = reverse-DNS Googlebot. |
| `schema [<url>]` | none | Generate JSON-LD for a URL (BlogPosting + Breadcrumb + Organization), or list pages missing structured data. |
| `eeat` | none | E-E-A-T signals: author, dates, citations, trust pages, HTTPS. |
| `authority` | none | Topical-authority clusters: pillar presence + internal-link density. |
| `geo` | none | GEO/AEO readiness score — extractability, schema, AI-crawler access, E-E-A-T per page. |
| `report` | none+ | Self-contained HTML dashboard (`report.html`) fusing audit + plan + GEO + E-E-A-T + GSC. |
| `llmstxt` | none | Generate an `llms.txt` from the corpus. |

## Observe (track over time)
| Command | Needs | Does |
|---|---|---|
| `gsc` | GSC | Striking-distance + low-CTR opportunities; snapshots to `history/`. |
| `rank` | DFS | Track position + SERP features (AIO/snippet/PAA/video/shopping/…) over time + movement. |
| `trends <seed…>` | DFS | Emerging / rising keywords (new-since-last-run + rising interest). |
| `backlinks` | DFS | Backlink profile, or competitor link-gap (outreach targets). |
| `toxicity` | DFS | Conservative toxic-link review — **disavow is rarely needed in 2026** (see note in output). |

## Decide
| Command | Needs | Does |
|---|---|---|
| `research <kw…>` | DFS | Dedup verdict (NOVEL/RELATED/EXTEND) + internal-link targets per keyword. |
| `discover <seed>` | DFS | DataForSEO keyword ideas for a seed. |
| `gap` | DFS | Competitor content gap — keywords 2–3 competitors rank for that you don't. |
| `aio` | GSC+DFS | Re-rank striking-distance by **AI-Overview-adjusted** CTR (don't chase queries an AIO caps). |
| `consolidate` | none | Cannibalization → keep-one / 301-redirect plan. |
| `inlinks <url>` | none | Reverse internal-link recommender: existing pages that should link to a target. |
| `autolink` | none | Batch internal-link plan: for every under-linked page, which pages should link to it + anchor. |
| `decay` | GSC | Queries losing rank + pages losing clicks (needs ≥2 `gsc` snapshots). |
| `algo` | GSC | Attribute traffic shifts to known Google updates. |
| `radar` | none | Watch Google's Search Status Dashboard; flag when `algo.py` update knowledge is stale. |

## Produce
| Command | Needs | Does |
|---|---|---|
| `analyze [--keywords-file f]` | none+ | Report (cannibalization + gaps + GSC) → `recommendations.md`. |
| `brief <keyword>` | DFS | SERP + People-Also-Ask outline. |
| `draft <keyword>` | none | Writing packet → **the agent writes the article** (or a headless model, if `llm.provider` set). |
| `score <keyword> <url>` | DFS | Content comprehensiveness vs SERP competitors — missing subtopics. |
| `retitle <url> [--keyword k]` | none | Title/meta rewrite task → the agent proposes options. |

## Publish & orchestrate
| Command | Needs | Does |
|---|---|---|
| `publish <post.json>` | CMS | Publish via the configured connector (file/git-PR default, or WordPress/Webflow/Ghost). |
| `run [--monthly] [--keywords-file f]` | none+ | Full orchestration → `digest.md` (weekly signals; monthly adds trends/backlinks/algo/gaps). |
| `mcp` | none | Start the stdio MCP server (30 tools). Register in an MCP client as `python -m seo_agent mcp`. |

## Outputs written to the workspace
`corpus.json` (crawl) · `BASELINE.md` · `audit.md` · `plan.md` · `recommendations.md` ·
`digest.md` · `history/` (dated snapshots) · `content/` (drafts, for the git-PR flow). All
are gitignored by `safety`/`init`.

## Notes
- **needs "none+"** = works with none, better with GSC/DataForSEO.
- Content drafting needs **no key** when an agent drives the tool; set `llm.provider` to
  `anthropic`/`openai` (+ the matching key) only for unattended/cron runs.
- Fixes are **proposed, not applied** — review and apply as PRs (human merge gate).
