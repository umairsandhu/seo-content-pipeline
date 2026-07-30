"""CLI: python -m seo_agent <cmd> --config config.json

Onboard   init · safety · integrations · onboard   bootstrap → fork-safe → baseline
Doctor    audit · geo · sitemap · speed · logs · schema · eeat · authority · report · llmstxt
Observe   ingest · gsc · rank · trends · backlinks · toxicity
Decide    research · discover · gap · aio · consolidate · inlinks · autolink · decay · algo · radar
Produce   analyze · brief · draft · score · retitle
Plan      plan                          ranked "what to do next" (the co-pilot)
Publish   publish · mcp
Run       run [--monthly]              full orchestration → digest.md
"""
import argparse
import json
import sys
from pathlib import Path

from . import (aio, aivis, algo, analyze, anomaly, audit, authority, authority_flow, autonomy,
               autopilot, backlinks, brain, channels, citability, cms_extra, competitors, consult,
               content_score, crew, ctr_curves, decay, deliver as deliver_mod, eeat, edition, entity,
               ga4, geo, gsc_csv, history, ingest,
               integrations, internal, intl, jobs, journey, learn, local, logs, mcp_server, notify, onboard,
               orchestrate, plan, produce, projects, prospect, publish, review, serve as serve_mod,
               explain as explain_mod, ledger, radar, rank, refresh, remediate, render, repo, report,
               safety, safetygate, schema, site_control, speed, trends, webagent, wizard)
from . import config as cfgmod
from .index import Index, load_corpus


def main():
    ap = argparse.ArgumentParser(prog="seo-content-pipeline")
    ap.add_argument("--config", default="config.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest")
    pg = sub.add_parser("gsc"); pg.add_argument("--csv", nargs="+", metavar="PATH",
        help="import GSC CSV export(s) instead of the API (Queries.csv, Pages.csv, a dir, or a .zip)")
    sub.add_parser("decay")
    sub.add_parser("algo")
    sub.add_parser("radar")
    sub.add_parser("backlinks")
    sub.add_parser("audit").add_argument("--fix", action="store_true", help="also emit the remediation plan (PR-ready)")
    sub.add_parser("speed")
    sub.add_parser("sitemap")
    sub.add_parser("gap")
    sub.add_parser("aio")
    sub.add_parser("rank")
    sub.add_parser("plan")
    sub.add_parser("eeat")
    sub.add_parser("authority")
    sub.add_parser("geo")
    sub.add_parser("autolink")
    prep = sub.add_parser("report"); prep.add_argument("--pdf", action="store_true", help="also render report.pdf via headless Chrome/Chromium")
    prep.add_argument("--email", action="store_true", help="email report.pdf to report.email_to")
    sub.add_parser("consolidate")
    sub.add_parser("toxicity")
    pin = sub.add_parser("inlinks"); pin.add_argument("url")
    sub.add_parser("llmstxt")
    # roadmap capabilities
    sub.add_parser("aivis")        # AI-visibility / LLM-citation tracker
    sub.add_parser("entity")       # entity graph + Wikidata + sameAs
    sub.add_parser("citability")   # passage-citability for AI answers
    sub.add_parser("ctr")          # first-party CTR curve
    sub.add_parser("pagerank")     # internal authority-flow (PageRank)
    sub.add_parser("intl")         # hreflang / international
    sub.add_parser("local")        # local SEO (NAP + LocalBusiness)
    sub.add_parser("prospect")     # link-acquisition prospects
    sub.add_parser("remediate")    # ordered remediation plan
    sub.add_parser("jobs")         # durable job queue
    sub.add_parser("refresh").add_argument("url")
    sub.add_parser("renderdiff").add_argument("url")
    sub.add_parser("gate").add_argument("post_json", help="draft JSON to check against the safety gate")
    pj = sub.add_parser("projects"); pj.add_argument("action", nargs="?", choices=["list", "add"], default="list")
    pj.add_argument("name", nargs="?"); pj.add_argument("directory", nargs="?")
    # expert / control / delivery layer
    sub.add_parser("consult")                                    # McKinsey-level strategy report
    pcr = sub.add_parser("crew"); pcr.add_argument("kind", choices=["article", "change"])
    pcr.add_argument("target")                                   # keyword or change goal
    pw = sub.add_parser("wizard"); pw.add_argument("--interactive", action="store_true")
    sub.add_parser("autonomy")                                   # show mode + pending approvals
    sub.add_parser("apply").add_argument("--approved", action="store_true")  # execute approval queue
    sub.add_parser("control").add_argument("change_json", help="a change JSON: {op, ...}")
    sub.add_parser("pr").add_argument("edits_json", help="repo PR JSON: {title, edits:[{file, edits:[...], desc, url}]}")
    sub.add_parser("ledger")                                     # change log + causal attribution
    sub.add_parser("explain").add_argument("url")               # why did this page change?
    sub.add_parser("learn").add_argument("--notify", action="store_true")  # what worked best (day/week/month) + cross-site
    pbr = sub.add_parser("brain")  # continuous self-learning memory (taste/playbooks/lessons)
    pbr.add_argument("--add", metavar="TEXT"); pbr.add_argument("--kind", default="fact",
                     choices=["fact", "lesson", "preference", "playbook"])
    sub.add_parser("cms")  # every CMS connector + its env/config requirements
    pdl = sub.add_parser("deliver"); pdl.add_argument("files", nargs="*", default=["report.pdf"])
    pdl.add_argument("--note", default="")   # email + Google Drive delivery to the client
    pfb = sub.add_parser("feedback"); pfb.add_argument("text")
    pfb.add_argument("--about", default="")  # client's reaction → taste → future output
    # human review across channels + connectors
    sub.add_parser("review").add_argument("--poll", action="store_true")
    sub.add_parser("approve").add_argument("id", type=int)
    pch = sub.add_parser("changes"); pch.add_argument("id", type=int); pch.add_argument("feedback")
    sub.add_parser("ga4")
    sub.add_parser("competitors")
    sub.add_parser("anomaly").add_argument("--alert", action="store_true")
    # autonomous loop + local dashboard
    pap = sub.add_parser("autopilot")
    pap.add_argument("--daily", action="store_true"); pap.add_argument("--weekly", action="store_true")
    pap.add_argument("--monthly", action="store_true"); pap.add_argument("--no-deliver", action="store_true")
    psrv = sub.add_parser("serve"); psrv.add_argument("--port", type=int, default=8787)
    psrv.add_argument("--no-open", action="store_true", help="don't auto-open the browser")
    pst = sub.add_parser("start")  # THE hand-held entry: status → guided web dashboard
    pst.add_argument("--port", type=int, default=8787); pst.add_argument("--no-open", action="store_true")
    sub.add_parser("practices")   # best practices learned + applied here, with numbers
    sub.add_parser("demo").add_argument("--dir", default="seo-demo")  # 5-min zero-key demo workspace
    pcf = sub.add_parser("config")  # show every setting slot + what's filled; --fix adds missing slots
    pcf.add_argument("--fix", action="store_true", help="add any missing slots to config.json (values kept)")
    sub.add_parser("edition")   # show edition + entitlements
    sub.add_parser("webtask").add_argument("task_json", help="a web task JSON: {name, steps:[...]}")
    pe = sub.add_parser("email"); pe.add_argument("--pdf", default="report.pdf")
    sub.add_parser("integrations")
    sub.add_parser("mcp")
    pl = sub.add_parser("logs"); pl.add_argument("path", nargs="?"); pl.add_argument("--verify", action="store_true")
    psc = sub.add_parser("schema"); psc.add_argument("url", nargs="?")
    pcs = sub.add_parser("score"); pcs.add_argument("keyword"); pcs.add_argument("url")
    sf = sub.add_parser("safety"); sf.add_argument("--precommit", action="store_true")
    pin2 = sub.add_parser("init"); pin2.add_argument("--site")
    sub.add_parser("preflight")   # onboarding readiness gate (no baseline)
    po = sub.add_parser("onboard"); po.add_argument("--keywords-file")
    po.add_argument("--degraded", action="store_true",
                    help="proceed even if required accesses (GSC/DataForSEO) are missing")
    sub.add_parser("brief").add_argument("keyword")
    sub.add_parser("draft").add_argument("keyword")
    sub.add_parser("discover").add_argument("seed")
    sub.add_parser("research").add_argument("keywords", nargs="+")
    sub.add_parser("trends").add_argument("seeds", nargs="+")
    pa = sub.add_parser("analyze"); pa.add_argument("--keywords-file")
    pr = sub.add_parser("run"); pr.add_argument("--monthly", action="store_true")
    pr.add_argument("--daily", action="store_true"); pr.add_argument("--email", action="store_true")
    pr.add_argument("--keywords-file")
    pp = sub.add_parser("publish"); pp.add_argument("post_json", help="path to a post JSON file")
    pt = sub.add_parser("retitle"); pt.add_argument("page"); pt.add_argument("--keyword", default="")
    a = ap.parse_args()
    cfg = cfgmod.load(a.config)
    dump = lambda o: print(json.dumps(o, indent=1, ensure_ascii=False))
    kw_file = lambda f: [l.strip() for l in open(f) if l.strip()] if f else []

    if a.cmd == "ingest":
        ingest.build(cfg)
    elif a.cmd == "gsc":
        if a.csv:
            raw = gsc_csv.import_csv(cfg, a.csv)
            print(f"imported GSC CSV → {len(raw['queries'])} queries, {len(raw['pages'])} pages"
                  + (f", {len(raw['pairs'])} query×page pairs" if raw["pairs"] else "")
                  + " (snapshot to history/)")
        else:
            raw = analyze.gsc_raw(cfg)
            if not raw:
                print("GSC not connected. Two ways (pick one):\n"
                      "  1) EASIEST — export from Search Console (Performance → Export) and run:\n"
                      "     python -m seo_agent gsc --csv <export.zip>\n"
                      "  2) API — save your service-account JSON here as gsc-credentials.json\n"
                      "     (auto-detected, git-ignored), set gsc_property in config.json, and share\n"
                      "     the GSC property with the service account's email.\n"
                      "  `preflight` shows exactly which step you're on."); return
            history.snapshot(cfg, "gsc_queries", raw["queries"])
            history.snapshot(cfg, "gsc_pages", raw["pages"])
        dump(analyze.opportunities_from(raw))
    elif a.cmd == "decay":
        dump(decay.detect(cfg))
    elif a.cmd == "algo":
        dump(algo.attribution(cfg) or "need >=2 GSC snapshots (run `gsc` on a cadence)")
    elif a.cmd == "radar":
        dump(radar.check())
    elif a.cmd == "backlinks":
        dump(backlinks.link_gap(cfg) if cfg.get("competitors")
             else backlinks.profile(cfg))
    elif a.cmd == "safety":
        if a.precommit:                       # git pre-commit hook entrypoint
            leaks = safety.scan_tree("."); tracked = safety.tracked_secrets(".")
            if leaks or tracked:
                print("✋ commit blocked — possible secrets:", file=sys.stderr)
                for f, k, _ in leaks:
                    print(f"  {f}: {k}", file=sys.stderr)
                for f in tracked:
                    print(f"  tracked secret/config file: {f}", file=sys.stderr)
                sys.exit(1)
            sys.exit(0)
        dump(safety.check(cfg))
    elif a.cmd == "init":
        r = onboard.init(site=a.site)
        if r.get("error"):
            print(r["error"]); return
        print(f"✓ workspace ready for {r['site']}  ·  fork-safe: {r['fork_safe']}")
        print(f"  config.json ({'created' if r['created_config'] else 'exists'} — every setting has "
              f"a slot + hint), .env ({'created' if r['created_env'] else 'exists'}), .gitignore hardened")
        print("Next: `python -m seo_agent start` — the dashboard opens and walks you through "
              "every remaining step.\n(Prefer text? `wizard` · `config` shows every slot · "
              "`preflight` is the readiness gate.)")
    elif a.cmd == "preflight":
        print(journey.render_md(journey.readiness(cfg)))
    elif a.cmd == "onboard":
        _, md = onboard.run(cfg, kw_file(a.keywords_file), degraded=a.degraded)
        print(md)
    elif a.cmd == "audit":
        rep = audit.report(cfg)
        Path("audit.md").write_text(audit.render_md(cfg, rep))
        print(audit.render_md(cfg, rep))
        if getattr(a, "fix", False):
            print("\n---\n" + remediate.render_md(cfg, remediate.plan(cfg))
                  + "\n\n_Ship each fix with `pr <edits.json>` or `control <change.json>` — "
                    "queued items go through `review` → `apply --approved`._")
    elif a.cmd == "sitemap":
        f = []; info = audit.sitemap_health(cfg, load_corpus(), f)
        dump({"summary": info, "findings": f})
    elif a.cmd == "speed":
        corpus = load_corpus()
        urls = [c.get("final_url") or c["url"] for c in corpus][:8] or [cfg.get("site")]
        dump(speed.check(cfg, urls))
    elif a.cmd == "gap":
        dump(analyze.competitor_gap(cfg, Index(load_corpus())))
    elif a.cmd == "aio":
        opp = analyze.gsc_opportunities(cfg)
        if not opp:
            print("GSC not configured — AIO model re-ranks striking-distance queries."); return
        print(aio.render_md(cfg, aio.annotate(cfg, opp["striking"])))
    elif a.cmd == "rank":
        rows = rank.track(cfg)
        print(rank.render_md(cfg, rows, rank.movement(cfg)))
    elif a.cmd == "plan":
        actions = plan.build(cfg)
        md = plan.render_md(cfg, actions)
        Path("plan.md").write_text(md)
        print(md)
    elif a.cmd == "schema":
        if a.url:
            print(schema.generate(cfg, a.url))
        else:
            m = schema.missing(cfg)
            print(f"{len(m)} indexable pages missing JSON-LD (pass a URL to generate):")
            for u in m[:30]:
                print(" ", u)
    elif a.cmd == "score":
        dump(content_score.score(cfg, a.keyword, a.url))
    elif a.cmd == "eeat":
        print(eeat.render_md(cfg, eeat.report(cfg)))
    elif a.cmd == "authority":
        print(authority.render_md(cfg, authority.clusters(cfg)))
    elif a.cmd == "geo":
        print(geo.render_md(cfg, geo.report(cfg)))
    elif a.cmd == "aivis":
        print(aivis.render_md(cfg, aivis.run(cfg)))
    elif a.cmd == "entity":
        print(entity.render_md(cfg, entity.report(cfg)))
    elif a.cmd == "citability":
        print(citability.render_md(cfg, citability.report(cfg)))
    elif a.cmd == "ctr":
        print(ctr_curves.render_md(cfg))
    elif a.cmd == "pagerank":
        print(authority_flow.render_md(cfg, authority_flow.report(cfg)))
    elif a.cmd == "intl":
        print(intl.render_md(cfg, intl.report(cfg)))
    elif a.cmd == "local":
        print(local.render_md(cfg, local.report(cfg)))
    elif a.cmd == "refresh":
        print(refresh.render_md(cfg, refresh.packet(cfg, a.url)))
    elif a.cmd == "prospect":
        print(prospect.render_md(cfg, prospect.run(cfg)))
    elif a.cmd == "renderdiff":
        print(render.render_md(cfg, render.diff(cfg, a.url)))
    elif a.cmd == "remediate":
        print(remediate.render_md(cfg, remediate.plan(cfg)))
    elif a.cmd == "gate":
        post = json.load(open(a.post_json))
        print(safetygate.render_md(safetygate.check(
            {"title": post.get("title", ""), "text": post.get("body") or post.get("markdown", "")})))
    elif a.cmd == "jobs":
        print(jobs.render_md(cfg))
    elif a.cmd == "projects":
        if a.action == "add":
            projects.add(a.name, a.directory); print(f"added project {a.name}")
            cap = edition.workspace_cap(cfg)
            n = len(projects._load()["projects"])
            if n > cap:
                print(f"⚠ {n} sites on the {edition.edition(cfg).title()} edition (cap {cap}). "
                      "Upgrade for more — see docs/PRICING.md.")
        print(projects.render_md())
    elif a.cmd == "consult":
        print(consult.render_md(cfg, consult.run(cfg)))
    elif a.cmd == "crew":
        p = crew.article(cfg, a.target) if a.kind == "article" else crew.change(cfg, a.target)
        print(crew.render_md(cfg, p))
    elif a.cmd == "wizard":
        if a.interactive:
            wizard.interactive(cfg)
        print(wizard.render_md(cfg, wizard.next_step(cfg)))
    elif a.cmd == "autonomy":
        print(autonomy.render_md(cfg))
    elif a.cmd == "apply":
        if a.approved:
            dump(site_control.apply_approved(cfg))
        else:
            print(autonomy.render_md(cfg))
    elif a.cmd == "control":
        ch = json.load(open(a.change_json))
        print(site_control.render_md(cfg, site_control.change(cfg, ch.pop("op"), **ch)))
    elif a.cmd == "pr":
        spec = json.load(open(a.edits_json))
        print(repo.render_md(cfg, repo.open_pr(cfg, spec["title"], spec["edits"])))
    elif a.cmd == "ledger":
        print(ledger.render_md(cfg))
    elif a.cmd == "explain":
        print(explain_mod.render_md(cfg, explain_mod.explain(cfg, a.url)))
    elif a.cmd == "learn":
        print(learn.render_md(cfg))
        if a.notify:
            dump(learn.notify(cfg))
    elif a.cmd == "brain":
        if a.add:
            dump(brain.add(cfg, a.kind, a.add, source="manual"))
        print(brain.render_md(cfg))
    elif a.cmd == "cms":
        print(cms_extra.render_md(cfg))
    elif a.cmd == "deliver":
        print(deliver_mod.render_md(cfg, deliver_mod.deliver(cfg, a.files, note=a.note)))
    elif a.cmd == "feedback":
        dump(deliver_mod.feedback(cfg, a.text, about=a.about))
    elif a.cmd == "review":
        if a.poll:
            dump(review.poll(cfg))
        else:
            dump(review.request(cfg))
        print(review.status_md(cfg))
    elif a.cmd == "approve":
        dump(review.respond(cfg, a.id, "approve"))
    elif a.cmd == "changes":
        dump(review.respond(cfg, a.id, "changes", a.feedback))
    elif a.cmd == "ga4":
        print(ga4.render_md(cfg, ga4.organic(cfg)))
    elif a.cmd == "competitors":
        print(competitors.render_md(cfg, competitors.delta(cfg)))
    elif a.cmd == "anomaly":
        res = anomaly.alert(cfg) if a.alert else {"alerts": anomaly.detect(cfg)}
        print(anomaly.render_md(cfg, res["alerts"]))
    elif a.cmd == "autopilot":
        cad = "monthly" if a.monthly else "weekly" if a.weekly else "daily"
        print(autopilot.render_md(cfg, autopilot.cycle(cfg, cadence=cad, deliver=not a.no_deliver)))
    elif a.cmd == "serve":
        serve_mod.serve(cfg, port=a.port, open_browser=not a.no_open)
    elif a.cmd == "start":
        # hand-held entry point: show where you are, then open the guided dashboard
        if not (cfg.get("site") or "").strip() or "example.com" in cfg.get("site", ""):
            print("No site configured here yet. In an EMPTY folder (one per site), run:\n"
                  "  python -m seo_agent init --site https://your-site.com\n"
                  "  python -m seo_agent start\n"
                  "The dashboard opens and walks you through every remaining step.")
            return
        print(wizard.render_md(cfg, wizard.next_step(cfg)))
        print("\nOpening the dashboard — it shows these steps, what's done, best practices "
              "learned, and every document to review…")
        serve_mod.serve(cfg, port=a.port, open_browser=not a.no_open)
    elif a.cmd == "practices":
        from . import practices
        print(practices.render_md(cfg))
    elif a.cmd == "demo":
        from . import demo
        print(demo.render_md(demo.build(a.dir)))
    elif a.cmd == "config":
        if a.fix:
            added = cfgmod.ensure_keys(a.config)
            print(("added slots: " + ", ".join(added)) if added else "all slots already present",
                  "→ " + a.config)
        raw = json.load(open(a.config)) if Path(a.config).exists() else {}

        def _filled(v):  # a slot counts as filled when SOMETHING non-placeholder is in it
            if isinstance(v, dict):
                return any(_filled(x) for x in v.values())
            if isinstance(v, (list, tuple)):
                return len(v) > 0
            return bool(v) and "example.com" not in str(v)

        print(f"# config — {a.config}\n")
        for k, hint in cfgmod.HINTS.items():
            if k.startswith("_"):
                continue
            v = raw.get(k)
            slot = "" if k in raw else "  (no slot yet — run `config --fix`)"
            print(f"{'✅' if _filled(v) else '⬜'} {k}: {json.dumps(v) if k in raw else '—'}{slot}\n     ↳ {hint}")
        print("\nSecrets live in .env (never here). `wizard` fills the essentials interactively.")
    elif a.cmd == "edition":
        print(edition.render_md(cfg))
    elif a.cmd == "webtask":
        print(webagent.render_md(cfg, webagent.run_task(cfg, json.load(open(a.task_json)))))
    elif a.cmd == "email":
        print(notify.render_md(cfg, notify.email_report(cfg, a.pdf)))
    elif a.cmd == "autolink":
        print(internal.render_link_plan(cfg, internal.link_plan(cfg)))
    elif a.cmd == "report":
        html = report.build(cfg)
        print("wrote " + html + " — open it in a browser")
        pdf = None
        if a.pdf or a.email:
            pdf, err = report.to_pdf(html)
            print("wrote " + pdf if pdf else "PDF skipped — " + err)
        if a.email:
            print(notify.render_md(cfg, notify.email_report(cfg, pdf or html)))
    elif a.cmd == "consolidate":
        print(internal.render_md(cfg, internal.consolidation(cfg)))
    elif a.cmd == "toxicity":
        dump(backlinks.toxicity(cfg))
    elif a.cmd == "inlinks":
        dump(internal.inbound_suggestions(cfg, a.url))
    elif a.cmd == "logs":
        path = a.path or cfg.get("logs", {}).get("path")
        if not path:
            print("usage: logs <access.log[.gz]>  (or set logs.path in config)"); return
        print(logs.render_md(cfg, logs.analyze(cfg, path, verify=a.verify)))
    elif a.cmd == "integrations":
        print(integrations.render_md(cfg))
    elif a.cmd == "llmstxt":
        print(audit.llms_txt_template(cfg))
    elif a.cmd == "research":
        dump(analyze.content_gaps(Index(load_corpus()), a.keywords, cfg))
    elif a.cmd == "discover":
        rows = analyze.discover(a.seed, cfg)
        if not rows:
            print("no results (need DataForSEO creds)")
        for r in rows:
            print(f"{(r['volume'] if r['volume'] is not None else '—'):>7}  {r['keyword']}")
    elif a.cmd == "trends":
        dump(trends.scan(cfg, a.seeds))
    elif a.cmd == "brief":
        dump(produce.brief(cfg, a.keyword))
    elif a.cmd == "draft":
        d = produce.draft(cfg, a.keyword)
        # mode "agent" prints the writing packet for the agent to author from;
        # mode "generated" (headless llm.provider set) prints the finished draft.
        print(d["markdown"] if d["mode"] == "generated" else d["assignment"])
    elif a.cmd == "retitle":
        r = produce.retitle(cfg, a.page, keyword=a.keyword)
        print(r["suggestions"] if r["mode"] == "generated" else r["task"])
    elif a.cmd == "analyze":
        _, rep = analyze.report(cfg, kw_file(a.keywords_file))
        md = analyze.render_md(cfg, rep)
        Path("recommendations.md").write_text(md)
        print(md)
    elif a.cmd == "run":
        _, md = orchestrate.run(cfg, kw_file(a.keywords_file), monthly=a.monthly,
                                daily=a.daily, email=a.email)
        print(md)
    elif a.cmd == "publish":
        dump(publish.publish(cfg, json.load(open(a.post_json))))
    elif a.cmd == "mcp":
        mcp_server.serve()


if __name__ == "__main__":
    main()
