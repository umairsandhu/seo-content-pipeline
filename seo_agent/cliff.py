"""Traffic-cliff detector — the DAILY series behind `diagnose`.

Two 28-day aggregates cannot see a cliff: on superx.pk (2026-11-03) Search Console showed
impressions 711 on 27 Oct, then 52, 23, 11, 4 — a 97–99% fall in every section on one day —
while `diagnose` compared the last two 28-day snapshots and printed "Clicks +0%". A step change
lives in the daily numbers, so this module reads those (LEARNINGS 34).

  fetch(cfg)   a few GSC calls (<= 8): daily totals + daily series for the top path sections;
               snapshots the result to history/gsc_daily/ and falls back to that snapshot
               when the API is unreachable. No credentials and no snapshot -> None.
  detect(...)  pure and deterministic: scan every split day, take the one with the biggest
               fall of "median of the next 3-5 days" vs "median of the 7 days before", then
               pin the first day it happened. A gradual decline and flat noise are NOT steps.
  find(cfg)    fetch + detect + the split by top-level path section (site-wide or one template?)
               + the overlap with a listed Google update. Stdlib only."""
import datetime
import re
import statistics
from urllib.parse import urlparse

from . import history

WINDOW = 7            # days before the step that define "normal"
AFTER_MAX = 5         # days after the step compared against it
AFTER_MIN = 3         # fewest after-days that can prove a step
MIN_BEFORE = {"impressions": 20, "clicks": 10}   # below this a daily median is noise
HIGH = 0.5            # fall that earns high confidence
MED = 0.3             # smallest fall reported at all
UPDATE_DAYS = 16      # a listed update starting this many days before the step may explain it
TOP_SECTIONS = 6
SHARE_MATERIAL = 0.05  # a section under 5% of the traffic does not decide site-wide vs template
_IDX = {"clicks": 0, "impressions": 1}


def _d(s):
    return datetime.date.fromisoformat(s)


def _days(first, last):
    n = (_d(last) - _d(first)).days
    return [(_d(first) + datetime.timedelta(days=i)).isoformat() for i in range(n + 1)]


def _vals(daily, days, metric):
    """Aligned list of one metric over `days`; a day Search Console omits had no impressions."""
    i = _IDX[metric]
    return [float((daily.get(d) or [0, 0])[i]) for d in days]


def _med(xs):
    return statistics.median(xs) if xs else 0.0


def _step(vals, o):
    """before/after medians and the 3-day sharpness around index `o`."""
    before = _med(vals[max(0, o - WINDOW):o])
    after = _med(vals[o:o + AFTER_MAX])
    pre3, post3 = _med(vals[max(0, o - 3):o]), _med(vals[o:o + 3])
    drop = 1 - after / before if before else 0.0
    sharp = 1 - post3 / pre3 if pre3 else 0.0
    return before, after, drop, sharp


def _scan(vals, metric):
    """The split with the largest median fall, then the first day of that fall; or None."""
    n = len(vals)
    best = None
    for s in range(WINDOW, n - AFTER_MIN + 1):
        before = _med(vals[s - WINDOW:s])
        if before < MIN_BEFORE[metric]:
            continue
        after_days = vals[s:s + AFTER_MAX]
        if max(after_days) > before * (1 - MED) or max(after_days) >= min(vals[s - WINDOW:s]):
            continue          # after a step EVERY day is below normal and below every day before it
        drop = 1 - _med(after_days) / before
        if best is None or drop > best[0] + 1e-9:
            best = (drop, s, before)
    if not best or best[0] < MED:
        return None
    drop, s, before = best
    mid = (before + _med(vals[s:s + AFTER_MAX])) / 2
    o = s
    for d in range(max(0, s - WINDOW), min(n - AFTER_MIN + 1, s + AFTER_MAX)):   # first day that stays under the midpoint
        if max(vals[d:d + AFTER_MIN]) <= mid:
            o = d
            break
    return o


def detect(total, through=None, metrics=("impressions", "clicks")):
    """Step change in a daily series {date: [clicks, impressions]}.
    Returns None (no step, or too little data) or a dict: metric, onset, before, after,
    drop_pct, sharp_pct, confidence, recovered, through, days. Deterministic."""
    if not total:
        return None
    through = through or max(total)
    days = _days(min(total), through)
    if len(days) < WINDOW + AFTER_MIN + 4:
        return None
    out = None
    for m in metrics:
        vals = _vals(total, days, m)
        o = _scan(vals, m)
        if o is None:
            continue
        before, after, drop, sharp = _step(vals, o)
        if before < MIN_BEFORE[m] or drop < MED or sharp < max(MED, 0.6 * drop):
            continue          # a slow slide changes little from one 3-day block to the next
        r = {"metric": m, "onset": days[o], "before": round(before, 1), "after": round(after, 1),
             "drop_pct": round(drop * 100, 1), "sharp_pct": round(sharp * 100, 1),
             "confidence": "high" if drop >= HIGH else "med",
             "recovered": _med(vals[-3:]) >= 0.8 * before,
             "through": days[-1], "days": len(days), "after_days": len(days) - o}
        if out is None or r["drop_pct"] > out["drop_pct"]:
            out = r
    return out


def sections_split(cliff, total, sections):
    """The same step in each top-level path section. `sections` = {name: {date: [c, i]}}.
    Verdict: 'site-wide' (every material section fell), 'template' (some held) or 'single'."""
    days = _days(min(total), cliff["through"])
    o = days.index(cliff["onset"])
    m = cliff["metric"]
    site_drop = cliff["drop_pct"] / 100
    rows = []
    for name, daily in sections.items():
        v = _vals(daily, days, m)
        before, after, drop, _ = _step(v, o)
        rows.append({"section": name, "before": round(before, 1), "after": round(after, 1),
                     "drop_pct": round(drop * 100, 1)})
    tot_before = sum(r["before"] for r in rows) or 1
    for r in rows:
        r["share_pct"] = round(r["before"] / tot_before * 100, 1)
        r["fell"] = r["before"] > 0 and r["drop_pct"] / 100 >= max(MED, 0.5 * site_drop)
    material = [r for r in rows if r["share_pct"] >= SHARE_MATERIAL * 100 and r["before"] > 0]
    rows.sort(key=lambda r: -r["before"])
    if len(material) < 2:
        verdict = "single"
    elif all(r["fell"] for r in material):
        verdict = "site-wide"
    else:
        verdict = "template"
    return {"rows": rows, "verdict": verdict,
            "fell": [r["section"] for r in material if r["fell"]],
            "held": [r["section"] for r in material if not r["fell"]]}


def overlapping_update(onset, updates):
    """A listed Google update that started up to UPDATE_DAYS before the step, or 1 day after."""
    o = _d(onset)
    hit = [(d, n) for d, n in updates if -1 <= (o - _d(d)).days <= UPDATE_DAYS]
    return hit[-1] if hit else None


def section_of(url):
    """'/stocks/' for https://x.com/stocks/OGDC/; '(root)' for the home page and root-level pages."""
    segs = [s for s in urlparse(url).path.split("/")]
    return f"/{segs[1]}/" if len(segs) > 2 and segs[1] else "(root)"


def _section_regex(name):
    if name == "(root)":
        return r"^https?://[^/]+(/[^/]*)?$"
    return r"^https?://[^/]+" + re.escape(name)


def _rows_by_date(rows):
    return {r["date"]: [r["clicks"], r["impressions"]] for r in rows}


def fetch(cfg, days=35, today=None):
    """Daily totals + per-section daily series: {'total', 'sections', 'through', 'source'}.
    <= 8 GSC calls (1 totals, 1 page list, 1 per section). Falls back to the latest
    history/gsc_daily snapshot; None when neither exists."""
    from . import providers
    prop, cred = cfg.get("gsc_property"), cfg.get("gsc_credentials")
    if prop and cred:
        try:
            svc = providers.gsc_service(cred)
            if svc:
                end = (today or datetime.date.today()) - datetime.timedelta(days=1)
                start = end - datetime.timedelta(days=days - 1)
                a, b = str(start), str(end)
                total = _rows_by_date(providers.gsc_query(svc, prop, a, b, ("date",), 100))
                if total:
                    pages = providers.gsc_query(svc, prop, a, b, ("page",), 25000)
                    weight = {}
                    for r in pages:
                        s = section_of(r["page"])
                        weight[s] = weight.get(s, 0) + r["impressions"]
                    top = sorted(weight, key=lambda s: -weight[s])[:TOP_SECTIONS]
                    sections = {s: _rows_by_date(providers.gsc_query(
                        svc, prop, a, b, ("date",), 100, page_regex=_section_regex(s))) for s in top}
                    data = {"total": total, "sections": sections, "through": max(total)}
                    history.snapshot(cfg, "gsc_daily", data)
                    return {**data, "source": "live"}
        except Exception:
            pass          # quota, network or auth: use the stored series below
    snap = history.latest(cfg, "gsc_daily")
    if snap and snap["data"].get("total"):
        return {**snap["data"], "source": f"history {snap['date']}"}
    return None


def find(cfg, series=None):
    """Everything `diagnose` needs: {'cliff': dict|None, 'source', 'through', 'sections', 'update'}
    or None when there is no daily series at all (no GSC, no snapshot)."""
    from . import algo
    series = series or fetch(cfg)
    if not series:
        return None
    c = detect(series["total"], series.get("through"))
    out = {"cliff": c, "source": series.get("source"), "through": series.get("through"),
           "sections": None, "update": None}
    if c:
        out["update"] = overlapping_update(c["onset"], algo.UPDATES)
        if series.get("sections"):
            out["sections"] = sections_split(c, series["total"], series["sections"])
    return out
