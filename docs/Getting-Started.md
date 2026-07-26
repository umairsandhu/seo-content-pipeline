# Getting Started

From nothing to a prioritized action plan in ~5 minutes.

## 1. Install

```bash
git clone https://github.com/umairsandhu/seo-content-pipeline.git
cd seo-content-pipeline
pip install -e .                 # installs the `seo-content-pipeline` command
# optional extras:
pip install -e ".[gsc]"          # Google Search Console
pip install -e ".[render]"       # JavaScript rendering (then: playwright install chromium)
pip install -e ".[embeddings]"   # semantic similarity backend
```

Requires Python ≥ 3.9. Core deps are just `numpy` + `scikit-learn`; everything else is
stdlib. You can also run it without installing: `python -m seo_agent <cmd>` from the repo.

> Running as a **Claude skill / MCP tool**? It's already invokable — see
> [Integrations → MCP](Integrations.md#mcp-server). The commands below are identical.

## 2. Bootstrap a workspace (site-agnostic)

Pick an **empty directory for your site** (one directory = one site) and run:

```bash
mkdir my-site && cd my-site
seo-content-pipeline init --site https://www.yoursite.com
```

This scaffolds `config.json`, `.env` (from a generated `.env.example`), and a hardened
`.gitignore`, and confirms the workspace is **fork-safe** (no secret can be committed). It
refuses to run inside the tool's own install directory.

## 3. Configure

Edit **`config.json`**:

```jsonc
{
  "site": "https://www.yoursite.com",
  "sitemap": "https://www.yoursite.com/sitemap.xml",   // auto-discovered from robots.txt if wrong
  "include": ["/blog/"],            // path prefixes to ingest ("" = everything)
  "competitors": ["competitor.com"],// for gap + backlink analysis
  "gsc_property": "sc-domain:yoursite.com",
  "gsc_credentials": "gsc-service-account.json",
  "dataforseo": { "location_name": "United States", "language_name": "English" },
  "cms": { "type": "file", "dir": "content" },   // file (git-PR) | wordpress | webflow | ghost
  "brand": { "name": "YourBrand" }
}
```

Add any API keys to **`.env`** (all optional; everything degrades):

```
DATAFORSEO_LOGIN=…      DATAFORSEO_PASSWORD=…     # volume / SERP / backlinks / trends
PAGESPEED_API_KEY=…                               # Core Web Vitals
```

GSC uses a service-account JSON file (path in `config.json`), not an env var. Content drafting
needs **no key** when an agent drives the tool. Run `seo-content-pipeline integrations` to see
exactly what's active, missing, and what each gap unlocks.

## 4. First run

```bash
seo-content-pipeline preflight   # readiness gate: staged checklist + 0–100 score (wire the required accesses)
seo-content-pipeline onboard     # gated baseline: fork-safety → Site Doctor → speed → gaps → AI-search readiness → BASELINE.md
seo-content-pipeline audit       # the full technical Site Doctor → audit.md
seo-content-pipeline plan        # the co-pilot: ranked "what to do next" → plan.md
```

`preflight` blocks the baseline until the required accesses are wired in (search performance via
**GSC or a CSV import**, and market data via **DataForSEO or an alternative**) — it prints exactly
what to set and what each unlocks. To baseline anyway with partial data, use `onboard --degraded`.

Read `BASELINE.md` (your snapshot), `audit.md` (technical findings, fix crawl/index → content
→ links), and `plan.md` (do the top items, as PRs). Then optimize for AI search — `entity`,
`citability`, and `aivis` — and publish through the safety-gated `publish`.

## 5. The ongoing rhythm

- **Weekly:** `run` → `plan` → ship the top 5 as PRs.
- **Monthly:** `run --monthly` → `radar` (append new Google updates to `algo.py`) → re-`audit`.
- **Quarterly:** re-benchmark, re-pull AI-search stats, build the next capability.

Follow the full phased path in **[PLAYBOOK.md](../PLAYBOOK.md)**.

## Zero-credential mode

Without any keys you still get: the entire **Site Doctor** (sitemap, robots, llms.txt,
metadata, H1, canonical, dedup, content depth, internal links, redirects, hreflang,
accessibility, structured-data detection, CSR detection), **E-E-A-T** and **topical-authority**
structure, **schema** generation, **consolidation** + **internal-link** recommenders, and —
when an agent drives it — **written content**. Wire GSC + DataForSEO to add rank/CTR/gap data.
