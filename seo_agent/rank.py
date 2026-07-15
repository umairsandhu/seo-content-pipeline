"""Rank + SERP-feature tracking over time (roadmap #5). Snapshots our position +
which SERP features are present (AI Overview, featured snippet, PAA, video,
shopping, local pack, knowledge graph) per tracked keyword into history, then
diffs run-over-run: who moved up/down, which features you gained or lost.

This is the payoff for wiring DataForSEO/GSC — true longitudinal movement, not a
point-in-time snapshot. Degrades to empty without DataForSEO. Keywords come from
config `rank.keywords`, else the top GSC queries by impressions."""
from . import analyze, history, providers


def _host(url):
    return (url or "").replace("https://", "").replace("http://", "").rstrip("/").split("/")[0]


def _gsc_top_queries(cfg, n=50):
    raw = analyze.gsc_raw(cfg)
    if not raw:
        return []
    q = sorted(raw["queries"], key=lambda r: -r.get("impressions", 0))
    return [r["query"] for r in q[:n]]


def track(cfg, keywords=None):
    dfs = cfg.get("dataforseo", {})
    rc = cfg.get("rank", {})
    host = _host(cfg.get("site"))
    kws = keywords or rc.get("keywords") or _gsc_top_queries(cfg, rc.get("max", 50))
    rows = []
    for kw in kws[: rc.get("max", 50)]:
        s = providers.serp(kw, dfs.get("location_name"), dfs.get("language_name"), depth=20)
        org = s.get("organic", [])
        pos = next((i + 1 for i, o in enumerate(org) if host and host in (o.get("url") or "")), None)
        rows.append({"keyword": kw, "position": pos, "features": s.get("features", {})})
    history.snapshot(cfg, "rank", rows)
    return rows


def movement(cfg):
    prev, curr = history.previous(cfg, "rank"), history.latest(cfg, "rank")
    if not (prev and curr):
        return None
    pv = {r["keyword"]: r for r in prev["data"]}
    moved, feats = [], []
    for r in curr["data"]:
        p = pv.get(r["keyword"])
        if not p:
            continue
        a, b = p.get("position"), r.get("position")
        if a and b and a != b:
            moved.append({"keyword": r["keyword"], "prev": a, "curr": b, "delta": b - a})  # neg = improved
        rf, pf = r.get("features", {}), p.get("features", {})
        gained = [f for f, v in rf.items() if v and not pf.get(f)]
        lost = [f for f, v in pf.items() if v and not rf.get(f)]
        if gained or lost:
            feats.append({"keyword": r["keyword"], "gained": gained, "lost": lost})
    moved.sort(key=lambda m: m["delta"])
    return {"moved": moved, "features": feats}


def render_md(cfg, rows, mv):
    L = [f"# Rank + SERP features — {cfg.get('site','site')}", "",
         "| keyword | pos | AIO | snippet | PAA | video | shopping |", "|---|--:|:--:|:--:|:--:|:--:|:--:|"]
    for r in sorted(rows, key=lambda r: (r["position"] is None, r["position"] or 99))[:40]:
        f = r.get("features", {})
        y = lambda k: "•" if f.get(k) else ""
        L.append(f"| {r['keyword']} | {r['position'] or '—'} | {y('ai_overview')} | "
                 f"{y('featured_snippet')} | {y('people_also_ask')} | {y('video')} | {y('shopping')} |")
    if mv:
        up = [m for m in mv["moved"] if m["delta"] < 0]
        down = [m for m in mv["moved"] if m["delta"] > 0]
        if up:
            L += ["", f"## ▲ Improved ({len(up)})"] + [f"- {m['keyword']}: {m['prev']}→{m['curr']}" for m in up[:15]]
        if down:
            L += ["", f"## ▼ Dropped ({len(down)})"] + [f"- {m['keyword']}: {m['prev']}→{m['curr']}" for m in down[:15]]
        if mv["features"]:
            L += ["", "## SERP-feature changes"]
            for c in mv["features"][:15]:
                bits = (["+" + g for g in c["gained"]] + ["-" + x for x in c["lost"]])
                L.append(f"- {c['keyword']}: {', '.join(bits)}")
    return "\n".join(L)
