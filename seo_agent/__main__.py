"""CLI: python -m seo_agent <cmd> --config config.json

Onboard   init · safety · integrations · onboard   bootstrap → fork-safe → baseline
Doctor    audit · sitemap · speed · logs · schema · eeat · authority · llmstxt
Observe   ingest · gsc · rank · trends · backlinks · toxicity
Decide    research · discover · gap · aio · consolidate · inlinks · decay · algo · radar
Produce   analyze · brief · draft · score · retitle
Plan      plan                          ranked "what to do next" (the co-pilot)
Publish   publish · mcp
Run       run [--monthly]              full orchestration → digest.md
"""
import argparse
import json
import sys
from pathlib import Path

from . import (aio, algo, analyze, audit, authority, backlinks, content_score, decay,
               eeat, history, ingest, integrations, internal, logs, mcp_server, onboard,
               orchestrate, plan, produce, publish, radar, rank, safety, schema, speed,
               trends)
from . import config as cfgmod
from .index import Index, load_corpus


def main():
    ap = argparse.ArgumentParser(prog="seo-content-pipeline")
    ap.add_argument("--config", default="config.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest")
    sub.add_parser("gsc")
    sub.add_parser("decay")
    sub.add_parser("algo")
    sub.add_parser("radar")
    sub.add_parser("backlinks")
    sub.add_parser("audit")
    sub.add_parser("speed")
    sub.add_parser("sitemap")
    sub.add_parser("gap")
    sub.add_parser("aio")
    sub.add_parser("rank")
    sub.add_parser("plan")
    sub.add_parser("eeat")
    sub.add_parser("authority")
    sub.add_parser("consolidate")
    sub.add_parser("toxicity")
    pin = sub.add_parser("inlinks"); pin.add_argument("url")
    sub.add_parser("llmstxt")
    sub.add_parser("integrations")
    sub.add_parser("mcp")
    pl = sub.add_parser("logs"); pl.add_argument("path", nargs="?"); pl.add_argument("--verify", action="store_true")
    psc = sub.add_parser("schema"); psc.add_argument("url", nargs="?")
    pcs = sub.add_parser("score"); pcs.add_argument("keyword"); pcs.add_argument("url")
    sf = sub.add_parser("safety"); sf.add_argument("--precommit", action="store_true")
    pin2 = sub.add_parser("init"); pin2.add_argument("--site")
    po = sub.add_parser("onboard"); po.add_argument("--keywords-file")
    sub.add_parser("brief").add_argument("keyword")
    sub.add_parser("draft").add_argument("keyword")
    sub.add_parser("discover").add_argument("seed")
    sub.add_parser("research").add_argument("keywords", nargs="+")
    sub.add_parser("trends").add_argument("seeds", nargs="+")
    pa = sub.add_parser("analyze"); pa.add_argument("--keywords-file")
    pr = sub.add_parser("run"); pr.add_argument("--monthly", action="store_true")
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
        raw = analyze.gsc_raw(cfg)
        if not raw:
            print("GSC not configured — set gsc_property + gsc_credentials."); return
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
        print(f"  config.json ({'created' if r['created_config'] else 'exists'}), "
              f".env ({'created' if r['created_env'] else 'exists'}), .gitignore hardened")
        print("Next: edit config.json (site · competitors), add any keys to .env, then "
              "`python -m seo_agent onboard`. See PLAYBOOK.md for the 0→100 path.")
    elif a.cmd == "onboard":
        _, md = onboard.run(cfg, kw_file(a.keywords_file))
        print(md)
    elif a.cmd == "audit":
        rep = audit.report(cfg)
        Path("audit.md").write_text(audit.render_md(cfg, rep))
        print(audit.render_md(cfg, rep))
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
        _, md = orchestrate.run(cfg, kw_file(a.keywords_file), monthly=a.monthly)
        print(md)
    elif a.cmd == "publish":
        dump(publish.publish(cfg, json.load(open(a.post_json))))
    elif a.cmd == "mcp":
        mcp_server.serve()


if __name__ == "__main__":
    main()
