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

## AI search / GEO & advanced (2026)
| Command | Needs | Does |
|---|---|---|
| `aivis` | LLM keys / DFS; agent-mode w/o | AI-visibility: mentions + citations + sentiment + competitor SoV across ChatGPT/Perplexity/Gemini/Claude + Google AI Overviews. |
| `entity` | none (Wikidata free) | Entity graph: Wikidata QID + `sameAs` + generated Organization JSON-LD + brand salience. |
| `citability` | none | Passage-citability (0–100) — how extractable each page is for AI answers. |
| `ctr` | GSC history | First-party position→CTR curve from your own data. |
| `pagerank` | none | Internal PageRank / authority flow — starved pillars, hoarders, sculpting plan. |
| `refresh <url>` | none+ | Content-refresh packet: diagnose staleness → rewrite → re-verify. |
| `prospect` | DFS + competitors; agent-mode w/o | Link-acquisition prospects from the competitor backlink gap + outreach packet. |
| `intl` | none | hreflang / international validation. |
| `local` | none | Local SEO — NAP consistency + LocalBusiness schema (auto-detects if local). |
| `renderdiff <url>` | Playwright | Rendered-vs-raw DOM diff for JS/SPA sites. |
| `remediate` | none | Ordered, human-gated remediation plan from the audit. |
| `gate <post.json>` | none | Programmatic safety gate (thin/near-dup/boilerplate/schema) — also enforced on `publish`. |
| `preflight` | none | Onboarding readiness gate — staged checklist + 0–100 score. |
| `jobs` / `projects [add <name> <dir>]` | none | Durable job queue · multi-site agency portfolio + readiness roll-up. |

## Expert brain, control & delivery
| Command | Needs | Does |
|---|---|---|
| `consult` | none+ | McKinsey/Google-level growth strategy from every signal (Pyramid Principle, agent writes it). |
| `crew article "<kw>"` / `crew change "<goal>"` | none+ | Multi-agent pipeline: Researcher→Strategist→Writer→Editor→Tech-SEO→publish (or diagnose→plan→apply), each a real expert persona. |
| `control <change.json>` | CMS (file/PR default) | Full site control: create/update_meta/update_content/delete/redirect — **autonomy-gated**. |
| `apply --approved` | none | Execute the approval queue (approve mode). |
| `autonomy` | none | Show the autonomy mode (`manual`/`approve`/`auto`) + pending approvals. |
| `webtask <task.json>` | Playwright / computer-use MCP | Drive a real browser for API-less sites; mutating tasks autonomy-gated. |
| `wizard [--interactive]` | none | Guided, hand-holding setup — next best step; `--interactive` fills config.json. |
| `email [--pdf <path>]` | SMTP/Resend/SendGrid | Email the PDF report to `report.email_to`. |
| `pr <edits.json>` | git + `gh` | Edit meta/schema/redirects in the codebase → unified diff → open a PR (autonomy-gated, logged). |
| `ledger` | GSC history | Change log + causal attribution (before→after vs a holdout of untouched pages). |
| `explain <url>` | GSC history | "Why did /x change?" — vs our change log + GSC trend + Google updates. |
| `audit --fix` | corpus | Audit + PR-ready remediation plan. |
| `ga4` | GA4 + service acct | Organic sessions / conversions / **revenue**. |
| `competitors` | competitors set | Monthly sitemap delta — what competitors newly published. |
| `anomaly [--alert]` | GSC/rank history | Indexation drops, traffic cliffs, rank drops, AI-Overview appearance; `--alert` pushes to channels. |

## Human review (approve from anywhere)
| Command | Needs | Does |
|---|---|---|
| `review [--poll]` | review.channels | Send queued items to reviewers (CLI/email/Slack/Mattermost/WhatsApp); `--poll` ingests email/drop-file replies. |
| `approve <id>` / `changes <id> "notes"` | none | Reviewer decision; only approved items are pushed by `apply --approved`. |

## Publish & orchestrate
| Command | Needs | Does |
|---|---|---|
| `publish <post.json>` | CMS | Publish via the configured connector (file/git-PR default, or WordPress/Webflow/Ghost). **Enforces the safety gate first.** |
| `report [--pdf]` | none | Shareable self-contained HTML dashboard (+ PDF via headless browser). |
| `run [--daily\|--monthly] [--email] [--keywords-file f]` | none+ | Scheduled digest → `digest.md` at three cadences (daily pulse / weekly / monthly full); `--email` auto-sends the PDF. |
| `mcp` | none | Start the stdio MCP server (41 tools). Register in an MCP client as `python -m seo_agent mcp`. |

## Outputs written to the workspace
`corpus.json` (crawl) · `BASELINE.md` · `audit.md` · `plan.md` · `recommendations.md` ·
`digest.md` · `history/` (dated snapshots) · `content/` (drafts, for the git-PR flow). All
are gitignored by `safety`/`init`.

## Notes
- **needs "none+"** = works with none, better with GSC/DataForSEO.
- Content drafting needs **no key** when an agent drives the tool; set `llm.provider` to
  `anthropic`/`openai` (+ the matching key) only for unattended/cron runs.
- Fixes are **proposed, not applied** — review and apply as PRs (human merge gate).
