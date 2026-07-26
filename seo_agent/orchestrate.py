"""Layer 5 — Orchestrate (goals #1, #7). Scheduled runs that observe → decide →
report, persisting each run to history and diffing vs last. Emits digest.md:
what changed, what to do, what to approve.

  weekly  — snapshot GSC, decay, striking-distance, low-CTR, cannibalization
  monthly — everything weekly + trends, backlink gap, algo-update attribution,
            content-gap analysis

Wire via cron or the /schedule skill; the digest is the human review surface
(human merge-gate first, auto-merge later)."""
import datetime

from . import (aivis, algo, analyze, authority_flow, backlinks, citability, decay, entity,
               history, notify, rank, report, trends)
from .index import Index, load_corpus


def run(cfg, keywords=None, monthly=False, daily=False, email=False, out="digest.md"):
    cadence = "daily" if daily else "monthly" if monthly else "weekly"
    rep = {"date": datetime.date.today().isoformat(), "monthly": monthly, "cadence": cadence,
           "site": cfg.get("site", "site")}

    raw = analyze.gsc_raw(cfg)
    if raw:
        history.snapshot(cfg, "gsc_queries", raw["queries"])
        history.snapshot(cfg, "gsc_pages", raw["pages"])
        rep["gsc"] = analyze.opportunities_from(raw)
    rep["decay"] = decay.detect(cfg)

    if daily:  # a light daily pulse — movement + fresh issues, skip the heavy passes
        rep["movement"] = _safe(lambda: rank.movement(cfg))
        md = render_digest(cfg, rep)
        open(out, "w").write(md)
        if email:
            rep["email"] = _email(cfg, cadence, md)
        return rep, md

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
        # AI-search / GEO layer (all offline/free except aivis, which is opt-in)
        for key, fn in (("citability", lambda: citability.report(cfg)),
                        ("entity", lambda: entity.report(cfg)),
                        ("authority_flow", lambda: authority_flow.report(cfg))):
            try:
                rep[key] = fn()
            except Exception:
                rep[key] = None
        if (cfg.get("aivis", {}) or {}).get("auto"):  # set aivis.auto=true to track on cadence
            try:
                rep["aivis"] = aivis.run(cfg)
            except Exception:
                rep["aivis"] = None
        else:
            snap = history.latest(cfg, "aivis")
            rep["aivis_last"] = (snap or {}).get("data")

    md = render_digest(cfg, rep)
    open(out, "w").write(md)
    if email:
        rep["email"] = _email(cfg, cadence, md)
    return rep, md


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None


def _email(cfg, cadence, digest_md):
    """Render report.pdf and email it (auto-email PDF reports on a cadence)."""
    try:
        html = report.build(cfg)
        pdf, _err = report.to_pdf(html)
    except Exception:
        pdf = None
    subject = f"{cadence.title()} SEO report — {cfg.get('site','')}"
    body = f"{cadence.title()} SEO digest for {cfg.get('site','')}.\n\n" + digest_md[:1500]
    return notify.send(cfg, None, subject, body, attachments=[pdf] if pdf else [])


def _corpus_ok():
    try:
        load_corpus()
        return True
    except Exception:
        return False


def render_digest(cfg, rep):
    L = [f"# SEO run digest — {rep['site']} — {rep['date']}",
         f"_{rep.get('cadence','weekly')} run_", ""]

    mv = rep.get("movement")
    if mv:
        up = [m for m in mv.get("moved", []) if m["delta"] < 0]
        down = [m for m in mv.get("moved", []) if m["delta"] > 0]
        L += [f"## Daily pulse — rank movement (▲{len(up)} / ▼{len(down)})"]
        for m in (sorted(up, key=lambda m: m["delta"])[:8]):
            L.append(f"- ▲ {m['keyword']}: {m['prev']}→{m['curr']}")
        for m in (sorted(down, key=lambda m: -m["delta"])[:8]):
            L.append(f"- ▼ {m['keyword']}: {m['prev']}→{m['curr']}")
        L.append("")

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

        # ── AI-search / GEO section ──
        en = rep.get("entity")
        if en:
            wd = "✅ " + en["wikidata"]["qid"] if en["wikidata"] else "🔴 none — top GEO fix"
            L += ["## AI search / GEO",
                  f"- Wikidata entity: {wd} · sameAs profiles: {len(en['sameAs_present'])} · "
                  f"brand salience {en['salience']}"]
        ci = rep.get("citability")
        if ci:
            L.append(f"- Passage-citability: **{ci['avg']}/100** avg · "
                     f"{ci['missing'].get('answer_first',0)}/{ci['pages']} pages lack an answer-first passage")
        af = rep.get("authority_flow")
        if af and af.get("starved_pillars"):
            L.append(f"- Internal authority: {len(af['starved_pillars'])} money/pillar page(s) starved — "
                     "link them from high-PR pages (`pagerank`)")
        av = rep.get("aivis")
        if av and av.get("summary"):
            s = av["summary"]
            L.append(f"- AI visibility: brand cited in **{s['brand_sov']*100:.0f}%** of AI answers "
                     + (f"(competitors: {', '.join(k for k in s['competitor_sov'])})" if s["competitor_sov"] else ""))
        elif rep.get("aivis_last"):
            rows = rep["aivis_last"]
            sov = sum(r.get("mentioned") for r in rows) / max(len(rows), 1)
            L.append(f"- AI visibility (last snapshot): brand cited in **{sov*100:.0f}%** of answers "
                     "— set `aivis.auto=true` to refresh each run")
        if en or ci or af:
            L.append("")

    if len(L) <= 3:
        L.append("_No signals yet — run `ingest` + `gsc` at least twice to build history._")
    return "\n".join(L)
