"""CLI: python -m seo_agent <cmd> --config config.json

  ingest                  crawl the site's sitemap → corpus.json
  discover <seed>         DataForSEO keyword ideas for a seed (trend/gap pull)
  research <kw> [kw…]     enrich keywords + dedup gate + link targets
  gsc                     GSC striking-distance + low-CTR opportunities
  analyze [--keywords-file f]   full report → recommendations.md
  brief <keyword>         live SERP for a keyword (outline input)
"""
import argparse
import json
from pathlib import Path

from . import analyze, ingest, providers
from . import config as cfgmod
from .index import Index, load_corpus


def main():
    ap = argparse.ArgumentParser(prog="seo-content-pipeline")
    ap.add_argument("--config", default="config.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest")
    sub.add_parser("gsc")
    pr = sub.add_parser("research"); pr.add_argument("keywords", nargs="+")
    pd = sub.add_parser("discover"); pd.add_argument("seed")
    pa = sub.add_parser("analyze"); pa.add_argument("--keywords-file")
    pb = sub.add_parser("brief"); pb.add_argument("keyword")
    a = ap.parse_args()
    cfg = cfgmod.load(a.config)
    dfs = cfg.get("dataforseo", {})

    if a.cmd == "ingest":
        ingest.build(cfg)
    elif a.cmd == "research":
        g = analyze.content_gaps(Index(load_corpus()), a.keywords, cfg)
        print(json.dumps(g, indent=1, ensure_ascii=False))
    elif a.cmd == "discover":
        rows = analyze.discover(a.seed, cfg)
        if not rows:
            print("no results (need DataForSEO creds)")
        for r in rows:
            print(f"{(r['volume'] if r['volume'] is not None else '—'):>7}  {r['keyword']}")
    elif a.cmd == "gsc":
        opp = analyze.gsc_opportunities(cfg)
        print(json.dumps(opp, indent=1, ensure_ascii=False) if opp
              else "GSC not configured — set gsc_property + gsc_credentials.")
    elif a.cmd == "analyze":
        kws = [l.strip() for l in open(a.keywords_file)] if a.keywords_file else []
        kws = [k for k in kws if k]
        _, rep = analyze.report(cfg, kws)
        md = analyze.render_md(cfg, rep)
        Path("recommendations.md").write_text(md)
        print(md)
    elif a.cmd == "brief":
        print(json.dumps(providers.serp(a.keyword, dfs.get("location_name"),
                                        dfs.get("language_name")), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
