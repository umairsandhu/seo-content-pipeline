# Getting Started

From nothing to a self-improving SEO loop. Three stops: **try it (5 min) → your site
(20 min) → on autopilot (15 min/day of your attention).**

## 0. Try it before you wire anything (zero keys)

```bash
pip install numpy scikit-learn
git clone https://github.com/umairsandhu/seo-content-pipeline.git && cd seo-content-pipeline
pip install -e .
python -m seo_agent demo && cd seo-demo && python -m seo_agent start
```

`demo` builds a synthetic workspace — a 17-page site with realistic flaws, 3 months of
search history, and 4 measured changes (2 wins, 1 honest loss). `start` opens the guided
dashboard in your browser. Poke `plan`, `learn`, `practices`, `brain`, `audit`. Nothing
here needs a credential or the network.

> Running as a **Claude Code skill**? `/plugin install seo-content-pipeline` — then just ask:
> *"onboard www.example.com"*. As an **MCP server**: `python -m seo_agent mcp` (59 tools).

## 1. Point it at your real site

One folder = one site. In an EMPTY directory:

```bash
mkdir my-site && cd my-site
python -m seo_agent init --site https://www.yoursite.com
python -m seo_agent start
```

`init` scaffolds three files and hardens the folder:
- **`config.json`** — every setting already has a visible slot + a `_hints` how-to
  (like `.env.example`, but for config). `config` shows what's filled; `config --fix`
  upgrades old configs.
- **`.env`** — where secrets live (git-ignored, leak-scanned; never in config).
- **`.gitignore`** — hardened so no key can ever be committed.

`start` opens the dashboard; its **Getting-started panel** lists your setup as numbered
steps and always names the ONE next action with the exact command. Prefer text? `wizard` —
and **`wizard --interactive` asks you to pick a provider per capability**, gateway-style:
each seam shows the RECOMMENDED option (and why), the free open-source local alternative
(SearXNG, Ollama, Lighthouse), and skip — then writes your config and lists exactly what
goes in `.env`. Nothing is assumed; everything has a zero-key path.

### Connect your data (the two that matter)

**Search Console — pick whichever is easier:**
- *No-API path:* export Performance data from Search Console → `gsc --csv export.zip`. Done.
- *API path:* save your service-account JSON in the folder as `gsc-credentials.json`
  (**auto-detected**, git-ignored), set `gsc_property` in config — then `preflight`
  literally prints the service-account email to invite in GSC → Settings → Users.

**Market data:** put `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` in `.env`
(sub-cent per call, billed to you directly). Unlocks volumes, SERPs, PAA, backlinks, gaps.

**Your CMS (optional, for shipping fixes):** run `cms` — a matrix of all 13 connectors
(WordPress, Webflow, Ghost, Shopify, Contentful, Strapi, Sanity, HubSpot, Drupal, Joomla,
Wix, Notion) with the exact env vars + config keys each needs. No CMS API? The default
file/git-PR flow ships changes as reviewable diffs.

### Baseline

```bash
python -m seo_agent preflight   # the readiness gate — resolve the 🔴 items it names
python -m seo_agent onboard     # Site Doctor + baseline → BASELINE.md
python -m seo_agent plan        # the co-pilot: ranked "what to do next"
python -m seo_agent voice       # measure your existing brand voice → every draft matches it
```

## 2. Turn on the loop

Set `"autonomy": "approve"` in config (the recommended mode: it queues changes for your
OK, ships nothing alone). Then two cron lines:

```cron
30 8 * * *  cd ~/sites/my-site && python3 -m seo_agent gsc && python3 -m seo_agent autopilot --daily
0  9 * * 5  cd ~/sites/my-site && python3 -m seo_agent report --pdf && python3 -m seo_agent deliver report.pdf
```

Your daily 5 minutes: open `serve` (http://127.0.0.1:8787) → approve/decline the queue.
Decline **with a note** — every note teaches the brain your taste. Weekly: import a fresh
GSC export if you're on the CSV path (attribution needs the snapshots).

## 3. Watch it learn

- `ledger` — every shipped change, measured vs a holdout of untouched pages
- `learn` — impact by **day (+7) / week (+28) / month (+90)**, per change type
- `practices` — best practices found → fixed → **measured**, with this-site numbers
- `brain` — what it has learned about your site and your taste
- `explain <url>` — "why did this page move?" with evidence

The loop compounds: proven change types get recommended more, losers get flagged
"rethink", and (opt-in) anonymized lessons carry across your workspaces so site #2
starts smarter than site #1 did.

## Troubleshooting

- **`preflight` shows red** — each 🔴 line includes the exact fix; `config` shows every slot.
- **Site looks empty / client-rendered** — the audit flags CSR; set `render.enabled: true`
  (`pip install playwright && playwright install chromium`).
- **A command degraded** — that's by design: everything runs with whatever access exists
  and tells you what adding a key would unlock (`integrations` shows the matrix).

Full command reference: **[Capabilities](Capabilities.md)** · commercial licensing:
**[PRICING](PRICING.md)**.
