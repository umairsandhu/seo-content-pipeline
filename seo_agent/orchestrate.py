"""Layer 5 — Orchestrate (goals #1, #7). Scheduled runs that observe → decide →
report, persisting each run to history and diffing vs last. Emits digest.md:
what changed, what to do, what to approve.

  weekly  — snapshot GSC, decay, striking-distance, low-CTR, cannibalization
  monthly — everything weekly + trends, backlink gap, algo-update attribution,
            content-gap analysis

Wire via cron or the /schedule skill; the digest is the human review surface
(human merge-gate first, auto-merge later)."""
import datetime

from . import algo, analyze, backlinks, decay, history, trends
from .index import Index, load_corpus


def run(cfg, keywords=None, monthly=False, out="digest.md"):
    rep = {"date": datetime.date.today().isoformat(), "monthly": monthly,
           "site": cfg.get("site", "site")}

    raw = analyze.gsc_raw(cfg)
    if raw:
        history.snapshot(cfg, "gsc_queries", raw["queries"])
        history.snapshot(cfg, "gsc_pages", raw["pages"])
        rep["gsc"] = analyze.opportunities_from(raw)
    rep["decay"] = decay.detect(cfg)

    try:
        idx = Index(load_corpus())
        rep["cannibalization"] = analyze.cannibalization(idx)
    except Exception:
        rep["cannibalization"] = []

    if monthly:
        rep["gaps"] = analyze.content_gaps(Index(load_corpus()), keywords or [], cfg) \
            if _corpus_ok() else []
        rep["trends"] = trends.scan(cfg, keywords or [cfg.get("brand", {}).get("name", "")]) \
            if keywords else None
        rep["link_gap"] = backlinks.link_gap(cfg) if cfg.get("competitors") else None
        rep["algo"] = algo.attribution(cfg)

    md = render_digest(cfg, rep)
    open(out, "w").write(md)
    return rep, md


def _corpus_ok():
    try:
        load_corpus()
        return True
    except Exception:
        return False


def render_digest(cfg, rep):
    L = [f"# SEO run digest — {rep['site']} — {rep['date']}",
         f"_{'monthly' if rep['monthly'] else 'weekly'} run_", ""]

    dec = rep.get("decay") or {}
    q = dec.get("queries")
    if q:
        L += [f"## ⚠ Decaying queries — refresh these ({len(q)})",
              "| query | was | now | Δpos |", "|---|--:|--:|--:|"]
        L += [f"| {m['query']} | {m['prev']} | {m['curr']} | +{m['delta']} |" for m in q[:15]]
        L.append("")
    p = dec.get("pages")
    if p:
        L += [f"## ⚠ Pages losing clicks ({len(p)})", "| page | Δclicks |", "|---|--:|"]
        L += [f"| {m['page']} | {m['delta']} |" for m in p[:15]]
        L.append("")

    gsc = rep.get("gsc")
    if gsc:
        s = gsc["striking"]
        L += [f"## Striking distance — one push to page 1 ({len(s)})",
              "| query | pos | impr |", "|---|--:|--:|"]
        L += [f"| {r['query']} | {r['position']:.1f} | {r['impressions']} |" for r in s[:15]]
        L += ["", f"## Low-CTR pages — retitle ({len(gsc['low_ctr'])})", "| page | impr | ctr |",
              "|---|--:|--:|"]
        L += [f"| {r['page']} | {r['impressions']} | {r['ctr']*100:.1f}% |"
              for r in gsc["low_ctr"][:15]]
        L.append("")

    c = rep.get("cannibalization") or []
    if c:
        L += [f"## Consolidate — cannibalization clusters ({len(c)})"]
        L += ["- " + " · ".join(m.rsplit('/', 1)[-1] for m in g["members"]) for g in c[:10]]
        L.append("")

    if rep.get("monthly"):
        tr = rep.get("trends")
        if tr and tr.get("rising"):
            L += [f"## 📈 Rising / emerging keywords ({len(tr['rising'])})",
                  "| keyword | vol | signal |", "|---|--:|---|"]
            L += [f"| {r['keyword']} | {r.get('volume') or '—'} | "
                  f"{'emerging' if r.get('emerging') else ''}{' ' if r.get('emerging') and r.get('trend')=='rising' else ''}"
                  f"{'rising' if r.get('trend')=='rising' else ''} |" for r in tr["rising"][:20]]
            L.append("")
        g = rep.get("gaps") or []
        if g:
            L += [f"## Content gaps to write ({len(g)})", "| keyword | vol | verdict |",
                  "|---|--:|---|"]
            L += [f"| {r['keyword']} | {r['volume'] or '—'} | {r['verdict']} |" for r in g[:20]]
            L.append("")
        lg = rep.get("link_gap")
        if lg:
            L += [f"## Backlink gap — outreach targets ({len(lg)})",
                  "| domain | links to # competitors |", "|---|--:|"]
            L += [f"| {d['domain']} | {len(d['links_to'])} |" for d in lg[:20]]
            L.append("")
        a = rep.get("algo")
        if a:
            L += ["## Algorithm-update impact", "| date | update | Δclicks |", "|---|---|--:|"]
            L += [f"| {u['date']} | {u['update']} | {u['change_pct']:+}% |" for u in a]
            L.append("")

    if len(L) <= 3:
        L.append("_No signals yet — run `ingest` + `gsc` at least twice to build history._")
    return "\n".join(L)
