"""The onboarding journey — a gated readiness check that every new site must pass
before the baseline runs. It enforces the thing that makes results trustworthy:
one workspace = one site, secrets are safe, and the *right data accesses* are wired
in (or explicitly waived). Nothing here fetches paid data — it only inspects config,
env, the workspace, and the sitemap's reachability.

`readiness(cfg, root)` returns a staged checklist + a verdict. `onboard` calls it
first and refuses to burn time/API budget on a half-configured site; `preflight`
prints it on demand. Reuses `integrations` as the single source of truth for APIs."""
import os
import urllib.request
from pathlib import Path

from . import integrations, safety

# status: ok (green) · warn (amber, recommended-but-missing) · todo (red, required-missing) · skip
_WEIGHT = {"must": 3, "recommended": 2, "optional": 1}


def _sitemap_ok(url):
    if not url:
        return False, "no `sitemap` in config.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 seo-agent"})
        head = urllib.request.urlopen(req, timeout=15).read(4000).decode("utf-8", "ignore").lower()
        if "<urlset" in head or "<sitemapindex" in head:
            return True, "resolves + is valid XML"
        return False, "reachable but not a sitemap (no <urlset>)"
    except Exception as e:
        return False, f"unreachable ({type(e).__name__})"


def _has_gsc_history(cfg):
    d = Path(cfg.get("history_dir", "history")) / "gsc_queries"
    return d.exists() and any(d.glob("*.json"))


def _item(key, label, status, required, detail, how_to="", unlocks=""):
    return {"key": key, "label": label, "status": status, "required": required,
            "detail": detail, "how_to": how_to, "unlocks": unlocks}


def readiness(cfg, root="."):
    root = Path(root).resolve()
    stages = []

    # ── Stage A · Target site ────────────────────────────────────────────────
    A = []
    fresh = not (root / "seo_agent" / "__main__.py").exists()
    A.append(_item("workspace", "Dedicated site workspace", "ok" if fresh else "todo", True,
                   "one workspace = one site" if fresh else "running inside the install dir",
                   "cd to an empty dir and run `init --site https://…` (never the skill's own folder)"))
    site = (cfg.get("site") or "").strip()
    real = bool(site) and "example.com" not in site
    A.append(_item("site", "Target domain set", "ok" if real else "todo", True,
                   site or "unset", "set `site` in config.json to the real domain"))
    sm_ok, sm_detail = _sitemap_ok(cfg.get("sitemap"))
    A.append(_item("sitemap", "Sitemap reachable", "ok" if sm_ok else "todo", True, sm_detail,
                   "set `sitemap` in config.json (check /sitemap.xml or robots.txt)"))
    inc = cfg.get("include") or []
    A.append(_item("include", "Content sections chosen", "ok" if inc else "warn", False,
                   ", ".join(inc) if inc else "empty — will crawl everything",
                   "set `include` (e.g. [\"/blog/\",\"/post/\"]) so analysis targets the right pages",
                   "focused cannibalization / authority / gap analysis"))
    comp = cfg.get("competitors") or []
    A.append(_item("competitors", "Competitors listed", "ok" if comp else "warn", False,
                   ", ".join(comp) if comp else "none",
                   "set `competitors` (domains) in config.json",
                   "content gap, backlink gap, share-of-voice"))
    stages.append({"stage": "A · Target site", "items": A})

    # ── Stage B · Safety (hard gate) ─────────────────────────────────────────
    saf = safety.check(cfg, root=str(root), apply=True)
    stages.append({"stage": "B · Fork-safety", "items": [
        _item("safety", "Secrets safe (gitignore + no tracked keys)",
              "ok" if saf.get("fork_safe") else "todo", True,
              "fork-safe" if saf.get("fork_safe") else "; ".join(saf.get("issues", [])) or "exposed secrets",
              "run `safety` — it hardens .gitignore and writes .env.example")]})

    # ── Stage C · Data & access (the crux) ───────────────────────────────────
    C = []
    mtx = {it["key"]: it for it in integrations.matrix(cfg)}
    # GSC — satisfied by API creds OR an imported CSV/Sheet snapshot in history
    gsc = mtx.get("gsc", {})
    gsc_csv = _has_gsc_history(cfg)
    gsc_ok = gsc.get("active") or gsc_csv
    C.append(_item("gsc", "Search performance (GSC)", "ok" if gsc_ok else "todo", True,
                   "API connected" if gsc.get("active") else ("CSV imported" if gsc_csv else "not connected"),
                   "share a GSC service account (gsc_property + gsc_credentials) OR import an export: "
                   "`gsc --csv <export.zip|dir|Queries.csv>`",
                   "striking-distance, low-CTR, decay, algo attribution"))
    for key in ("dataforseo", "pagespeed", "logs", "render"):
        it = mtx.get(key)
        if not it:
            continue
        required = it["tier"] == "must"
        status = "ok" if it["active"] else ("todo" if required else "warn")
        C.append(_item(key, it["name"], status, required,
                       "active" if it["active"] else "missing: " + ", ".join(it["missing"] or it.get("env", [])),
                       f"set {', '.join(it['missing'] or it.get('env') or it.get('config') or [])}"
                       + (f" · alts: {', '.join(it['options'][:2])}" if it.get("options") else ""),
                       ", ".join(it["unlocks"][:4])))
    stages.append({"stage": "C · Data & access", "items": C})

    # ── Verdict ──────────────────────────────────────────────────────────────
    allitems = [i for s in stages for i in s["items"]]
    required_missing = [i for i in allitems if i["required"] and i["status"] != "ok"]
    # weighted readiness score (required items count triple)
    def w(i):
        if i["key"] in ("workspace", "site", "sitemap", "safety"):
            return 3
        return _WEIGHT.get(mtx.get(i["key"], {}).get("tier", "recommended"), 2)
    got = sum(w(i) * (1 if i["status"] == "ok" else 0.5 if i["status"] == "warn" else 0) for i in allitems)
    tot = sum(w(i) for i in allitems) or 1
    return {"site": site, "stages": stages, "ready": not required_missing,
            "required_missing": [i["label"] for i in required_missing],
            "score": round(100 * got / tot)}


_ICON = {"ok": "✅", "warn": "🟡", "todo": "🔴", "skip": "⬜"}


def render_md(r):
    L = [f"# Onboarding readiness — {r['site'] or '(no site)'}",
         f"**{r['score']}/100 ready** · " + ("🟢 cleared — baseline can run" if r["ready"]
         else "🔴 setup required: " + ", ".join(r["required_missing"])), ""]
    for st in r["stages"]:
        L.append(f"## {st['stage']}")
        for i in st["items"]:
            tag = "" if i["required"] else " _(recommended)_"
            L.append(f"- {_ICON.get(i['status'],'⬜')} **{i['label']}**{tag} — {i['detail']}")
            if i["status"] != "ok" and i["how_to"]:
                L.append(f"    → {i['how_to']}")
            if i["status"] != "ok" and i["unlocks"]:
                L.append(f"    unlocks: {i['unlocks']}")
        L.append("")
    if not r["ready"]:
        L += ["---", "_Resolve the 🔴 required items, then re-run `onboard`. "
              "To proceed anyway in degraded mode: `onboard --degraded`._"]
    return "\n".join(L)
