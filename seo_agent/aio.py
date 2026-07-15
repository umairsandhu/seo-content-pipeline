"""AI-Overview-adjusted CTR model (build-loop roadmap #1). AI Overviews appear on
20%+ of Google searches and suppress organic CTR — heavily at the top, less lower
down. Ranking opportunities on a FLAT CTR curve now over-values queries where an
AIO caps the click-through, so striking-distance/opportunity scoring must discount
by AIO presence × position.

DEGRADATION = AIO-attributed CTR reduction by organic position (Ahrefs, ~300k GSC
keywords, Dec-2023 vs Dec-2025). Positions 1/2/3/10 are the VERIFIED anchors
(-58.0/-50.8/-46.4/-19.4%); 4-9 are linearly interpolated between them. These
figures are directional and short-shelf-life — re-pull quarterly (see BUILDLOOP.md).

BASELINE is a tunable organic-CTR-by-position curve (heuristic default; override
via config `aio.baseline`). Everything degrades: with no DataForSEO creds, AIO
presence is unknown and rows are ranked on the un-discounted model."""
from . import providers

DEGRADATION = {1: -0.580, 2: -0.508, 3: -0.464, 4: -0.425, 5: -0.387,
               6: -0.348, 7: -0.309, 8: -0.271, 9: -0.232, 10: -0.194}
BASELINE = {1: 0.28, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05,
            6: 0.04, 7: 0.03, 8: 0.025, 9: 0.02, 10: 0.018}


def _pos(p):
    return max(1, min(10, int(round(p))))


def degradation(position):
    return DEGRADATION[_pos(position)]


def expected_ctr(position, aio_present, baseline=None):
    b = (baseline or BASELINE)[_pos(position)]
    return b * (1 + degradation(position)) if aio_present else b


def potential_clicks(row, target_pos, aio_present, baseline=None):
    """Extra monthly clicks from reaching target_pos, AIO-aware. Floored at 0."""
    gain = row["impressions"] * expected_ctr(target_pos, aio_present, baseline) - row.get("clicks", 0)
    return max(0, round(gain))


def annotate(cfg, rows, target_pos=None, detect=True):
    """Annotate GSC striking-distance rows with AIO presence + AIO-adjusted upside
    and re-rank by it. `detect` runs one SERP call per row (capped) to find AIOs."""
    a = cfg.get("aio", {})
    target_pos = target_pos or a.get("target_pos", 3)
    baseline = a.get("baseline") or BASELINE
    dfs = cfg.get("dataforseo", {})
    cap = a.get("max_detect", 20)
    out = []
    for i, r in enumerate(rows):
        aio_present = None
        if detect and i < cap:
            aio_present = providers.serp(r["query"], dfs.get("location_name"),
                                         dfs.get("language_name")).get("ai_overview")
        eff = bool(aio_present)  # unknown → treat as no-AIO for the estimate
        out.append({**r, "aio_present": aio_present,
                    "aio_ctr_penalty": f"{degradation(target_pos)*100:.0f}%" if eff else None,
                    "adjusted_potential": potential_clicks(r, target_pos, eff, baseline),
                    "raw_potential": potential_clicks(r, target_pos, False, baseline)})
    out.sort(key=lambda r: -r["adjusted_potential"])
    return out


def render_md(cfg, rows, target_pos=None):
    tp = target_pos or cfg.get("aio", {}).get("target_pos", 3)
    L = [f"# AIO-adjusted opportunities (target position {tp})", "",
         "Upside discounted for AI-Overview presence. Queries with an AIO are worth less "
         "at the top than a flat CTR curve implies.", "",
         "| query | pos | impr | AIO | adj. clicks | raw |", "|---|--:|--:|:--:|--:|--:|"]
    for r in rows[:25]:
        aio = "yes" if r["aio_present"] else ("no" if r["aio_present"] is False else "?")
        L.append(f"| {r['query']} | {r['position']:.1f} | {r['impressions']} | {aio} | "
                 f"{r['adjusted_potential']} | {r['raw_potential']} |")
    return "\n".join(L)
