"""Action engine — "do the right things for any site." Fuses every signal the
tool produces (Site Doctor findings, GSC striking-distance + low-CTR, content
decay, competitor gaps, cannibalization, orphans, AI-crawler policy) into ONE
prioritized action plan: what to do next, in order, scored by impact ÷ effort,
each with the command to run.

This is the 0→100 co-pilot — run `plan` at any point to get the next best moves.
Every source degrades: with no creds you still get the technical-fix plan from
the Site Doctor."""
from . import (analyze, audit, authority, authority_flow, citability, decay, eeat, entity,
               geo, history, internal)
from .index import Index, load_corpus

EFFORT_W = {"S": 1.0, "M": 0.8, "L": 0.6}


def _a(impact, effort, kind, target, why, cmd):
    return {"kind": kind, "target": target, "why": why, "effort": effort, "cmd": cmd,
            "impact": impact, "score": round(min(100, impact) * EFFORT_W[effort])}


def build(cfg):
    actions, seen = [], set()

    def add(action):
        key = (action["kind"], action["target"])
        if key not in seen:
            seen.add(key)
            actions.append(action)

    # 1. Technical fixes from the Site Doctor
    try:
        a = audit.report(cfg)
        for f in a["findings"]:
            if f["sev"] == "high":
                add(_a(90, "S", "fix:" + f["cat"], f["url"], f["msg"], "audit"))
            elif f["sev"] == "med":
                add(_a(60, "S", "fix:" + f["cat"], f["url"], f["msg"], "audit"))
            elif "AI crawlers" in f["msg"]:  # strategic, surfaced despite low sev
                add(_a(75, "S", "decide", f["url"], f["msg"], "audit"))
    except Exception:
        pass

    # 2. GSC opportunities — push striking-distance, retitle low-CTR
    opp = analyze.gsc_opportunities(cfg)
    if opp:
        for r in opp["striking"][:15]:
            add(_a(40 + r["impressions"] // 50, "M", "push", r["query"],
                   f"pos {r['position']:.1f}, {r['impressions']} impr — one push to page 1",
                   f"aio  (check AIO before investing)"))
        for r in opp["low_ctr"][:10]:
            add(_a(45 + r["impressions"] // 100, "S", "retitle", r["page"],
                   f"{r['impressions']} impr at {r['ctr']*100:.1f}% CTR", f"retitle {r['page']}"))

    # 3. Decaying content → refresh
    dec = decay.detect(cfg) or {}
    for m in (dec.get("queries") or [])[:8]:
        add(_a(70, "M", "refresh", m["query"], f"slipped {m['prev']}→{m['curr']} in rank", "decay"))
    for m in (dec.get("pages") or [])[:8]:
        add(_a(65, "M", "refresh", m["page"], f"clicks {m['delta']:+}", "decay"))

    # 4. Competitor gaps → write
    if cfg.get("competitors"):
        try:
            for g in analyze.competitor_gap(cfg, Index(load_corpus()))[:8]:
                add(_a(45 + len(g["competitors"]) * 10, "L", "write", g["keyword"],
                       f"{len(g['competitors'])} competitor(s) rank; you don't",
                       f'draft "{g["keyword"]}"'))
        except Exception:
            pass

    # 5. E-E-A-T + topical structure + consolidation (offline, cheap)
    try:
        e = eeat.report(cfg)
        if e["pages"] and len(e["no_author"]) > e["pages"] * 0.5:
            add(_a(50, "M", "eeat", cfg.get("site", ""),
                   f"{len(e['no_author'])}/{e['pages']} pages have no author byline", "eeat"))
        for tp in e["missing_trust"][:1]:
            add(_a(55, "S", "eeat", "/" + tp, f"no {tp} page (trust signal)", "eeat"))
    except Exception:
        pass
    try:
        for c in authority.clusters(cfg):
            if not c["healthy"] and c["size"] >= 3:
                add(_a(55, "M", "cluster", c["pillar"],
                       f"weak topic cluster (size {c['size']}, density {c['link_density']}) — pillar + internal links",
                       "authority"))
    except Exception:
        pass
    try:
        for cn in internal.consolidation(cfg)[:5]:
            add(_a(60, "M", "consolidate", cn["keep"],
                   f"cannibalization — redirect {len(cn['merge_redirect'])} page(s) into this", "consolidate"))
    except Exception:
        pass
    try:
        g = geo.report(cfg)
        for k, n in g["missing"].items():
            if k in ("schema", "qa_headings", "citations") and g["pages"] and n > g["pages"] * 0.5:
                add(_a(48, "M", "geo", cfg.get("site", ""),
                       f"{n}/{g['pages']} pages missing {k} — AI-citation readiness", "geo"))
                break
    except Exception:
        pass

    # 6. Entity / knowledge-graph — a missing Wikidata node is the top GEO fix
    try:
        en = entity.report(cfg)
        if not en["wikidata"]:
            add(_a(72, "M", "entity", cfg.get("site", ""),
                   "no Wikidata entity — AI engines can't resolve the brand to a knowledge-graph node", "entity"))
        elif len(en["sameAs_present"]) < 4:
            add(_a(45, "S", "entity", cfg.get("site", ""),
                   f"only {len(en['sameAs_present'])} authoritative sameAs profiles — add more", "entity"))
    except Exception:
        pass

    # 7. Passage-citability — front-load answers so AI answers can quote you
    try:
        ci = citability.report(cfg)
        af = ci["missing"].get("answer_first", 0)
        if ci["pages"] and af > ci["pages"] * 0.5:
            add(_a(52, "M", "citability", cfg.get("site", ""),
                   f"{af}/{ci['pages']} pages lack an answer-first passage (AI-citability {ci['avg']}/100)",
                   "citability"))
    except Exception:
        pass

    # 8. Internal authority flow — link starved money/pillar pages
    try:
        pr = authority_flow.report(cfg)
        for p in pr["starved_pillars"][:2]:
            add(_a(58, "M", "sculpt", p["url"],
                   f"pillar starved of internal authority ({p['inbound']} inbound) — link from hoarders", "pagerank"))
    except Exception:
        pass

    # 9. AI-visibility — act on the last aivis snapshot if the tracker has run
    try:
        av = history.latest(cfg, "aivis")
        rows = (av or {}).get("data") or []
        if rows:
            sov = sum(r.get("mentioned") for r in rows) / len(rows)
            if sov < 0.5:
                add(_a(68, "M", "ai-visibility", cfg.get("site", ""),
                       f"cited in only {sov*100:.0f}% of AI answers — improve entity + citability", "aivis"))
    except Exception:
        pass

    # 10. Learn from what worked — repeat proven wins (from the causal ledger)
    try:
        from . import ledger
        att = ledger.attribution(cfg)
        for w in [r for r in att.get("rows", []) if r.get("holdout_adjusted_lift", 0) > 5][:3]:
            add(_a(64, "S", "repeat-win", w["url"],
                   f"proven +{w['holdout_adjusted_lift']} clicks (holdout-adjusted) after our last change — "
                   "apply the same play to similar pages", "ledger"))
    except Exception:
        pass

    actions.sort(key=lambda x: -x["score"])
    return actions


def render_md(cfg, actions):
    L = [f"# Action plan — {cfg.get('site','site')}", "",
         f"{len(actions)} prioritized actions (impact ÷ effort). Fixes are proposed — apply as PRs.", ""]
    if not actions:
        return "\n".join(L + ["_No actions — run `ingest` + `audit` first, and wire GSC/DataForSEO._"])
    L += ["## This week (top 10)", "| # | do | target | why | effort | cmd |", "|--:|---|---|---|:--:|---|"]
    for i, x in enumerate(actions[:10], 1):
        tgt = x["target"].rsplit("/", 1)[-1] or x["target"]
        L.append(f"| {i} | **{x['kind']}** | {tgt[:40]} | {x['why'][:60]} | {x['effort']} | `{x['cmd']}` |")
    rest = actions[10:40]
    if rest:
        L += ["", f"## Backlog ({len(actions)-10} more)"]
        for x in rest:
            L.append(f"- {x['kind']} — {x['target'].rsplit('/',1)[-1] or x['target']} ({x['why'][:50]})")
    return "\n".join(L)
