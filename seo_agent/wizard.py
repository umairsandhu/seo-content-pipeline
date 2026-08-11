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
         "do": by.get("gsc", {}).get("how_to") or "Easiest: `gsc --csv <export.zip>` (a Search Console "
               "export or Google Sheet). API: save the service-account JSON here as "
               "gsc-credentials.json (auto-detected) + set gsc_property in config.json."},
        {"n": 5, "title": "Connect market data", "done": by.get("dataforseo", {}).get("status") == "ok",
         "why": "Volumes, difficulty, SERPs, backlinks and gaps — how you find and size opportunities.",
         "do": "Put DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD in .env (or a Semrush/Ahrefs alt)."},
        {"n": 6, "title": "Set competitors & content sections", "done":
            by.get("competitors", {}).get("status") == "ok" and by.get("include", {}).get("status") == "ok",
         "why": "Focuses gap/backlink analysis and keeps the crawl on the pages that matter.",
         "do": "Set `competitors` (2–3 domains) and `include` (e.g. [\"/blog/\"]) in config.json."},
        {"n": 7, "title": "Connect your CMS (publish + update/delete)",
         "done": by.get("cms", {}).get("status") == "ok",
         "why": "Lets approved changes ship straight into WordPress / Webflow / Ghost / Shopify / "
                "Contentful / Strapi / Sanity / HubSpot / Drupal / Joomla / Wix / Notion. "
                "No CMS API? The file/git-PR flow always works.",
         "do": _cms_do(cfg)},
        {"n": 8, "title": "Pick an autonomy mode", "done": bool(cfg.get("autonomy")),
         "why": "Decide how much the tool may do on its own: plan-only, approve-then-do, or auto.",
         "do": "Set `autonomy` to `manual`, `approve`, or `auto` in config.json (default manual)."},
        {"n": 9, "title": "Set delivery + the feedback loop (optional)",
         "done": by.get("delivery", {}).get("status") == "ok",
         "why": "Reports/drafts reach the client by email or their Google Drive folder; their replies "
                "feed the taste/learning loop (`feedback`), so output matches how they like to work.",
         "do": "Set `report.email_to` + a transport (SMTP_* or RESEND_API_KEY), and/or `drive.folder_id` "
               "(share the folder with your service account). Then `deliver report.pdf`."},
        {"n": 10, "title": "Run the baseline", "done": Path(root, "BASELINE.md").exists(),
         "why": "Your snapshot + first prioritized plan — everything is measured against it.",
         "do": "`onboard` (clears the readiness gate first), then `plan` for the ranked next actions."},
    ]
    return steps, r


def _cms_do(cfg):
    from . import cms_extra
    t = ((cfg.get("cms") or {}).get("type") or "file").lower()
    req = cms_extra.requirements(t) or {}
    if t == "file":
        return ("Set `cms.type` in config.json — run `cms` for the full matrix. e.g. webflow needs "
                "WEBFLOW_TOKEN (.env) + cms.collection_id/field_map; shopify needs SHOPIFY_ACCESS_TOKEN "
                "+ cms.store/blog_id.")
    if "manual" in req:
        return f"{req['name']} has no public write API — keep the file/git-PR flow ({req['manual']})."
    need = cms_extra.missing_env(t)
    return (f"{req['name']}: add {', '.join(need) or 'creds'} to .env (git-ignored) and set "
            f"{', '.join(req.get('config', [])) or 'cms config'} in config.json.")


def next_step(cfg, root="."):
    steps, r = _steps(cfg, root)
    nxt = next((s for s in steps if not s["done"]), None)
    return {"steps": steps, "readiness": r, "next": nxt}


# ── provider choices, OpenClaw-gateway style: every capability seam presents its
# options — the RECOMMENDED one first (and why), the free/OSS local alternative, and
# skip. The user picks; we write config and tell them exactly what goes in .env. ──
CHOICES = [
    {"seam": "Search performance (your real demand data)", "config_key": None, "options": [
        {"label": "GSC service account (RECOMMENDED — live API, auto-snapshots on every cycle)",
         "why": "attribution + learning need snapshots on a cadence; the API never forgets to export",
         "env": [], "note": "save the JSON key here as gsc-credentials.json (auto-detected) + set gsc_property"},
        {"label": "CSV import (fastest — no Google Cloud setup)",
         "why": "60 seconds to working data; you re-export weekly",
         "env": [], "note": "Search Console → Performance → Export → `gsc --csv export.zip`"},
        {"label": "Skip for now", "env": [], "note": "the plan/ledger stay demand-blind until connected"},
    ]},
    {"seam": "Market data (volumes, SERPs, People-Also-Ask)", "config_key": None, "options": [
        {"label": "DataForSEO (RECOMMENDED — volumes + PAA + difficulty, ≈$0.006/SERP, bring-your-own)",
         "why": "briefs, gap analysis, and forecasts feed on volumes + PAA no free source provides",
         "env": ["DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"]},
        {"label": "SearXNG self-hosted (free, open source — organic SERPs only)",
         "why": "zero spend; briefs stay SERP-grounded but lose PAA/volumes/features",
         "env": ["SEARXNG_URL"], "note": "docker run -d -p 8888:8080 searxng/searxng → SEARXNG_URL=http://127.0.0.1:8888"},
        {"label": "Free Google Autocomplete only (zero setup)",
         "why": "keyword ideas with no volumes — the automatic fallback anyway", "env": []},
    ]},
    {"seam": "Writing engine (who writes drafts/strategy)", "config_key": ("llm", "provider"), "options": [
        {"label": "Agent mode (RECOMMENDED inside Claude Code — the driving agent writes; no key)",
         "value": "agent", "why": "frontier-quality writing at no extra cost when Claude drives the skill", "env": []},
        {"label": "Ollama — local open-source model (private, free; for headless cron runs)",
         "value": "ollama", "why": "nothing leaves the machine; good for client-confidential work",
         "env": [], "note": "install ollama.com → `ollama pull llama3.1`"},
        {"label": "Anthropic API (headless cron with frontier quality)",
         "value": "anthropic", "env": ["ANTHROPIC_API_KEY"], "why": "best headless output; per-token cost"},
        {"label": "OpenAI API", "value": "openai", "env": ["OPENAI_API_KEY"], "why": "alternative headless provider"},
    ]},
    {"seam": "Speed lab data (Core Web Vitals)", "config_key": None, "options": [
        {"label": "Lighthouse CLI, local (RECOMMENDED — free, no key, no quota; auto-used when present)",
         "why": "same open-source engine PSI wraps, on your machine",
         "env": [], "note": "npm i -g lighthouse (or have npx)"},
        {"label": "PageSpeed API key (adds CrUX FIELD data — real users, the ranking signal)",
         "why": "lab tells you what to fix; field tells you what Google measures",
         "env": ["PAGESPEED_API_KEY"]},
        {"label": "Skip", "env": []},
    ]},
    {"seam": "Review & alert channel (approvals reach you where you live)", "config_key": None, "options": [
        {"label": "CLI + dashboard (RECOMMENDED to start — zero setup, `serve` approves inline)",
         "why": "everything works locally; add a channel when away-from-desk approvals matter", "env": []},
        {"label": "Slack", "env": ["SLACK_WEBHOOK_URL"]},
        {"label": "Email (send + reply-to-approve)", "env": ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD",
                                                            "IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD"]},
        {"label": "WhatsApp", "env": ["WHATSAPP_TOKEN", "WHATSAPP_PHONE_ID"]},
    ]},
]


def apply_choice(cfg, seam, opt):
    """Write a chosen option's config value; return the .env lines it still needs.
    (Pure — the interactive loop and tests both use it.)"""
    ck = seam.get("config_key")
    if ck and opt.get("value") is not None:
        cur = cfg
        for part in ck[:-1]:
            cur = cur.setdefault(part, {})
        cur[ck[-1]] = opt["value"]
    todo = [f"{e}=" for e in opt.get("env", [])]
    return cfg, todo


def interactive(cfg, root=".", config_path="config.json"):
    """Terminal 'modals' — collect the essentials and write them into config.json."""
    import json
    import sys
    if not sys.stdin.isatty():
        return {"error": "not a TTY — run in a terminal, or let the agent ask these questions"}
    print("\n=== SEO pipeline — guided setup ===\n")
    ask = lambda q, d="": (input(f"{q}" + (f" [{d}]" if d else "") + ": ").strip() or d)
    from . import cms_extra
    site = ask("Site URL", cfg.get("site", ""))
    comps = ask("Competitor domains (comma-separated)", ",".join(cfg.get("competitors", [])))
    cms_t = ask("CMS (" + "/".join(cms_extra.REQUIREMENTS) + ")",
                (cfg.get("cms", {}) or {}).get("type", "file")).lower()
    emails = ask("Email PDF reports to (comma-separated, optional)")
    drive = ask("Google Drive folder id for deliverables (optional)")
    share = ask("Share anonymized change-type stats across your workspaces so every site "
                "learns from the others? Only 'change type × lift' aggregates, domain hashed — "
                "no URLs/content/domains [y/N]").lower().startswith("y")
    auton = ask("Autonomy [manual/approve/auto]", cfg.get("autonomy") if isinstance(cfg.get("autonomy"), str) else "manual")
    cfg["site"] = site.rstrip("/")
    cfg["sitemap"] = cfg.get("sitemap") or site.rstrip("/") + "/sitemap.xml"
    cfg["competitors"] = [c.strip() for c in comps.split(",") if c.strip()]
    cfg["autonomy"] = auton
    if cms_t in cms_extra.REQUIREMENTS:
        cfg.setdefault("cms", {})["type"] = cms_t
    if emails:
        cfg.setdefault("report", {})["email_to"] = [e.strip() for e in emails.split(",") if e.strip()]
    if drive:
        cfg.setdefault("drive", {})["folder_id"] = drive.strip()
    cfg.setdefault("learning", {})["share_cross_site"] = share

    # provider choices — one seam at a time, recommended first, trade-offs stated
    print("\n=== Pick your providers (Enter = the recommended option) ===")
    env_todo, notes = [], []
    for seam in CHOICES:
        print(f"\n{seam['seam']}")
        for i, o in enumerate(seam["options"], 1):
            print(f"  {i}. {o['label']}")
            if o.get("why"):
                print(f"     ↳ {o['why']}")
        pick = ask("Choice", "1")
        try:
            opt = seam["options"][max(0, min(len(seam["options"]) - 1, int(pick) - 1))]
        except ValueError:
            opt = seam["options"][0]
        cfg, todo = apply_choice(cfg, seam, opt)
        env_todo += todo
        if opt.get("note"):
            notes.append(f"{seam['seam'].split(' (')[0]}: {opt['note']}")
    from . import config as _cfgmod
    Path(config_path).write_text(json.dumps(_cfgmod.persistable(cfg), indent=2) + "\n")  # SEC-M6: no env creds on disk
    if env_todo:
        print("\n── Add to .env (git-ignored — never share these): "
              + " ".join(dict.fromkeys(env_todo)))
    for n in notes:
        print(f"  → {n}")

    # the interview (Hermes-style user modeling): 6 questions → CLIENT.md + brain seeds,
    # so the strategist/writer know the BUSINESS on day one. Enter skips any question.
    from . import identity
    print("\n=== The interview — 2 minutes that make every draft business-aware (Enter skips) ===")
    answers = {}
    for key, q in identity.INTERVIEW:
        answers[key] = ask(q)
    ci = identity.write_client(cfg, answers)
    if ci.get("ok"):
        print(f"  ✓ CLIENT.md written ({ci['answered']} answers) — seeded into the brain; "
              "edit the file any time")
    identity.scaffold(cfg)
    req = cms_extra.requirements(cms_t) or {}
    if req.get("env") or req.get("config"):
        print(f"\n  {req['name']}: add {', '.join(req['env']) or 'nothing'} to .env (git-ignored)"
              + (f"; set {', '.join(req['config'])} in config.json" if req.get("config") else "")
              + f"\n  docs: {req['docs']}")
    if "manual" in req:
        print(f"\n  {req['name']}: {req['manual']}")
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
