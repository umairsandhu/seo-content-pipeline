"""Editions & entitlements — the commercial packaging, in code.

The tool runs **entirely on the user's machine** — as a Claude Code skill, an MCP server,
or a standalone CLI. Nothing is hosted; there is no SaaS. The ENGINE is open-core: every
analysis / produce / control / AI-search capability, the autopilot loop, and the local
dashboard run free, forever, locally, keys bring-your-own.

Paid **editions are local commercial licenses** — they unlock white-label reports, multi-site
(agency/client) use, commercial/reseller rights, and priority support + updates. Set `edition`
in config (or env `SEO_EDITION`): open · pro · agency · enterprise. `has()` never blocks a core
capability; it only informs packaging and toggles white-label/commercial features. Stdlib only."""
import os

ORDER = ["open", "pro", "agency", "enterprise"]

# licensed (local) feature → minimum edition that unlocks it
_MIN = {
    "white_label_reports": "pro",     # drop the attribution footer / use your own brand
    "priority_support": "pro",        # support + update channel
    "commercial_use": "agency",       # use on client / commercial sites at scale
    "reseller_rights": "agency",      # deliver reports & services under your brand
    "custom_dev": "enterprise",       # bespoke connectors / checks
    "sla": "enterprise",
}
# multi-site workspace cap per edition (local — how many site folders you manage; soft nudge)
_WORKSPACES = {"open": 1, "pro": 10, "agency": 100000, "enterprise": 100000}

PRICING = {
    "open":       {"price": "$0",       "unit": "open-source · personal / single site", "workspaces": 1},
    "pro":        {"price": "$149",     "unit": "/yr license · white-label + multi-site + support", "workspaces": 10},
    "agency":     {"price": "$599",     "unit": "/yr license · unlimited sites + reseller rights", "workspaces": "unlimited"},
    "enterprise": {"price": "custom",   "unit": "· custom dev + SLA + done-for-you", "workspaces": "unlimited"},
}


def edition(cfg=None):
    e = (os.environ.get("SEO_EDITION") or (cfg or {}).get("edition") or "open").lower()
    return e if e in ORDER else "open"


def has(cfg, feature):
    """True if the current edition unlocks a licensed feature (core features → always True)."""
    minimum = _MIN.get(feature)
    if minimum is None:
        return True  # core capability — always available in open-core
    return ORDER.index(edition(cfg)) >= ORDER.index(minimum)


def workspace_cap(cfg):
    return _WORKSPACES.get(edition(cfg), 1)


def nudge(cfg, feature):
    """A tasteful upgrade line for a licensed feature (or '' if unlocked)."""
    if has(cfg, feature):
        return ""
    tier = _MIN.get(feature, "pro")
    return f"↑ {feature.replace('_', ' ')} is a **{tier.title()}** license feature — see docs/PRICING.md."


def render_md(cfg):
    e = edition(cfg)
    L = [f"# Edition — **{e.title()}**  ({PRICING[e]['price']} {PRICING[e]['unit']})", "",
         "Runs 100% on your machine — no hosting, no SaaS. Open-core: the full engine, all 52 tools, "
         "the MCP server, the autopilot loop and local dashboard are free. Licenses add white-label, "
         "multi-site/commercial use, and support.", "", "| feature | your edition |", "|---|---|",
         "| core engine + 52 tools + MCP + autopilot + dashboard | ✅ (all editions) |",
         f"| sites you can manage | {workspace_cap(cfg)} |"]
    for f in ("white_label_reports", "priority_support", "commercial_use", "reseller_rights", "custom_dev"):
        L.append(f"| {f.replace('_',' ')} | {'✅' if has(cfg, f) else '—'} |")
    L.append("\n_Set `edition` in config or `SEO_EDITION`. Pricing: docs/PRICING.md · License: COMMERCIAL.md._")
    return "\n".join(L)
