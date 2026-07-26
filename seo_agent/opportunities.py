"""Data-driven opportunity discovery — the "plan on the basis of data" engine.

Expands seed themes into keyword candidates (DataForSEO suggestions), dedupes
near-identical phrasings, pulls REAL keyword difficulty (organic ease-of-ranking),
drops anything the site already covers (the Stage-2 dedup gate), scores by
volume × ease, maps each to a pillar, and (optional) tags trend direction. Output:
a ranked opportunities.json + a printed table.

Self-contained DataForSEO calls (doesn't depend on other provider edits). Reads
DATAFORSEO_LOGIN/PASSWORD from env or a local .env.local.

  python -m seo_agent.opportunities                       # uses config seeds
  python -m seo_agent.opportunities "seed one" "seed two" # ad-hoc seeds
"""
import base64
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from . import config as cfgmod
from .index import Index, load_corpus

STOP = set("in the for of a to and best top how buy from with your me is".split())
# Sensible defaults if config.seed_sets is absent. Group = intent bucket.
DEFAULT_SEED_SETS = {
    "core": [],           # fill from config or CLI
}


def _load_env():
    for f in (Path(".env.local"), Path(__file__).resolve().parent.parent / ".env.local"):
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _auth():
    _load_env()
    lo, pw = os.environ.get("DATAFORSEO_LOGIN"), os.environ.get("DATAFORSEO_PASSWORD")
    return base64.b64encode(f"{lo}:{pw}".encode()).decode() if lo and pw else None


def _post(path, payload, cost, timeout=60):
    auth = _auth()
    if not auth:
        return None
    req = urllib.request.Request("https://api.dataforseo.com/v3/" + path,
                                 data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=timeout))
        cost[0] += r.get("cost") or 0
        return r
    except Exception as e:
        print(f"  ! DataForSEO {path}: {e}", file=sys.stderr)
        return None


def _items(res):
    return ((res.get("tasks") or [{}])[0].get("result") or [{}])[0].get("items") or [] if res else []


def _key(kw):
    return frozenset(w for w in re.findall(r"[a-z0-9]+", kw.lower()) if w not in STOP)


def _pillar(kw, pillars):
    k = kw.lower()
    for path in pillars:
        if path.strip("/").split("/")[0] in k:
            return path
    return next(iter(pillars), "/") if pillars else "/"


def discover(cfg, seeds, max_cost=0.85, min_vol=100, per_seed=35, with_trends=True):
    dfs = cfg.get("dataforseo", {})
    loc, lang = dfs.get("location_name"), dfs.get("language_name")
    cost = [0.0]
    pool = {}
    for s in seeds:
        if cost[0] > max_cost * 0.65:
            print(f"  (stopping seed expansion at ${cost[0]:.2f})")
            break
        for it in _items(_post("dataforseo_labs/google/keyword_suggestions/live",
                               [{"keyword": s, "location_name": loc, "language_name": lang, "limit": per_seed}], cost)):
            kw = it.get("keyword")
            v = (it.get("keyword_info") or {}).get("search_volume") or 0
            if kw and (kw not in pool or v > pool[kw]):
                pool[kw] = v
        time.sleep(0.25)

    # dedupe near-identical phrasings → highest-volume representative
    groups = {}
    for kw, v in pool.items():
        if v >= min_vol:
            groups.setdefault(_key(kw), []).append((v, kw))
    cands = [max(g)[::-1] for g in groups.values()]

    # gap gate against the site's own corpus
    idx = Index(load_corpus())
    gap = [(kw, v) for kw, v in cands if idx.check_topic(kw)[0] != "EXTEND"]

    # real keyword difficulty
    kd = {}
    for i in range(0, len(gap), 100):
        for it in _items(_post("dataforseo_labs/google/bulk_keyword_difficulty/live",
                               [{"keywords": [k for k, _ in gap[i:i + 100]], "location_name": loc, "language_name": lang}], cost)):
            kd[it.get("keyword")] = it.get("keyword_difficulty")

    pillars = cfg.get("pillars", {})
    rows = []
    for kw, v in gap:
        d = kd.get(kw)
        d = d if isinstance(d, (int, float)) else 50
        rows.append({"keyword": kw, "volume": v, "difficulty": d,
                     "opportunity": round(v * (100 - d) / 100),
                     "verdict": idx.check_topic(kw)[0], "pillar": _pillar(kw, pillars)})
    rows.sort(key=lambda r: -r["opportunity"])

    if with_trends and rows and cost[0] < max_cost:
        res = _post("keywords_data/google_trends/explore/live",
                    [{"keywords": [r["keyword"] for r in rows[:5]], "location_name": loc,
                      "language_name": lang, "time_range": "past_12_months"}], cost)
        avg = {}
        for it in _items(res):
            for k, a in zip(it.get("keywords") or [], it.get("averages") or []):
                avg[k] = a
        for r in rows:
            r["trend_interest"] = avg.get(r["keyword"])

    return rows, cost[0]


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    cfg = cfgmod.load(os.environ.get("SEO_CONFIG", "config.json"))
    seeds = argv or cfg.get("seeds") or sum((cfg.get("seed_sets") or DEFAULT_SEED_SETS).values(), [])
    if not seeds:
        print("No seeds — pass some on the CLI or set `seeds` / `seed_sets` in config.json.")
        return
    rows, cost = discover(cfg, seeds)
    Path("opportunities.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(f"\n{len(rows)} ranked opportunities · spend ${cost:.2f} · wrote opportunities.json\n")
    print(f"{'opp':>5} {'vol':>5} {'KD':>3} {'trend':>5} {'gate':<8} {'pillar':<16} keyword")
    for r in rows[:30]:
        t = r.get("trend_interest")
        star = " ★" if (r["volume"] >= 250 and r["difficulty"] <= 30) else ""
        print(f"{r['opportunity']:5} {r['volume']:5} {r['difficulty']:3.0f} "
              f"{('' if t is None else t):>5} {r['verdict']:<8} {r['pillar']:<16} {r['keyword']}{star}")


if __name__ == "__main__":
    main()
