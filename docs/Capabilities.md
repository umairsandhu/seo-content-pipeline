# Capabilities — the complete, step-by-step reference

Everything the tool can do, grouped the way you actually use it, with **what each
command needs, what it returns, and how it degrades** when a credential is missing.
The tool is site-agnostic (point it at any domain), file-based (no DB/server), and
degrades gracefully — the core runs with **zero credentials**, and each API layers
in more.

**Three ways to drive it** — all the same engine:
- **CLI** — `python -m seo_agent <command>` from a site workspace.
- **MCP** — `python -m seo_agent mcp` exposes 41 tools to any MCP client (Claude, etc.).
- **Agent** — inside Claude/an LLM harness, the agent runs commands and *writes the
  prose* for `draft`/`retitle`/`refresh`/`aivis` packets (no content API key needed).

---

## The 0→100 journey (do these in order)

| # | Step | Command | You get |
|--:|---|---|---|
| 1 | **Bootstrap** a fork-safe, one-site workspace | `init --site https://…` | `config.json` + `.env` + hardened `.gitignore` |
| 2 | **Clear the readiness gate** — wire in the required accesses | `preflight` | a 0–100 scorecard; blocks the baseline until GSC/CSV + market data are set |
| 3 | **Baseline** the site | `onboard` | `BASELINE.md` (audit + speed + gaps + GSC + AI-search readiness) |
| 4 | **See the fix list** | `plan` | ranked "what to do next" (impact ÷ effort) fusing every signal |
| 5 | **Fix technical** issues (crawl → content → links) | `audit` `sitemap` `speed` `consolidate` `autolink` | proposed fixes (apply as PRs) |
| 6 | **Find & write** content | `discover` `gap` `brief` `draft` | opportunities → writing packets → drafts |
| 7 | **Optimize** for AI search | `entity` `citability` `schema` `aivis` | entity graph, extractable passages, structured data, citation tracking |
| 8 | **Publish / change the site** (gated) | `publish` · `control` · `crew` | file/PR or WordPress/Webflow/Ghost — blocked if thin/duplicate, and gated by your autonomy mode |
| 9 | **Track & deliver on cadence** | `run --daily/--weekly/--monthly [--email]` | `digest.md` + auto-emailed PDF |
| 10 | **Get the strategy** | `consult` | board-ready growth strategy from every signal |

Run `plan` (tactical next actions) or `consult` (full strategy) at **any** point, and
`wizard` for the guided setup — they always tell you the next best move.

---

## Layer 0 · Onboard & Site Doctor

| Command | Purpose | Needs | Returns |
|---|---|---|---|
| `init --site <url>` | Scaffold a new one-site workspace; run fork-safety | — | config/.env/.gitignore |
| `safety` | Fork-safety: `.env.example`, harden `.gitignore`, leak-scan tracked files + working tree | — | fork-safe verdict |
| `preflight` | **Onboarding readiness gate** — staged checklist + 0–100 score; blocks the baseline until required accesses are wired | — | `SETUP.md` when blocked |
| `onboard [--degraded]` | Full first-run baseline (gated); `--degraded` proceeds without required creds | — (more with keys) | `BASELINE.md` |
| `integrations` | Capability matrix — what's active / missing / what each gap unlocks | — | matrix |
| `audit` | **Site Doctor** — sitemap health, robots, llms.txt, meta/titles, H1, canonical, dedup/cannibalization, internal links (orphans/click-depth), CWV, structured data, a11y | corpus | `audit.md` |
| `sitemap` | Sitemap doctor only (limits, lastmod, coverage, orphans) | — | findings |
| `speed` | Core Web Vitals — Lighthouse lab + CrUX field (LCP/INP/CLS) | `PAGESPEED_API_KEY` for field | verdicts |
| `logs <access.log>` | Real crawler behavior: crawl waste + **AI-crawler coverage** (GPTBot/ClaudeBot/PerplexityBot/…) | a log file | coverage report |
| `schema [<url>]` | Generate JSON-LD (Organization/BlogPosting/Breadcrumb/FAQ) **+ validate** required fields | corpus | paste-ready `<script>` |
| `llmstxt` | Generate an `llms.txt` from the corpus | corpus | `llms.txt` |
| `renderdiff <url>` | Rendered-vs-raw DOM diff — what a raw crawl misses on JS/SPA sites | `pip install playwright` | render gap |

## Layer 1 · Observe (track over time)

| Command | Purpose | Needs | Returns |
|---|---|---|---|
| `ingest` | Crawl the sitemap → `corpus.json` (title/meta/headings/text/links/JSON-LD dates+authors) | — | corpus |
| `gsc` | Striking-distance + low-CTR; snapshots to `history/` | GSC service account | opportunities |
| `gsc --csv <path\|dir\|zip>` | Import a GSC CSV / Google-Sheet export when API access isn't possible | a GSC export | same, no API |
| `rank` | Track positions + SERP features (incl. **AI-Overview** flag) over time | DataForSEO | movement |
| `trends "<seed>"` | Emerging / rising keywords | DataForSEO | rising list |
| `backlinks` | Backlink profile / competitor link-gap | DataForSEO | link gap |
| `toxicity` | Conservative backlink-toxicity review | DataForSEO | flagged links |
| `ctr` | **First-party** position→CTR curve from your own GSC (feeds forecasts) | GSC history | curve |

## Layer 2 · Decide

| Command | Purpose | Needs | Returns |
|---|---|---|---|
| `consolidate` | Cannibalization → keep-one / 301-redirect plan | corpus | redirect plan |
| `research kw…` | Dedup verdict + internal-link targets for keywords | corpus | verdicts |
| `discover <seed>` | DataForSEO keyword ideas | DataForSEO | candidates |
| `gap` | Competitor content gap (keywords they rank for, you don't) | DataForSEO + competitors | gap list |
| `aio` | Re-rank striking-distance by AI-Overview-adjusted CTR | GSC | adjusted list |
| `inlinks <url>` / `autolink` | Internal-link plans (targets for a page / batch for orphans) | corpus | link plan |
| `pagerank` | **Internal PageRank / authority flow** — starved pillars, hoarders, + a sculpting plan | corpus (numpy) | sculpt plan |
| `decay` | Queries losing rank + pages losing clicks | ≥2 GSC snapshots | decliners |
| `algo` | Attribute traffic shifts to Google updates | ≥2 GSC snapshots | attribution |
| `radar` | Watch Google Search Status; flag stale algo knowledge | — | alerts |
| `authority` | Topical-authority clusters (pillar + link density) | corpus | clusters |
| `eeat` | E-E-A-T signals (author/dates/citations/trust pages — reads OG **and** JSON-LD, scans the sitemap) | corpus | signal coverage |

## Layer 3 · Produce (the agent writes)

| Command | Purpose | Needs | Returns |
|---|---|---|---|
| `analyze --keywords-file <f>` | Full report: cannibalization + gaps + GSC → `recommendations.md` | corpus (+ APIs) | recommendations |
| `brief "<kw>"` | Live SERP + People-Also-Ask outline | DataForSEO | brief |
| `draft "<kw>"` | SERP-grounded **writing packet** → the agent writes the article | corpus (+ DataForSEO) | packet or draft |
| `score "<kw>" <url>` | Content comprehensiveness vs SERP competitors | DataForSEO | gap score |
| `citability` | **Passage-citability** — how extractable each page is for AI answers (answer-first, Q&A headings, facts) | corpus | 0–100 per page |
| `retitle <url> --keyword` | Task → the agent writes 3 titles + a meta | — | packet |
| `refresh <url>` | Content-refresh packet: diagnose staleness → rewrite → re-verify | corpus (+ DataForSEO) | packet |

## Layer 3.5 · AI search / GEO (2026)

| Command | Purpose | Needs | Returns |
|---|---|---|---|
| `aivis` | **AI-visibility tracker** — brand mentions + citations + sentiment + competitor share-of-voice across ChatGPT/Perplexity/Gemini/Claude + Google AI Overviews | any of OPENAI/PERPLEXITY/GEMINI/ANTHROPIC keys or DataForSEO; **agent-mode packet with none** | grid + summary |
| `entity` | **Entity graph** — resolve to a Wikidata QID (free), read/generate `sameAs`, build Organization JSON-LD, score brand salience | — (Wikidata is free) | entity report + schema |
| `geo` | GEO/AEO readiness score (front-loaded answers, Q&A, schema, unblocked AI crawlers) | corpus | 0–100 |

## Layer 4 · Publish

| Command | Purpose | Needs | Returns |
|---|---|---|---|
| `gate <post.json>` | **Programmatic safety gate** — thin / near-duplicate / boilerplate / invalid-schema check | corpus | pass/block + reasons |
| `publish <post.json>` | Publish via the configured CMS — **enforces the safety gate first** | CMS creds (file/PR default) | url/path or block |
| `report [--pdf]` | Shareable self-contained HTML dashboard (+ PDF via headless browser) | — | `report.html` / `.pdf` |
| `mcp` | Start the MCP server (stdio) exposing the toolset | — | server |

## Layer 5 · Orchestrate & scale

| Command | Purpose | Needs | Returns |
|---|---|---|---|
| `plan` | **The co-pilot** — fuse every signal into a ranked next-actions list | whatever's available | `plan.md` |
| `run [--monthly]` | Scheduled run → `digest.md` (decay, striking, cannibalization; monthly adds trends, backlink gap, algo, and the **AI-search/GEO** section) | GSC/DataForSEO for depth | `digest.md` |
| `remediate` | Ordered, **human-gated** remediation plan mapping each audit finding to a fix command | corpus | plan |
| `intl` | hreflang / international validation (self-ref, x-default, return tags) | corpus | issues |
| `local` | Local SEO — NAP consistency + LocalBusiness schema (auto-detects if the site is local) | corpus | findings |
| `prospect` | Link-acquisition prospects from the competitor backlink gap + outreach packet | DataForSEO + competitors; agent-mode without | prospects |
| `jobs` | Durable job queue (SQLite) — schedule/retry long-running runs | — | queue |
| `projects [add <name> <dir>]` | Multi-site portfolio (agency) + readiness roll-up per client | — | portfolio |
| `run --daily / --weekly / --monthly [--email]` | Scheduled digest at three cadences; `--email` auto-sends the PDF | — (+GSC/DFS) | `digest.md` (+ email) |

## Layer 6 · Expert brain, full control & delivery

The tool doesn't just analyze — it can **think like a top consultant, run a team of
expert agents, control the live site, and deliver reports** — all under an autonomy
mode you choose.

| Command | Purpose | Needs | Returns |
|---|---|---|---|
| `consult` | **McKinsey/Google-level strategy** — assembles every signal and reasons as the STRATEGIST: situation → diagnosis → the 3–5 plays → 90-day roadmap → projected impact → risks | corpus (+ any signals); agent writes it | strategy |
| `crew article "<kw>"` | **Multi-agent content pipeline** — Researcher → Strategist → Writer → Editor → Tech-SEO, each a real expert persona, handing off to a safety-gated publish | corpus (+ DataForSEO) | staged brief |
| `crew change "<goal>"` | **Multi-agent change pipeline** — diagnose → prioritize → spec the exact `control` change (autonomy-gated) | corpus | change plan |
| `control <change.json>` | **Full site control** — `create` / `update_meta` / `update_content` / `delete` / `redirect` via the CMS API (WordPress/Webflow/Ghost) or git-PR file; every change autonomy-gated | CMS creds (file/PR default) | executed / queued / planned |
| `apply --approved` | Execute everything in the approval queue | — | results |
| `autonomy` | Show the current mode + pending approvals | — | status |
| `webtask <task.json>` | **Physical web control** — drive a real browser (goto/fill/click/extract) for sites with no API; mutating tasks autonomy-gated; falls back to a **computer-use MCP** packet | Playwright (or a computer-use MCP agent) | task log |
| `wizard [--interactive]` | **Guided onboarding** — numbered, hand-holding setup with ✅/▶/○ status and the exact next action; `--interactive` fills config.json via CLI prompts | — | next-step guide |
| `email [--pdf <path>]` | Email the PDF report to `report.email_to` | SMTP / Resend / SendGrid | send result |

### Autonomy modes (how much it may do on its own)
Set `autonomy` in config (or `SEO_AUTONOMY`): every action that changes the live site
or sends externally routes through this gate.

| Mode | Behavior |
|---|---|
| `manual` (default) | **Plan only** — writes a reviewable change file, executes nothing. |
| `approve` | **Queues** the action; you run `apply --approved` to execute. |
| `auto` | **Executes immediately** within guardrails — *destructive* ops (delete/redirect/bulk) still queue unless `autonomy.allow_destructive`, capped by `autonomy.max_auto_actions`. |

### Expert personas
Every generated output adopts a specific expert standard (`personas.py`): **Strategist**
(McKinsey + ex-Google Search engineer), **Tech-SEO**, **Writer** (E-E-A-T, answer-first,
citable), **Researcher**, **Editor**. This is what makes `draft`, `crew`, and `consult`
read like the work of a top specialist, not a generic model.

---

## Layer 7 · Closed loop — execute, measure, review, deliver

The moat: it doesn't just recommend the fix, it **ships the fix, measures the impact,
and learns** — with a human gate you can operate from anywhere.

| Command | Purpose | Needs | Returns |
|---|---|---|---|
| `pr <edits.json>` | **Repo execution** — edit meta/schema/canonical/redirects *in the codebase* as a unified diff, then `git branch → commit → gh pr create`. Autonomy-gated; logs to the ledger | git + `gh` (degrades to a `.patch`) | PR / diff |
| `control <change.json>` | Live-site CRUD (create/update_meta/update_content/delete/redirect) — autonomy-gated, logged | CMS (file/PR default) | executed/queued/planned |
| `ledger` | **Causal change ledger** — every change we made + before→after GSC clicks/position per URL **vs a holdout** of untouched pages (change-level attribution) | GSC history | change log + attribution |
| `learn [--notify]` | **The learning loop** — impact of each change at **day (+7) / week (+28) / month (+90)** horizons, aggregated by change type into "what works best" — plus an anonymized **cross-site** store so lessons compound across every company. Feeds `plan`. Runs automatically each cycle | GSC history | learned playbook |
| `brain [--add … --kind …]` | **Continuous self-learning memory** (Hermes-style observe→distill→reuse→refine): review notes + client replies distill into **taste**, measured outcomes into **proven playbooks**, surprises into **lessons** — all auto-injected into every Writer/Strategist prompt. Runs automatically each cycle | — (fills itself) | memory + taste + playbooks |
| `cms` | Every CMS connector + its env/config requirements: WordPress · Webflow · Ghost · **Shopify · Contentful · Strapi · Sanity · HubSpot · Drupal · Joomla · Wix · Notion** (+ honest "no write API" flags for Squarespace/Framer/Duda → file/git-PR flow) | — | connector matrix |
| `deliver <files…>` | **Client delivery** — email the files and/or upload to their **Google Drive folder** (service account or rclone). Every delivery is logged for the feedback loop | SMTP/Resend/SendGrid and/or drive.folder_id | delivery log + links |
| `feedback "…"` | Record the client's reaction to delivered work (or let `review --poll` catch email replies starting `FEEDBACK`). Distills into the brain as **taste** so the next deliverable matches how they work | — | learned preference |
| `explain <url>` | **"Why did /x change?"** — correlates the decline against our change log + GSC trend + Google-update timeline | GSC history | ranked, evidenced causes |
| `audit --fix` | Audit + the PR-ready remediation plan (triaged) | corpus | fixes to ship |
| `anomaly [--alert]` | Regression radar — indexation drops, traffic cliffs, rank drops, **AI-Overview appearance**; `--alert` pushes to channels | GSC/rank history | alerts |
| `competitors` | **Competitor sitemap-delta** — what each competitor newly published since last run | competitors set | new URLs |
| `ga4` | Organic **sessions / conversions / revenue** — business outcomes for the exec one-pager | GA4 property + service account | outcomes |

### Human-in-the-loop review — approve from anywhere
For teams that want a human to sign off before anything ships. Set
`review.channels` (and/or `autonomy: approve`): every queued change/draft is sent to
reviewers, and **only APPROVED items are pushed**.

| Command | Purpose |
|---|---|
| `review` | Send pending items to reviewers (CLI / email / Slack / Mattermost / WhatsApp) with approve / request-changes instructions |
| `review --poll` | Ingest replies — email (IMAP) + a local drop-file (webhooks in the app) |
| `approve <id>` / `changes <id> "notes"` | Local reviewer decision; `changes` records the feedback for revision |
| `apply --approved` | Push **only** the approved items |

**Flow:** `control`/`crew`/`pr` (queues) → `review` (notifies reviewers) → they reply
`APPROVE 3` or `CHANGES 3 make it punchier` (or you run `approve 3`) → `apply
--approved` ships it → `ledger` attributes the outcome. Channels: `SLACK_WEBHOOK_URL`,
`MATTERMOST_WEBHOOK_URL`, `WHATSAPP_TOKEN`+`WHATSAPP_PHONE_ID`, `IMAP_*` (reply polling).

### The autonomous loop + local dashboard
| Command | Purpose |
|---|---|
| `autopilot [--daily/--weekly/--monthly]` | One self-running cycle of the 4 agent roles — **Audit** (situation) → **Planner** (dated backlog + per-item cadence) → **Executor** (dispatch what's due, drip-capped, through the safety + review gate) → **Analyst** (attribution + report). Writes the shared `state/`; closes items when their change lands in the ledger. |
| `serve [--port 8787]` | A live local **dashboard** (`http://127.0.0.1:8787`) over that state — Situation · Plan (dated) · Execution · Review queue · Ledger — with **inline approve / request-changes** and a Run-cycle button. |

Schedule `autopilot` on cadence (cron or the `/schedule` skill); the Planner sets each
item's due-date and cadence, so the loop paces itself. See **[AGENT-LOOP-PLAN](AGENT-LOOP-PLAN.md)**.

### Where it runs — **local-only, no hosting**
Same engine, three runtimes, all on your own machine: **Claude Code** (skill), any
**MCP client** / agent runtime via `python -m seo_agent mcp` (52 tools), or a
**standalone CLI** (`pip install`; cron/CI the `autopilot`/`run`/`anomaly` commands for
cadence). Nothing is hosted — your data, keys, and the change ledger stay local. See
**[Distribution & Runtimes](APP-PLAN.md)**.

---

## Degradation matrix — what works with what

| You have… | Unlocks |
|---|---|
| **Nothing** (zero creds) | `init` `safety` `preflight` `wizard` `audit` `sitemap` `schema` `llmstxt` `ingest` `consolidate` `authority` `eeat` `geo` `entity` `citability` `pagerank` `intl` `local` `plan` `consult` `crew` `report` `gate` `autonomy` `control` (git-PR file) `renderdiff`* · `aivis`/`prospect`/`refresh`/`consult`/`crew` in **agent-mode** (the agent writes/runs) |
| **+ Autonomy mode + CMS/Playwright** | `control` + `webtask` execute real site changes (manual→plan, approve→queue, auto→apply); `apply --approved` |
| **+ Email transport** (SMTP/Resend/SendGrid) | `email`, `run --email`, `report --email` auto-deliver PDFs |
| **+ GSC** (or `gsc --csv`) | `gsc` `decay` `algo` `ctr` · striking-distance + low-CTR everywhere |
| **+ DataForSEO** | `discover` `gap` `trends` `backlinks` `rank` `aio` · live SERP grounding for `brief`/`draft`/`refresh` · live `aivis` (Google AIO) · `prospect` |
| **+ PageSpeed key** | `speed` field data (CWV) |
| **+ LLM engine keys** | live `aivis` across ChatGPT/Perplexity/Gemini/Claude · headless `draft`/`retitle` |
| **+ Playwright** | `renderdiff` + accurate audit of JS/SPA sites |
| **+ CMS creds** | `publish` to WordPress/Webflow/Ghost (git-PR file is the default, no creds) |

\* `renderdiff` needs Playwright; without it, it prints how to install it.

## Outputs (files the tool writes)

`BASELINE.md` · `audit.md` · `plan.md` · `recommendations.md` · `digest.md` ·
`SETUP.md` (when blocked) · `report.html` / `report.pdf` · `corpus.json` ·
`history/*/<date>.json` (time-series) · `seo.db` (queryable store) · `jobs.db` ·
`content/*.md` (git-PR publishing) · `site-changes/*.json` + `_redirects` (site control) ·
`approvals.json` (autonomy queue).

## Guardrails (why it's safe to sell)

- **Human-in-the-loop:** every content/fix output is *proposed*, applied as reviewed PRs — never auto-committed.
- **The publish safety gate** hard-blocks thin, near-duplicate, boilerplate, or invalid-schema pages (Google's 2026 scaled-content enforcement).
- **Fork-safety first:** secrets never leak from a fork — `.env` is git-ignored and leak-scanned.
- **Data stays yours:** file-based, in your own workspace — the tool never becomes a data redistributor.

See **[Getting-Started](Getting-Started.md)** for the walkthrough, **[Architecture](Architecture.md)**
for how it's built, **[AI-Search](AI-Search.md)** for the GEO playbook, and
**[LEARNINGS](LEARNINGS.md)** for the field notes that keep each run sharp.
