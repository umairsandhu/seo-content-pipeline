"""Onboarding driver — runs the staged first-time flow and emits BASELINE.md
(the snapshot every later run is measured against). The interactive interview is
the AGENT's job (see ONBOARDING.md); this wires the deterministic stages:

  1. fork-safety (safety.check)   — MUST pass before anything else
  2. ingest                       — build/refresh corpus.json (if missing)
  3. Site Doctor (audit.report)   — technical/on-page audit
  4. speed (Core Web Vitals)      — top pages, if PAGESPEED_API_KEY set
  5. content + gap (analyze)      — GSC + DataForSEO + competitor gap
  6. baseline report

Run: `python -m seo_agent onboard`. Stops with the fork-safety verdict if unsafe."""
import datetime
import json
from pathlib import Path

from . import analyze, audit, integrations, journey, logs, safety, speed
from .index import Index, load_corpus


def init(root=".", site=None):
    """Bootstrap a fresh, site-agnostic workspace so anyone can start from 0 in any
    directory/terminal: scaffold config.json, run fork-safety (.env.example +
    .gitignore + .env), and print next steps. Refuses to run inside the skill's own
    install directory so it never pollutes the shared code. One directory = one site."""
    root = Path(root).resolve()
    if (root / "seo_agent" / "__main__.py").exists():
        return {"error": "Run `init` from YOUR site's workspace directory, not the skill's install dir."}
    cfgp = root / "config.json"
    created_cfg = False
    if not cfgp.exists():
        from . import config as cfgmod
        # every settable key gets a visible slot + a "_hints" how-to — like .env.example
        cfgp.write_text(json.dumps(cfgmod.scaffold(site), indent=2) + "\n")
        created_cfg = True
    saf = safety.check(root=str(root), apply=True)  # .env.example + hardened .gitignore
    try:  # the employee's identity files (SOUL/AGENTS/BOOTSTRAP) — create-only
        from . import identity
        identity.scaffold({"site": site or "", "brand": {}}, root=str(root))
    except Exception:
        pass
    envp, exp = root / ".env", root / ".env.example"
    created_env = False
    if exp.exists() and not envp.exists():
        envp.write_text(exp.read_text())
        created_env = True
    return {"site": site or "https://www.example.com", "config": str(cfgp),
            "created_config": created_cfg, "created_env": created_env, "fork_safe": saf["fork_safe"]}


def run(cfg, keywords=None, root=".", do_ingest=True, out="BASELINE.md", degraded=False):
    stages = {}

    # Gate 0 — onboarding readiness. Every new site must clear the required checks
    # (workspace, target, sitemap, safety, search + market data) before we spend
    # time or API budget. `--degraded` proceeds with whatever is wired in.
    ready = journey.readiness(cfg, root=root)
    stages["readiness"] = ready
    if not ready["ready"] and not degraded:
        md = journey.render_md(ready)
        Path("SETUP.md").write_text(md)
        return stages, md  # halted — resolve required accesses, then re-run

    stages["safety"] = safety.check(cfg, root=root, apply=True)
    if not stages["safety"]["fork_safe"]:
        md = _render(cfg, stages, blocked=True)
        Path(out).write_text(md)
        return stages, md  # do not proceed while secrets are exposed

    stages["integrations"] = {"active": [i["name"] for i in integrations.matrix(cfg) if i["active"]],
                              "missing_required": [i["name"] for i in integrations.missing_required(cfg)]}

    if do_ingest and not Path("corpus.json").exists():
        from . import ingest
        ingest.build(cfg)

    try:
        stages["audit"] = audit.report(cfg)
    except Exception as e:
        stages["audit"] = {"error": f"run `ingest` first ({e})"}

    top = _top_pages(cfg)
    stages["speed"] = speed.check(cfg, top) if top else None
    lp = cfg.get("logs", {}).get("path")
    stages["logs"] = logs.analyze(cfg, lp) if lp else None

    try:
        idx = Index(load_corpus())
        stages["gaps"] = analyze.content_gaps(idx, keywords or [], cfg)
        stages["competitor_gap"] = analyze.competitor_gap(cfg, idx) if cfg.get("competitors") else []
    except Exception:
        stages["gaps"] = []
        stages["competitor_gap"] = []
    stages["gsc"] = analyze.gsc_opportunities(cfg)
    # AI-search baseline (offline, free) — entity + citability readiness
    from . import citability, entity
    try:
        stages["entity"] = entity.report(cfg)
    except Exception:
        stages["entity"] = None
    try:
        stages["citability"] = citability.report(cfg)
    except Exception:
        stages["citability"] = None

    md = _render(cfg, stages, blocked=False)
    Path(out).write_text(md)
    try:  # baseline done → identity files exist, first-run ritual retires itself
        from . import identity
        identity.scaffold(cfg, root=root)
        identity.complete_bootstrap(root=root)
        identity.journal(cfg, ["onboarding baseline complete — probation over; daily rhythm begins"],
                         root=root)
    except Exception:
        pass
    return stages, md


def _top_pages(cfg):
    try:
        corpus = load_corpus()
    except Exception:
        return []
    urls = [c.get("final_url") or c["url"] for c in corpus
            if c.get("status", 200) == 200][:8]
    return urls or ([cfg["site"]] if cfg.get("site") else [])


def _render(cfg, s, blocked):
    site = cfg.get("site", "site")
    L = [f"# SEO onboarding baseline — {site} — {datetime.date.today().isoformat()}", ""]

    sf = s["safety"]
    L += ["## 1. Fork-safety", ("**✅ fork-safe**" if sf["fork_safe"] else "**🔴 NOT fork-safe — fix before committing**")]
    for a in sf["actions"]:
        L.append(f"- did: {a}")
    for i in sf["issues"]:
        L.append(f"- 🔴 {i}")
    L.append("")
    if blocked:
        L.append("_Onboarding halted — resolve the secret exposure above, then re-run `onboard`._")
        return "\n".join(L)

    ig = s.get("integrations")
    if ig:
        L += ["## 1b. Integrations",
              "active: " + (", ".join(ig["active"]) or "none"),
              ("**⚠ missing must-have: " + ", ".join(ig["missing_required"]) + "** — run `integrations` for the full matrix"
               if ig["missing_required"] else "all must-have integrations configured ✅"), ""]

    au = s.get("audit", {})
    if "error" in au:
        L += ["## 2. Site Doctor", f"_{au['error']}_", ""]
    else:
        c = au["counts"]
        L += ["## 2. Site Doctor",
              f"{au['pages']} pages · **{c['high']} high · {c['med']} medium · {c['low']} low** issues · "
              f"orphans {au['links'].get('orphans')} · full detail in `audit.md`", ""]
        for f in sorted(au["findings"], key=lambda f: {"high": 0, "med": 1, "low": 2}[f["sev"]])[:8]:
            L.append(f"- {f['sev'].upper()}: {f['msg']}")
        L.append("")

    sp = s.get("speed")
    if sp:
        L += ["## 3. Core Web Vitals (field p75)"]
        o = sp.get("origin", {})
        v = o.get("verdict", {})
        if v:
            L.append(f"- origin: LCP {v.get('lcp')} · INP {v.get('inp')} · CLS {v.get('cls')}")
        elif not sp.get("has_key"):
            L.append("- _set PAGESPEED_API_KEY for real-user field data (lab-only without it)_")
        L.append("")

    lg = s.get("logs")
    if lg:
        cov = lg.get("ai_coverage") or {}
        L += ["## 3b. Log-file analysis",
              f"- {lg['ai_crawler_total']} AI-crawler hits; "
              f"{cov.get('seen_by_ai','?')}/{cov.get('pages','?')} indexable pages seen by AI bots · "
              f"detail in `logs` output", ""]

    g = s.get("gaps") or []
    if g:
        L += [f"## 4. Content gaps ({len(g)})", "| keyword | vol | verdict |", "|---|--:|---|"]
        L += [f"| {r['keyword']} | {r['volume'] or '—'} | {r['verdict']} |" for r in g[:15]]
        L.append("")
    cg = s.get("competitor_gap") or []
    if cg:
        L += [f"## 4b. Competitor content gap ({len(cg)})", "| keyword | vol | # competitors |", "|---|--:|--:|"]
        L += [f"| {r['keyword']} | {r['volume'] or '—'} | {len(r['competitors'])} |" for r in cg[:15]]
        L.append("")
    gsc = s.get("gsc")
    if gsc:
        L += [f"## 5. GSC striking-distance ({len(gsc['striking'])})", "| query | pos | impr |", "|---|--:|--:|"]
        L += [f"| {r['query']} | {r['position']:.1f} | {r['impressions']} |" for r in gsc["striking"][:10]]
        L.append("")

    en = s.get("entity")
    ci = s.get("citability")
    if en or ci:
        L.append("## 6. AI search / GEO readiness")
        if en:
            wd = ("✅ " + en["wikidata"]["qid"]) if en["wikidata"] else "🔴 none (top GEO fix)"
            L.append(f"- Wikidata entity: {wd} · sameAs profiles: {len(en['sameAs_present'])} · "
                     f"brand salience {en['salience']}")
        if ci:
            L.append(f"- Passage-citability: **{ci['avg']}/100** avg · "
                     f"{ci['missing'].get('answer_first',0)}/{ci['pages']} pages lack an answer-first passage")
        L.append("")

    L += ["## Next",
          "- Run **`plan`** for the ranked next-actions; follow **PLAYBOOK.md** for the 0→100 path.",
          "- Fix Site Doctor **high** items first (crawl/index), then content, then links.",
          "- Turn top gaps into briefs → drafts → PRs (human merge gate).",
          "- Schedule `run` weekly / `run --monthly` monthly to track vs this baseline."]
    return "\n".join(L)
