"""Autopilot — the self-running loop. Four agent roles run in sequence each cycle and
write to the shared blackboard (`state/`): Audit finds the situation, Planner sets the
dated backlog + per-item cadence, Executor ships what's due (through the safety + review
gate), Analyst measures and reports. Every role orchestrates existing commands; the loop
just advances items planned → dispatched → done and records everything.

Runs in the CLI (`autopilot --daily|--weekly|--monthly`) or is spawned as agents inside
Claude Code. Human review stays between the Executor and any live change. Site-agnostic."""
import datetime

from . import channels, ledger, state

# per action-kind: (days until due, recheck cadence)
_SCHED = {
    "fix:meta": (0, "weekly"), "fix:links": (0, "weekly"), "fix:duplicate": (0, "weekly"),
    "fix:headings": (0, "weekly"), "fix:a11y": (2, "monthly"), "retitle": (0, "weekly"),
    "consolidate": (1, "weekly"), "sculpt": (1, "weekly"), "push": (2, "weekly"),
    "refresh": (1, "weekly"), "repeat-win": (0, "weekly"),
    "write": (4, "weekly"), "cluster": (5, "weekly"),
    "eeat": (3, "monthly"), "geo": (3, "monthly"), "entity": (3, "monthly"),
    "citability": (3, "monthly"), "ai-visibility": (2, "weekly"), "decide": (1, "weekly"),
}


def _today():
    return datetime.date.today()


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None


def _key(a):
    return f"{a.get('kind', a.get('action'))}|{a.get('target')}"


# ── 1. AUDIT ────────────────────────────────────────────────────────────────
def audit_phase(cfg):
    from . import anomaly, audit, decay
    sit = {"date": _today().isoformat(), "health": None, "problems": [], "anomalies": [], "movers": []}
    a = _safe(lambda: audit.report(cfg))
    if a:
        sit["health"] = a.get("counts")
        order = {"high": 0, "med": 1, "low": 2}
        sit["problems"] = [{"sev": f["sev"], "msg": f["msg"], "cat": f.get("cat"), "cmd": "audit"}
                           for f in sorted(a["findings"], key=lambda f: order.get(f["sev"], 3))[:12]]
    sit["anomalies"] = [{"sev": x["sev"], "kind": x["kind"], "msg": x["msg"]}
                        for x in (_safe(lambda: anomaly.detect(cfg)) or [])]
    dec = _safe(lambda: decay.detect(cfg)) or {}
    sit["movers"] = [{"query": m["query"], "prev": m["prev"], "curr": m["curr"]}
                     for m in (dec.get("queries") or [])[:8]]
    state.write(cfg, "situation", sit)
    return sit


# ── 2. PLAN (dated, merges with prior so statuses persist) ──────────────────
def plan_phase(cfg):
    from . import plan as planmod
    actions = _safe(lambda: planmod.build(cfg)) or []
    today = _today()
    prior = {i["key"]: i for i in (state.read(cfg, "plan", {}) or {}).get("items", [])}
    next_id = max([i["id"] for i in prior.values()], default=0)
    items = []
    for a in actions[:40]:
        k = _key(a)
        if k in prior:
            items.append(prior.pop(k))  # keep status + dates
            continue
        off, cad = _SCHED.get(a["kind"], (2, "weekly"))
        next_id += 1
        items.append({"id": next_id, "action": a["kind"], "target": a["target"], "why": a["why"],
                      "effort": a["effort"], "impact": a["impact"], "cmd": a["cmd"], "cadence": cad,
                      "due_date": (today + datetime.timedelta(days=off)).isoformat(),
                      "status": "planned", "key": k})
    # carry over any still-open prior items not re-surfaced (don't lose in-flight work)
    items += [i for i in prior.values() if i["status"] not in ("done",)]
    pl = {"date": today.isoformat(), "items": sorted(items, key=lambda i: (i["due_date"], -i["impact"]))}
    state.write(cfg, "plan", pl)
    return pl


# ── 3. EXECUTE (advance due items; close via the ledger) ────────────────────
_TASK = {
    "write": lambda t: f'crew article "{t}"', "cluster": lambda t: f'draft "{t}" (pillar)',
    "refresh": lambda t: f"refresh {t}", "retitle": lambda t: f"retitle {t}",
    "consolidate": lambda t: f"consolidate → control redirect into {t}",
    "fix:meta": lambda t: f"pr/control update_meta on {t}", "fix:links": lambda t: f"autolink → {t}",
    "fix:freshness": lambda t: f"retitle {t} (bump the stale year, refresh dated stats)",
    "sculpt": lambda t: f"add internal links to {t} (pagerank)", "push": lambda t: f'brief "{t}" → optimize',
    "entity": lambda t: "entity → add Wikidata + sameAs", "citability": lambda t: f"rewrite {t} answer-first",
}


def execute_phase(cfg):
    pl = state.read(cfg, "plan", {}) or {}
    today = _today().isoformat()
    cap = (cfg.get("autopilot", {}) or {}).get("max_per_cycle", 5)
    changed_urls = {c["url"].rstrip("/") for c in ledger.changes(cfg)}
    done, dispatched, scheduled, n = [], [], [], 0
    for it in pl.get("items", []):
        tgt = str(it["target"]).rstrip("/")
        if it["status"] == "dispatched":  # close the loop: a change was logged for it
            if tgt in changed_urls:
                it["status"] = "done"
                done.append({"id": it["id"], "action": it["action"], "target": it["target"]})
            continue
        if it["status"] == "planned" and it["due_date"] <= today and n < cap:
            fn = _TASK.get(it["action"])
            it["task"] = fn(it["target"]) if fn else f"run `{it['cmd']}` for {it['target']}"
            it["status"] = "dispatched"
            dispatched.append({"id": it["id"], "action": it["action"], "target": it["target"], "task": it["task"]})
            n += 1
        elif it["status"] == "planned":
            scheduled.append({"id": it["id"], "action": it["action"], "due_date": it["due_date"]})
    state.write(cfg, "plan", pl)
    ex = {"date": today, "done": done, "dispatched": dispatched, "scheduled": scheduled[:15],
          "note": "dispatched tasks are executed by the agent/workflows through the review + safety gate; "
                  "each item closes to 'done' when its change lands in the ledger"}
    state.write(cfg, "executions", ex)
    return ex


# ── 4. REPORT (attribution + deliver) ───────────────────────────────────────
def report_phase(cfg, deliver=True):
    from . import learn
    ex = state.read(cfg, "executions", {}) or {}
    att = _safe(lambda: ledger.attribution(cfg)) or {}
    wins = [r for r in att.get("rows", []) if r.get("holdout_adjusted_lift", 0) > 0][:8]
    # STANDING RULE: measure follow-ups (day/week/month) + contribute to cross-site learning,
    # and run the brain's observe→distill→reuse→refine pass (feedback → taste → playbooks).
    from . import brain
    _safe(lambda: learn.cycle(cfg))
    brain_state = _safe(lambda: brain.cycle(cfg)) or {}
    learned = _safe(lambda: learn.ranking(cfg)) or []
    rep = {"date": _today().isoformat(), "shipped_today": ex.get("done", []),
           "dispatched_today": ex.get("dispatched", []), "proven_wins": wins,
           "attribution_window": att.get("window"),
           "learned_best": learned[:5], "brain": brain_state.get("memory")}
    state.write(cfg, "report", rep)
    if deliver and (cfg.get("review", {}) or cfg.get("report", {})):
        text = _digest_text(cfg, rep)
        rep["delivered"] = channels.send(cfg, text, subject=f"SEO autopilot — {cfg.get('site','')}")
    return rep


def _digest_text(cfg, rep):
    ship = "\n".join(f"  • {d['action']} → {d['target']}" for d in rep["shipped_today"]) or "  • (nothing landed today)"
    disp = "\n".join(f"  • {d['action']} → {d['target']}" for d in rep["dispatched_today"][:6]) or "  • (none)"
    wins = "\n".join(f"  • {w['url']}: +{w['holdout_adjusted_lift']} clicks (holdout-adjusted)"
                     for w in rep["proven_wins"][:5]) or "  • (attribution builds as history accrues)"
    return (f"*SEO autopilot — {cfg.get('site','')} — {rep['date']}*\n\n"
            f"Shipped today:\n{ship}\n\nDispatched (in progress / review):\n{disp}\n\n"
            f"Proven wins ({rep.get('attribution_window') or 'window'}):\n{wins}")


# ── the loop ────────────────────────────────────────────────────────────────
def cycle(cfg, cadence="daily", deliver=True):
    sit = audit_phase(cfg)
    pl = plan_phase(cfg)
    ex = execute_phase(cfg)
    if cadence == "monthly":
        from . import competitors
        _safe(lambda: competitors.delta(cfg))
    rep = report_phase(cfg, deliver=deliver)
    return {"cadence": cadence, "situation": sit, "plan": pl, "executions": ex, "report": rep}


def render_md(cfg, r):
    pl, ex, rep = r["plan"], r["executions"], r["report"]
    due = [i for i in pl["items"] if i["status"] == "dispatched"]
    L = [f"# Autopilot cycle ({r['cadence']}) — {cfg.get('site','site')}", "",
         f"**Situation:** {len(r['situation']['problems'])} problems, "
         f"{len(r['situation']['anomalies'])} anomalies · **Plan:** {len(pl['items'])} items · "
         f"**Executed:** {len(ex['done'])} closed, {len(ex['dispatched'])} dispatched, "
         f"{len(ex['scheduled'])} scheduled", ""]
    if ex["dispatched"]:
        L += ["## Dispatched this cycle (through review + safety gate)"]
        for d in ex["dispatched"]:
            L.append(f"- **{d['action']}** → {d['target']}  · `{d['task']}`")
    if ex["scheduled"]:
        L += ["", "## Scheduled ahead"]
        for s in ex["scheduled"][:8]:
            L.append(f"- {s['due_date']} — {s['action']} ({s['id']})")
    if rep["proven_wins"]:
        L += ["", "## Proven wins (ledger)"]
        for w in rep["proven_wins"][:5]:
            L.append(f"- {w['url']}: +{w['holdout_adjusted_lift']} clicks (holdout-adjusted)")
    if rep.get("learned_best"):
        L += ["", "## What's working best (learned — day/week/month follow-ups)"]
        for r in rep["learned_best"][:4]:
            L.append(f"- **{r['type']}** — {r['mean_lift']:+g} avg lift/page ({int(r['win_rate']*100)}% win, {r['source']})")
    L.append("\n_Watch it live with `serve`; approve dispatched changes there or via `review`. "
             "Impact by day/week/month + what works: `learn`._")
    return "\n".join(L)
