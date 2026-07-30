"""The learning loop — the tool teaches itself which changes actually work, and carries
those lessons across every site it touches.

Two layers:
  · LOCAL — aggregate the causal ledger's follow-ups (per change, at +7/+28/+90 days,
    holdout-adjusted) by *change type* → mean lift, win-rate, sample size. "On THIS site,
    answer-first rewrites beat title fixes at 28 days."
  · GLOBAL — an anonymized cross-site store (`~/.seo-agent/lessons.json`) so a lesson from
    one company informs the next (and cold-starts a brand-new site). Only aggregate stats
    are stored — change type → {n, lift, wins} per horizon, keyed by a HASH of the domain.
    No URLs, no content, no domains in the clear. Privacy-safe cross-company learning.

`ranking()` feeds `plan`/`autopilot` so recommendations are ordered by what has actually
worked (local evidence first, global for cold-start). This runs automatically every cycle —
it's a standing rule, not a manual step. Stdlib only. Site-agnostic."""
import datetime
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from . import ledger

HORIZONS = (7, 28, 90)
_LABEL = {7: "day", 28: "week", 90: "month"}


def _global_path(cfg):
    p = (cfg.get("global_lessons_path") or os.environ.get("SEO_GLOBAL_LESSONS")
         or os.path.expanduser("~/.seo-agent/lessons.json"))
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    return Path(p)


def _site_key(cfg):
    dom = urlparse(cfg.get("site", "")).netloc.replace("www.", "").lower() or "unknown"
    return hashlib.sha256(dom.encode()).hexdigest()[:12]  # anonymized, stable per site


def local_lessons(cfg):
    """{type: {horizon: {n, mean_lift, win_rate}}} from this site's follow-ups."""
    agg = {}
    for r in ledger.followups(cfg):
        t = agg.setdefault(r["type"], {}).setdefault(r["horizon"], {"n": 0, "sum": 0.0, "wins": 0})
        t["n"] += 1
        t["sum"] += r["lift"]
        t["wins"] += 1 if r["lift"] > 0 else 0
    return {t: {h: {"n": v["n"], "mean_lift": round(v["sum"] / v["n"], 1),
                    "win_rate": round(v["wins"] / v["n"], 2)}
                for h, v in hs.items()} for t, hs in agg.items()}


# ── cross-site global store (anonymized, aggregate-only, OPT-IN) ────────────
def sharing(cfg):
    """Cross-site contribution is consent-gated (asked at wizard/onboarding). Only
    change-type × horizon aggregates keyed by a domain hash are ever stored — but it
    still crosses workspace (client) boundaries, so it is OFF until someone says yes.
    config: learning.share_cross_site · env override: SEO_SHARE_LESSONS=1/0."""
    env = os.environ.get("SEO_SHARE_LESSONS")
    if env is not None:
        return env.lower() not in ("0", "false", "no", "off")
    return bool((cfg.get("learning") or {}).get("share_cross_site"))


def update_global(cfg):
    """Contribute this site's aggregate lessons to the global store (idempotent: replaces
    this site's prior contribution, keyed by domain hash). Runs automatically each cycle —
    but ONLY with consent (see `sharing`). Reading the store is always allowed: it's the
    operator's own machine-wide memory."""
    if not sharing(cfg):
        return {"contributed": 0, "sharing": "off",
                "how": "opt in with learning.share_cross_site=true in config.json (the wizard asks)"}
    raw = {}
    for r in ledger.followups(cfg):
        d = raw.setdefault(r["type"], {}).setdefault(str(r["horizon"]), {"n": 0, "sum": 0.0, "wins": 0})
        d["n"] += 1
        d["sum"] += r["lift"]
        d["wins"] += 1 if r["lift"] > 0 else 0
    if not raw:
        return {"contributed": 0}
    p = _global_path(cfg)
    store = json.loads(p.read_text()) if p.exists() else {"version": 1, "sites": {}}
    store["sites"][_site_key(cfg)] = {"types": raw, "updated": datetime.date.today().isoformat()}
    p.write_text(json.dumps(store, indent=1))
    return {"contributed": sum(len(v) for v in raw.values()), "sites_in_store": len(store["sites"])}


def global_lessons(cfg):
    """Sum every site's contribution → {type: {horizon: {n, mean_lift, win_rate}}} + site count."""
    p = _global_path(cfg)
    if not p.exists():
        return {}, 0
    store = json.loads(p.read_text())
    agg = {}
    for site in store.get("sites", {}).values():
        for t, hs in site.get("types", {}).items():
            for h, v in hs.items():
                d = agg.setdefault(t, {}).setdefault(int(h), {"n": 0, "sum": 0.0, "wins": 0})
                d["n"] += v["n"]
                d["sum"] += v["sum"]
                d["wins"] += v["wins"]
    out = {t: {h: {"n": v["n"], "mean_lift": round(v["sum"] / v["n"], 1),
                   "win_rate": round(v["wins"] / v["n"], 2)}
               for h, v in hs.items()} for t, hs in agg.items()}
    return out, len(store.get("sites", {}))


def ranking(cfg, horizon=28, min_n=3):
    """Change types ordered by proven lift — LOCAL evidence first, GLOBAL for cold-start.
    Returns [{type, mean_lift, n, win_rate, source}]. This is what plan/autopilot consult."""
    loc = local_lessons(cfg)
    glob, _sites = global_lessons(cfg)
    rows, seen = [], set()
    for t, hs in loc.items():
        v = hs.get(horizon) or next(iter(hs.values()), None)
        if v and v["n"] >= 1:
            rows.append({"type": t, "mean_lift": v["mean_lift"], "n": v["n"],
                         "win_rate": v["win_rate"], "source": "this-site"})
            seen.add(t)
    for t, hs in glob.items():  # cold-start / fill gaps from cross-site evidence
        if t in seen:
            continue
        v = hs.get(horizon) or next(iter(hs.values()), None)
        if v and v["n"] >= min_n:
            rows.append({"type": t, "mean_lift": v["mean_lift"], "n": v["n"],
                         "win_rate": v["win_rate"], "source": "cross-site"})
    return sorted(rows, key=lambda r: -r["mean_lift"])


def cycle(cfg):
    """The standing rule: measure follow-ups, then contribute to the global store. Called
    automatically by autopilot/run so learning is never skipped."""
    fu = ledger.follow_up(cfg, HORIZONS)
    up = update_global(cfg) if fu.get("recorded") else {"contributed": 0}
    return {"follow_up": fu, "global": up}


def render_md(cfg):
    cycle(cfg)  # refresh before reporting
    loc = local_lessons(cfg)
    glob, sites = global_lessons(cfg)
    L = [f"# What's working — learning loop — {cfg.get('site','site')}", ""]
    if loc:
        L += ["## This site — impact by change type (holdout-adjusted lift)",
              "| change type | day (+7) | week (+28) | month (+90) | wins |", "|---|--:|--:|--:|--:|"]
        for t, hs in sorted(loc.items(), key=lambda kv: -(kv[1].get(28, kv[1].get(7, {})).get("mean_lift", 0))):
            def cell(h):
                v = hs.get(h)
                return (f"{v['mean_lift']:+g} (n{v['n']})" if v else "—")
            wr = hs.get(28, hs.get(7, {})).get("win_rate")
            L.append(f"| {t} | {cell(7)} | {cell(28)} | {cell(90)} | {int((wr or 0)*100)}% |")
    else:
        L.append("_No measured follow-ups yet on this site — they accrue as `gsc` snapshots build "
                 "over time after changes are logged (via `control`/`pr`)._")
    rank = ranking(cfg)
    if rank:
        L += ["", "## ▶ Recommended next (best proven track record)"]
        for r in rank[:6]:
            L.append(f"- **{r['type']}** — {r['mean_lift']:+g} avg lift/page, {int(r['win_rate']*100)}% win "
                     f"(n={r['n']}, {r['source']})")
    if glob:
        L += ["", f"## Cross-site knowledge ({sites} site{'s' if sites!=1 else ''}, anonymized)",
              "| change type | week (+28) mean lift | win rate | n |", "|---|--:|--:|--:|"]
        for t, hs in sorted(glob.items(), key=lambda kv: -(kv[1].get(28, {}).get("mean_lift", 0)))[:8]:
            v = hs.get(28) or next(iter(hs.values()))
            L.append(f"| {t} | {v['mean_lift']:+g} | {int(v['win_rate']*100)}% | {v['n']} |")
    share = "ON" if sharing(cfg) else "OFF (opt in: learning.share_cross_site=true — the wizard asks)"
    L.append(f"\n_Runs automatically every autopilot/run cycle. Cross-site sharing: **{share}**. "
             "Global store: only change-type × horizon aggregates keyed by a domain hash — "
             "no URLs, content, or domains stored._")
    return "\n".join(L)


def notify(cfg):
    from . import channels
    rank = ranking(cfg)
    if not rank:
        return {"sent": None}
    top = rank[:3]
    text = f"*📚 SEO learning — {cfg.get('site','')}*\nBest-performing change types right now:\n" + \
           "\n".join(f"  • {r['type']}: {r['mean_lift']:+g} avg lift ({int(r['win_rate']*100)}% win, {r['source']})" for r in top)
    return {"top": top, "sent": channels.send(cfg, text, subject="SEO learning update")}
