"""First-party CTR curves — derive a position→CTR curve from the site's OWN Search
Console data instead of a generic industry curve. In an AI-Overview world generic
curves badly overstate traffic, so forecasts must come from first-party behaviour.

Reads the latest `gsc_queries` history snapshot (populated by `gsc` / `gsc --csv`),
buckets queries by integer position, and computes an impression-weighted mean CTR
per position. Falls back to a documented generic curve when there's no GSC data, so
it degrades gracefully. Site-agnostic — no brand assumptions."""
from . import history

# Generic desktop organic curve (fallback only) — approximate 2026 post-AIO values.
_GENERIC = {1: .27, 2: .15, 3: .10, 4: .07, 5: .05, 6: .04, 7: .033, 8: .028,
            9: .024, 10: .021}


def curve(cfg):
    """Return {position:int -> ctr:float} derived from GSC, plus a source flag."""
    snap = history.latest(cfg, "gsc_queries")
    rows = (snap or {}).get("data") or []
    if not rows:
        return {"curve": dict(_GENERIC), "source": "generic-fallback", "sample": 0}
    agg = {}  # pos -> [sum(ctr*impr), sum(impr)]
    for r in rows:
        pos, impr, ctr = r.get("position"), r.get("impressions") or 0, r.get("ctr")
        if pos is None or ctr is None or impr <= 0:
            continue
        p = int(round(pos))
        if not 1 <= p <= 20:
            continue
        a = agg.setdefault(p, [0.0, 0])
        a[0] += ctr * impr
        a[1] += impr
    fitted = {p: round(s / n, 4) for p, (s, n) in agg.items() if n > 0}
    if len(fitted) < 3:  # too sparse to trust
        return {"curve": dict(_GENERIC), "source": "generic-fallback", "sample": len(rows)}
    # smooth: enforce monotonic non-increasing so a noisy bucket can't out-CTR a better one
    last = None
    for p in sorted(fitted):
        if last is not None and fitted[p] > last:
            fitted[p] = last
        last = fitted[p]
    return {"curve": fitted, "source": "first-party-gsc", "sample": len(rows)}


def expected_ctr(c, position):
    """Expected CTR at a (possibly fractional) position, from a curve dict."""
    cur = c["curve"] if isinstance(c, dict) and "curve" in c else c
    p = max(1, int(round(position)))
    if p in cur:
        return cur[p]
    keys = sorted(cur)
    if p < keys[0]:
        return cur[keys[0]]
    below = [k for k in keys if k <= p]
    return cur[below[-1]] if below else cur[keys[-1]]


def project(cfg, impressions, from_pos, to_pos):
    """Extra monthly clicks from moving `impressions` from one position to another."""
    c = curve(cfg)
    gain = (expected_ctr(c, to_pos) - expected_ctr(c, from_pos)) * impressions
    return {"delta_clicks": round(gain), "source": c["source"]}


def render_md(cfg):
    c = curve(cfg)
    L = [f"# CTR curve — {cfg.get('site','site')}",
         f"source: **{c['source']}** · sample {c['sample']} queries", "",
         "| position | CTR |", "|--:|--:|"]
    for p in sorted(c["curve"]):
        L.append(f"| {p} | {c['curve'][p]*100:.1f}% |")
    if c["source"] != "first-party-gsc":
        L.append("\n_No GSC snapshot — using a generic fallback curve. Run `gsc` (or `gsc --csv`) "
                 "for first-party accuracy._")
    return "\n".join(L)
