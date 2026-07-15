# seo-content-pipeline

A **site-agnostic**, lightweight SEO automation engine across five layers. Point it
at any domain — no CMS coupling, no database, no server. Everything is file-based and
degrades gracefully; each layer activates as you add credentials.

1. **Observe** — ingest the site (sitemap) and track GSC rank/CTR, backlinks, and
   trends *over time* in `history/` (the longitudinal signal everything else builds on).
2. **Decide** — cannibalization clusters, content gaps, striking-distance (pos 5–15),
   low-CTR pages, **content decay** (posts slipping run-over-run), and **algorithm-update
   attribution** (traffic shifts mapped to Google updates).
3. **Produce** — SERP + People-Also-Ask-grounded **briefs**, article **writing packets**, and
   title/meta rewrite **tasks**. Run inside Claude/an agent, the agent writes the content
   (no key); a headless `llm.provider` (Anthropic/OpenAI) fills it for unattended cron runs.
4. **Publish** — one interface over **WordPress / Webflow / Ghost / git-PR** connectors,
   and an **MCP server** exposing the whole pipeline to any MCP client.
5. **Orchestrate** — scheduled weekly/monthly **`run`** → `digest.md`: what changed, what
   to do, what to approve.

Outputs: `recommendations.md` (`analyze`), `digest.md` (`run`), `history/` snapshots.

## Quick start
```bash
cp config.example.json config.json     # edit: site, sitemap, include, competitors, cms
export DATAFORSEO_LOGIN=…  DATAFORSEO_PASSWORD=…      # optional (volumes/SERP/backlinks/trends)
pip install numpy scikit-learn                       # + google libs for GSC
# Content drafting needs NO key when driven by an agent (Claude/OpenAI writes it);
# set llm.provider + ANTHROPIC_API_KEY|OPENAI_API_KEY only for unattended cron runs.

python -m seo_agent ingest                           # sitemap → corpus.json
python -m seo_agent gsc                              # opportunities + start building history
python -m seo_agent analyze --keywords-file seeds.txt   # → recommendations.md
python -m seo_agent run --monthly                    # full pipeline → digest.md
```

## Config (`config.json`)
| key | meaning |
|---|---|
| `site` / `sitemap` | domain + sitemap URL (sitemap defaults to `<site>/sitemap.xml`) |
| `include` / `exclude` | path prefixes to ingest / substrings to skip |
| `max_pages` | ingest cap (ingest is ~1s/page) |
| `pillars` | hub URLs to prefer as internal-link targets |
| `gsc_property` | `sc-domain:example.com` or the URL-prefix property |
| `gsc_credentials` | path to a Google service-account JSON (property shared to it, read-only) |
| `dataforseo` | `{location_name, language_name}` for volume/SERP/backlinks/trends |
| `competitors` | domains for backlink link-gap + content-gap analysis |
| `history_dir` | where dated snapshots live (default `history/`) |
| `llm` | `{model, max_tokens}` for drafting (Layer 3) |
| `cms` | publish target: `{type: "file"｜"wordpress"｜"webflow"｜"ghost", …}` |

Secrets never go in the config — via env: `DATAFORSEO_LOGIN/PASSWORD`, `ANTHROPIC_API_KEY`,
`WP_USER/WP_APP_PASSWORD`, `WEBFLOW_TOKEN`, `GHOST_ADMIN_KEY`; GSC via the service-account file.

## First run (onboarding)
`python -m seo_agent onboard` runs **fork-safety first** (writes `.env.example`,
hardens `.gitignore`, leak-scans so the operator's keys can't leak from a fork),
then the **Site Doctor** (sitemap·robots·llms.txt·metadata·H1·canonical·dedup·
content-depth·internal-links·speed), competitor gap, and GSC → `BASELINE.md`. See
`ONBOARDING.md` for the staged agent flow.

## Commands
Onboard: `safety` · `integrations` · `onboard` — Doctor: `audit` · `sitemap` · `speed` · `logs` · `aio` · `llmstxt` · `gap`
Pipeline: `ingest` · `gsc` · `decay` · `algo` · `radar` · `backlinks` · `trends <seed…>` ·
`research <kw…>` · `discover <seed>` · `analyze` · `brief <kw>` · `draft <kw>` ·
`retitle <url>` · `publish <post.json>` · `run [--monthly]` · `mcp`  (see `SKILL.md`).

## Design
File-based; TF-IDF cosine for similarity (`index.build_vectorizer` / `_embed_backend`
is the swap-point for semantic embeddings — `SEO_EMBEDDINGS=1` + `fastembed`). `history.py`
adds the time-series store that makes decay/algo/emerging work. Providers degrade
gracefully — the core (ingest + dedup + gaps) runs with zero credentials; GSC, DataForSEO,
the content model, and the CMS connectors each layer in when configured. The MCP server
(`seo_agent/mcp_server.py`) exposes the whole pipeline over stdio JSON-RPC with no deps.
