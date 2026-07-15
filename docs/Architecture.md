# Architecture

## Design principles
1. **Site-agnostic.** No hardcoded site anywhere; everything comes from `config.json`. One
   directory = one site. `init` bootstraps a clean workspace; the code never writes to its
   own install dir.
2. **File-based, no DB, no server.** State is JSON files in the workspace (`corpus.json`,
   `history/…`). Fine to ~thousands of pages; the swap-point to a vector DB is documented but
   deliberately not taken.
3. **Graceful degradation.** Every external API is optional. Missing credentials disable a
   capability, never crash a run. The full Site Doctor + content work run with zero keys.
4. **Deterministic core.** Pure Python + `numpy`/`scikit-learn` (TF-IDF cosine). The LLM does
   editorial writing/judgment; the code does the measurable, repeatable work.
5. **Agent-native.** Content and decisions are the *agent's* job — the tool hands it packets
   and data. A headless model is only a fallback for unattended runs.
6. **Propose, don't apply.** Findings and fixes are surfaced; changes ship as PRs (human
   merge gate).

## The five layers

```
0 · Onboard      init · safety · integrations · onboard        → BASELINE.md
    Plan         plan  (fuses everything below into ranked actions)
1 · Observe      ingest · gsc · rank · backlinks · trends      → corpus.json + history/
2 · Decide       audit · gap · aio · decay · algo · consolidate · authority · eeat …
3 · Produce      brief · draft · score · retitle               (agent writes; model optional)
4 · Publish      publish (WordPress/Webflow/Ghost/git-PR) · mcp
5 · Orchestrate  run [--monthly] → digest.md   ·  radar (build loop)
```

## Module map (`seo_agent/`)
| Module | Role |
|---|---|
| `config.py` | Config loader + `.env` auto-loader; defaults for every capability. |
| `ingest.py` | Sitemap crawl → `corpus.json`; captures title/meta/H1/links/canonical/robots/hreflang/lang/img-alt/author/dates/JSON-LD/CSR/status. Sitemap auto-discovery; checkpointing; optional JS render. |
| `index.py` | TF-IDF dedup + internal-link index (title-space + body-space). `build_vectorizer` is the embeddings swap-point. |
| `providers.py` | External data: DataForSEO (volume/SERP/backlinks/trends/ranked-keywords), GSC, and `http_json` (the generic "integrate any API" primitive) + optional LLM (Anthropic/OpenAI). |
| `integrations.py` | The declarative API registry — generates `.env.example`, drives onboarding, reports the capability matrix. |
| `safety.py` | Fork-safety: `.env.example`, `.gitignore` hardening, secret leak-scan, pre-commit hook. |
| `audit.py` | The Site Doctor (all technical/on-page/E-E-A-T-adjacent/a11y checks). |
| `speed.py` | PageSpeed (Lighthouse lab) + CrUX (field) + accessibility score. |
| `logs.py` | Server log-file analysis: Google + AI crawlers, crawl waste, AI-crawler coverage. |
| `aio.py` | AI-Overview-adjusted CTR model. |
| `rank.py` | Rank + SERP-feature tracking over time. |
| `decay.py` · `algo.py` · `radar.py` | Content decay; Google algorithm-update attribution; the build-loop sensor. |
| `backlinks.py` · `trends.py` | Backlink profile/gap/toxicity; emerging-keyword detection. |
| `analyze.py` | Cannibalization, content gaps, competitor gap, GSC opportunities. |
| `eeat.py` · `authority.py` · `internal.py` · `content_score.py` · `schema.py` | E-E-A-T signals; topical-authority structure; internal-link + consolidation recommenders; comprehensiveness scoring; JSON-LD generation. |
| `plan.py` | The action engine — fuses all signals into a ranked plan. |
| `produce.py` | Briefs, drafts (agent-written), retitles. |
| `publish.py` | CMS connectors. |
| `orchestrate.py` · `onboard.py` | Scheduled runs + digest; `init` + first-run baseline. |
| `mcp_server.py` | Stdlib stdio MCP server exposing 30 tools. |

## Data flow
```
sitemap ─▶ ingest ─▶ corpus.json ─┬─▶ audit / eeat / authority / schema / a11y ─▶ audit.md
                                   ├─▶ index (dedup + link graph) ─▶ cannibalization / inlinks
GSC ──────────────▶ history/ ─────┼─▶ decay / algo / striking-distance
DataForSEO ───────▶ SERP/volume ──┼─▶ gap / aio / rank / trends / score
                                  └─▶ plan ─▶ plan.md   ·   run ─▶ digest.md
```

## Extending
Add a Site-Doctor check (`audit.py`), an API (`integrations.py` + a provider fn using
`providers.http_json`), or a CMS connector (`publish.py`) in one place each. See
[Contributing.md](Contributing.md).
