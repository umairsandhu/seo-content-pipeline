# Commercial editions & licensing

## It runs on your machine — no hosting
There is **no hosted service and no SaaS**. The tool runs entirely locally — as a Claude Code
skill, an MCP server, or a standalone CLI. Your data and API keys never leave your machine.

## Open-core model
The **engine is open-core**: the full `seo_agent` package — every command, all 52 MCP tools,
the autopilot loop, the local dashboard, site control, and the causal ledger — is free to use
and self-host under the repository's open-source `LICENSE`. Bring your own API keys.

Commercial **editions** (Pro / Agency / Enterprise) do not unlock engine capabilities — they
are **local commercial licenses** that grant white-label reports, multi-site / client use,
reseller rights, and priority support + updates. See [docs/PRICING.md](docs/PRICING.md) for the
matrix and prices; entitlements are enforced in code by `seo_agent/edition.py`.

## What each edition is
- **Open** — open-source, free, personal / single-site, community support. The full engine.
- **Pro ($149/yr)** — white-label reports, up to 10 sites, priority support + updates. For a
  consultant or in-house team running it on their own sites.
- **Agency ($599/yr)** — unlimited sites, reseller rights (deliver reports/services under your
  own brand), commercial use at scale. The primary commercial tier.
- **Enterprise (custom)** — custom connectors/checks, SLA, done-for-you onboarding + operation.

## Entitlements in code
`edition` (config) or `SEO_EDITION` (env) sets the tier. `edition.has(cfg, feature)` gates only
licensed extras (white-label, commercial/reseller use, support); core features always return
`True`. `python -m seo_agent edition` prints the active entitlements. This is honest packaging —
the open tier is never crippled, and because it's local, the license is largely an honor
system + white-label toggle for businesses that want commercial terms and support.

## Data & compliance (all editions, always local)
- Bring-your-own API keys; the tool is not a data redistributor.
- Nothing is hosted; every workspace lives on your disk and is isolated.
- Every automated change is logged to that workspace's causal ledger for auditability.

## Trademarks & white-label
The open-source license covers the code. Product name and branding are reserved; the
**white-label** entitlement (Pro+) lets you ship reports and dashboards under your own brand
for your own clients.

## How to obtain a license
- **Open:** clone / `pip install` / install the Claude skill — no key required.
- **Pro / Agency / Enterprise:** contact the maintainer for a license key; set `edition` (or
  `SEO_EDITION`) accordingly. No account, no hosting — the key just unlocks local white-label /
  commercial features and the support channel.

_This document describes the intended commercial model; it is not itself a contract. The
binding software license is the repository `LICENSE`._
