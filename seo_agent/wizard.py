"""Guided onboarding wizard — the friendly, hand-holding layer over `preflight`. It
turns setup into a numbered, stateful journey: it inspects the current state, shows
every step with a ✅/▶/○ status, and spells out the ONE next action in plain language
with the exact command or file edit and *why it matters*. Run it any time — it always
points at the next thing to do.

Interactive "modals": in a terminal it can ask for the site, competitors, and report
emails and write them into `config.json` for you (`wizard --interactive`). Agent-driven,
the agent asks those questions instead. Site-agnostic."""
from pathlib import Path

from . import journey


def _steps(cfg, root):
    r = journey.readiness(cfg, root=root)
    by = {i["key"]: i for s in r["stages"] for i in s["items"]}
    site = cfg.get("site", "")
    steps = [
        {"n": 1, "title": "Create the workspace", "done": by.get("workspace", {}).get("status") == "ok"
            and by.get("site", {}).get("status") == "ok",
         "why": "One folder = one site keeps data and secrets isolated per client.",
         "do": "`init --site https://your-site.com` in an empty folder, then set `site`/`sitemap` in config.json."},
        {"n": 2, "title": "Point at the sitemap", "done": by.get("sitemap", {}).get("status") == "ok",
         "why": "The sitemap is how the tool discovers and crawls your pages.",
         "do": "Set `sitemap` in config.json (usually /sitemap.xml or listed in robots.txt)."},
        {"n": 3, "title": "Lock down secrets (fork-safety)", "done": by.get("safety", {}).get("status") == "ok",
         "why": "Keys must never leak from a fork — .env is git-ignored and leak-scanned.",
         "do": "`safety` — it hardens .gitignore and writes .env.example. Never commit .env."},
        {"n": 4, "title": "Connect search performance", "done": by.get("gsc", {}).get("status") == "ok",
         "why": "GSC is your real demand data — it powers striking-distance, decay, and CTR curves.",
         "do": "Share a GSC service account (gsc_property + gsc_credentials) OR import an export: "
               "`gsc --csv <export.zip>` (a Google Sheet works too)."},
        {"n": 5, "title": "Connect market data", "done": by.get("dataforseo", {}).get("status") == "ok",
         "why": "Volumes, difficulty, SERPs, backlinks and gaps — how you find and size opportunities.",
         "do": "Put DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD in .env (or a Semrush/Ahrefs alt)."},
        {"n": 6, "title": "Set competitors & content sections", "done":
            by.get("competitors", {}).get("status") == "ok" and by.get("include", {}).get("status") == "ok",
         "why": "Focuses gap/backlink analysis and keeps the crawl on the pages that matter.",
         "do": "Set `competitors` (2–3 domains) and `include` (e.g. [\"/blog/\"]) in config.json."},
        {"n": 7, "title": "Pick an autonomy mode", "done": bool(cfg.get("autonomy")),
         "why": "Decide how much the tool may do on its own: plan-only, approve-then-do, or auto.",
         "do": "Set `autonomy` to `manual`, `approve`, or `auto` in config.json (default manual)."},
        {"n": 8, "title": "Set report delivery (optional)", "done": bool((cfg.get("report", {}) or {}).get("email_to")),
         "why": "Auto-email PDF reports to stakeholders on a daily/weekly/monthly cadence.",
         "do": "Set `report.email_to` + a transport (SMTP_* or RESEND_API_KEY) to enable `report --email`."},
        {"n": 9, "title": "Run the baseline", "done": Path(root, "BASELINE.md").exists(),
         "why": "Your snapshot + first prioritized plan — everything is measured against it.",
         "do": "`onboard` (clears the readiness gate first), then `plan` for the ranked next actions."},
    ]
    return steps, r


def next_step(cfg, root="."):
    steps, r = _steps(cfg, root)
    nxt = next((s for s in steps if not s["done"]), None)
    return {"steps": steps, "readiness": r, "next": nxt}


def interactive(cfg, root=".", config_path="config.json"):
    """Terminal 'modals' — collect the essentials and write them into config.json."""
    import json
    import sys
    if not sys.stdin.isatty():
        return {"error": "not a TTY — run in a terminal, or let the agent ask these questions"}
    print("\n=== SEO pipeline — guided setup ===\n")
    ask = lambda q, d="": (input(f"{q}" + (f" [{d}]" if d else "") + ": ").strip() or d)
    site = ask("Site URL", cfg.get("site", ""))
    comps = ask("Competitor domains (comma-separated)", ",".join(cfg.get("competitors", [])))
    emails = ask("Email PDF reports to (comma-separated, optional)")
    auton = ask("Autonomy [manual/approve/auto]", cfg.get("autonomy") if isinstance(cfg.get("autonomy"), str) else "manual")
    cfg["site"] = site.rstrip("/")
    cfg["sitemap"] = cfg.get("sitemap") or site.rstrip("/") + "/sitemap.xml"
    cfg["competitors"] = [c.strip() for c in comps.split(",") if c.strip()]
    cfg["autonomy"] = auton
    if emails:
        cfg.setdefault("report", {})["email_to"] = [e.strip() for e in emails.split(",") if e.strip()]
    Path(config_path).write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"\n✓ wrote {config_path}. Next: add keys to .env, then `wizard` to see the next step.\n")
    return {"ok": True, "config": config_path}


_ICON = {True: "✅", False: "○"}


def render_md(cfg, r):
    steps, nxt = r["steps"], r["next"]
    done = sum(s["done"] for s in steps)
    L = [f"# Setup wizard — {done}/{len(steps)} steps done  ·  readiness {r['readiness']['score']}/100", ""]
    for s in steps:
        cur = nxt and s["n"] == nxt["n"]
        icon = "▶" if cur else _ICON[s["done"]]
        L.append(f"{icon} **{s['n']}. {s['title']}**" + ("  ← you are here" if cur else ""))
    if nxt:
        L += ["", f"## ▶ Do this next: {nxt['title']}",
              f"**Why:** {nxt['why']}", f"**How:** {nxt['do']}"]
    else:
        L += ["", "🎉 **Setup complete.** Run `onboard` for the baseline, then `plan` (or `consult` for a "
              "full strategy). Schedule `run --daily/--weekly/--monthly` and enable `report --email`."]
    L.append("\n_Tip: `wizard --interactive` in a terminal fills config.json for you._")
    return "\n".join(L)
