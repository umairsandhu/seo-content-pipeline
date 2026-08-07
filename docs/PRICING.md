# Pricing & Packaging

**Runs entirely on your machine — no hosting, no SaaS.** Install it as a Claude Code skill,
an MCP server, or a standalone CLI. Nothing phones home; your data and keys stay local.

**Open-core.** The full engine — every command, all 59 MCP tools, the **autopilot loop**, the
**local dashboard**, site-control, and the causal ledger — is free and open-source forever,
keys bring-your-own. Paid editions are **local commercial licenses** that unlock white-label
reports, multi-site / client use, reseller rights, and priority support + updates.

## The tiers (all run locally)

| | **Open** | **Pro** | **Agency** | **Enterprise** |
|---|---|---|---|---|
| **Price** | $0 · open-source | **$149**/yr license | **$599**/yr license | custom |
| Full engine + 59 tools + MCP | ✅ | ✅ | ✅ | ✅ |
| Autopilot loop + local dashboard (`serve`) | ✅ | ✅ | ✅ | ✅ |
| Site control (PRs/CMS/browser) + review | ✅ | ✅ | ✅ | ✅ |
| AI-search (aivis/entity/citability) + ledger | ✅ | ✅ | ✅ | ✅ |
| Sites you manage | 1 (personal) | 10 | unlimited | unlimited |
| **White-label reports** (your brand, no footer) | — | ✅ | ✅ | ✅ |
| **Priority support + update channel** | — | ✅ | ✅ | ✅ |
| **Commercial / client use at scale** | — | ✅ | ✅ | ✅ |
| **Reseller rights** (deliver under your brand) | — | — | ✅ | ✅ |
| Custom connectors/checks · SLA · done-for-you | — | — | — | ✅ |

Set the edition with `edition` in config or `SEO_EDITION`; `python -m seo_agent edition` shows
what's active. Nothing in the analysis / production / control engine is ever locked — the
license only toggles white-label + commercial/reseller use + support.

## Why this model

Because it's **local and open-source**, you sell a **commercial license + support**, not
access — the honest open-core play. The free tier is the funnel (the zero-credential Site
Doctor + GEO audit is the wedge; the Claude-skill / MCP distribution is CAC-free), and the
paid license is for **agencies and businesses** who want white-label deliverables, multi-client
use, and a support channel.

- **Open ($0)** — a person auditing their own site; the community; contributors.
- **Pro ($149/yr)** — a consultant / in-house team running it on their own sites, white-labeled.
- **Agency ($599/yr)** — an agency delivering it to clients under their own brand (reseller).
- **Enterprise (custom)** — bespoke connectors, an SLA, or done-for-you setup + operation.

## Data costs (always bring-your-own)

Every tier is BYO keys — you pay DataForSEO directly (sub-cent per SERP call) and content is
agent-written or on your own LLM key. The tool never touches data revenue, never resells or
warehouses data, and every workspace is isolated on your disk. This is a compliance feature,
not a limitation.

## Managed pilot (the productized service)

Don't want to run it yourself? We run the whole loop **on our machine, for your site**:
onboarding, daily autopilot cycles, human-reviewed changes shipped to your CMS, a weekly
PDF in your inbox or Drive folder, and the measured ledger at day 30/60/90.

- **Pilot** — $500/site/month, 90-day engagement, cancel anytime after month one.
- Includes a Pro license; the workspace (and everything it learned) is **yours to keep**
  if you take it in-house afterwards — no lock-in, that's the point of local-first.
- Capacity-limited (it's a human-reviewed service, not a farm).

## Add-ons (services, not hosting)
- **Done-for-you onboarding** — we wire GSC/GA4/DataForSEO, set the autonomy policy + cadence. $299 one-time.
- **White-label pack** (Agency) — brand assets applied to reports/dashboards.
- **Custom connectors / checks** (Enterprise).

## How to buy
- **Open** is `pip install` / install the Claude skill — nothing to buy.
- **Pro / Agency** — open a [GitHub issue titled "License"](https://github.com/umairsandhu/seo-content-pipeline/issues/new)
  or email the maintainer; you'll get a payment link + your license key within a day.
  (Self-serve checkout is coming — the license key simply sets `edition` in your config.)
- **Managed pilot / Enterprise** — same channel; include your site and CMS.

_Prices are launch targets; adjust with adoption. There is no hosted subscription — you run
everything on your own machine or CI (or we run it for you as a service)._
