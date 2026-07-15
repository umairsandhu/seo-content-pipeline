"""Layer 1 — Observe (goal #8). Emerging-keyword detection. Expand seeds via
DataForSEO suggestions, then flag two kinds of "rising":
  (a) keywords newly appearing vs the last trends snapshot (needs ≥2 runs), and
  (b) keywords whose Google Trends interest curve is sloping up.
Each run is persisted to history so "new since last month" is computable."""
from . import history, providers


def scan(cfg, seeds, limit=60):
    dfs = cfg.get("dataforseo", {})
    found = {}
    for seed in seeds:
        for r in providers.suggestions(seed, dfs.get("location_name"),
                                       dfs.get("language_name"), limit):
            found.setdefault(r["keyword"], r)
    curr = list(found.values())

    prev = history.latest(cfg, "trends")
    prev_kws = {r["keyword"] for r in prev["data"]} if prev else None
    for r in curr:
        r["emerging"] = (r["keyword"] not in prev_kws) if prev_kws is not None else None

    top = sorted(curr, key=lambda r: -(r.get("volume") or 0))[:20]
    tr = providers.google_trends([r["keyword"] for r in top],
                                 dfs.get("location_name"), dfs.get("language_name"))
    for r in curr:
        r["trend"] = tr.get(r["keyword"], {}).get("trend")

    history.snapshot(cfg, "trends", curr)
    rising = [r for r in curr if r.get("emerging") or r.get("trend") == "rising"]
    rising.sort(key=lambda r: -(r.get("volume") or 0))
    return {"all": curr, "rising": rising}
