"""The employee's identity & memory files — the OpenClaw workspace pattern, adopted:
persistent state lives in EDITABLE MARKDOWN the agent reads every session, so the
SEO employee survives restarts, model swaps, and context resets — and the operator
can tune its personality with a text editor.

  AGENTS.md   operating instructions for ANY driving agent session (the loop, the
              standing rules, where state lives, approval etiquette)  [every session]
  SOUL.md     the employee's persona, tone, boundaries — user-editable; injected
              into every persona prompt                               [every session]
  CLIENT.md   the business model of THIS client — built by the onboarding interview
              (Hermes-style user modeling), seeds the brain           [strategy/writing]
  MEMORY.md   auto-curated digest of the brain (taste/playbooks/lessons) — the
              human-readable mirror, refreshed every cycle
  memory/     daily journal notes (YYYY-MM-DD.md) written by each autopilot cycle;
              read today+yesterday at session start — the diary
  BOOTSTRAP.md the one-time first-run ritual — deleted when onboarding completes

Files are never overwritten once the operator edits them (scaffold is create-only).
Injection is budget-capped so big files can't blow up prompts. Stdlib only."""
import datetime
from pathlib import Path

_SOUL_BUDGET, _CLIENT_BUDGET = 1800, 2500


def _soul_template(cfg):
    brand = (cfg.get("brand", {}) or {}).get("name", "this site")
    return f"""# SOUL.md — who your SEO employee is  *(edit me — this is read every session)*

**Name:** Scout · **Role:** resident SEO employee for {brand}

**Character:** a senior SEO who has seen enough algorithm updates to be calm about all
of them. Evidence over opinion; the ledger settles arguments. Direct, concise, zero
fluff. Celebrates measured wins, owns misses openly, and says "not yet measurable"
instead of guessing.

**Standards:** answer-first writing · nothing ships without approval · every change is
measured against a holdout · a stale year in a title is a bug · the reader is a person,
not a crawler.

**Boundaries:** never keyword-stuff, never spin content, never buy links, never touch
robots/redirects without flagging blast radius, never claim causation the ledger can't
support, never publish anything the safety gate flags.
"""


def _agents_template(cfg):
    return f"""# AGENTS.md — operating instructions for this workspace  *(read at session start)*

You are the resident SEO employee for **{cfg.get('site', 'this site')}** (persona: SOUL.md,
client model: CLIENT.md, learned memory: MEMORY.md + `brain`).

**Session start ritual:** read SOUL.md · CLIENT.md · MEMORY.md · memory/<today>.md and
<yesterday>.md (the diary) · `preflight` if anything looks unconfigured.

**The loop you serve:** profile → crawl → audit → plan → (approved) ship → measure vs
holdout at +7/28/90d → learn → repeat. `autopilot --daily` runs one cycle; `agent` runs
it forever. You NEVER bypass: the safety gate, the approval queue (`autonomy` mode), or
`personas.system(role, cfg)` (that's how taste + playbooks reach the writing).

**Daily rhythm:** cycle → review queue (approve/decline WITH notes — notes teach the
brain) → check `sitediff`/`anomaly` regressions → log surprises to the journal.
**Weekly:** fresh GSC snapshot · `report --pdf` + `deliver` · read `learn`/`practices`.

**State lives in:** config.json (settings, `config` shows slots) · state/ (blackboard,
brain, deliveries, journal in memory/) · seo.db (ledger) · history/ (snapshots) ·
corpus.json (crawl). Secrets ONLY in .env.

**Escalate to the human:** destructive ops, migrations, anything measuring negative,
and every judgment call the ledger can't settle.
"""


def _bootstrap_template():
    return """# BOOTSTRAP.md — first-run ritual  *(this file deletes itself when onboarding completes)*

Welcome, new employee. In order:
1. `start` — the guided dashboard walks the human through setup (or `wizard --interactive`).
2. The interview answers become CLIENT.md — read it; it's who you work for.
3. `onboard` — baseline the site. `voice` — learn how they already write.
4. First cycle: `autopilot --daily`, then ask the human to approve 2–3 SMALL changes.
5. When BASELINE.md exists and the first change is in the ledger, your probation is over
   — this file disappears and the daily rhythm in AGENTS.md takes over.
"""


def scaffold(cfg, root="."):
    """Create-only: write the identity files that don't exist yet (operator edits win)."""
    root = Path(root)
    made = []
    for name, body in (("SOUL.md", _soul_template(cfg)), ("AGENTS.md", _agents_template(cfg)),
                       ("BOOTSTRAP.md", _bootstrap_template())):
        p = root / name
        if not p.exists():
            p.write_text(body)
            made.append(name)
    (root / "memory").mkdir(exist_ok=True)
    return {"created": made}


def complete_bootstrap(root="."):
    """Onboarding finished → the first-run ritual file removes itself (OpenClaw style)."""
    p = Path(root) / "BOOTSTRAP.md"
    if p.exists():
        p.unlink()
        return True
    return False


# ── CLIENT.md — the business model, from the onboarding interview ────────────
INTERVIEW = [
    ("sells", "What does this business sell, in one sentence?"),
    ("buyer", "Who is the ideal buyer? (role / segment — the person, not 'everyone')"),
    ("conversion", "What does a conversion look like? (demo, signup, purchase, call…)"),
    ("moat", "Why do customers pick you over the alternatives? (the honest reason)"),
    ("nogo", "Topics, claims, or competitors we must NEVER touch in content?"),
    ("capacity", "Roughly how many content changes/week can you review? (drip cap)"),
]


def write_client(cfg, answers, root="."):
    """Interview answers → CLIENT.md + seeded brain facts (the Hermes user model:
    proactive, not learned-by-correction — the strategist knows the business on day 1)."""
    filled = {k: v.strip() for k, v in answers.items() if v and v.strip()}
    if not filled:
        return {"ok": False, "skipped": True}
    labels = dict(INTERVIEW)
    L = [f"# CLIENT.md — who we work for  *(from the onboarding interview — keep me current)*",
         f"\nSite: {cfg.get('site', '')} · interviewed {datetime.date.today().isoformat()}\n"]
    for k, q in INTERVIEW:
        if k in filled:
            L.append(f"**{q}**\n{filled[k]}\n")
    Path(root, "CLIENT.md").write_text("\n".join(L))
    try:
        from . import brain
        if "sells" in filled or "buyer" in filled:
            brain.add(cfg, "fact", f"Business: sells {filled.get('sells', '?')} to "
                                   f"{filled.get('buyer', '?')}; conversion = {filled.get('conversion', '?')}; "
                                   f"differentiator: {filled.get('moat', '?')}",
                      source="onboarding-interview", tag="client-context")
        if "nogo" in filled:
            brain.add(cfg, "preference", f"NEVER touch in content: {filled['nogo']}",
                      source="onboarding-interview", tag="client-nogo")
        if "capacity" in filled:
            brain.add(cfg, "preference", f"Review capacity: {filled['capacity']} changes/week — "
                      "drip the plan accordingly", source="onboarding-interview", tag="client-capacity")
    except Exception:
        pass
    return {"ok": True, "file": "CLIENT.md", "answered": len(filled)}


def soul(cfg, root="."):
    p = Path(root) / "SOUL.md"
    return p.read_text()[:_SOUL_BUDGET] if p.exists() else ""


def client(cfg, root="."):
    p = Path(root) / "CLIENT.md"
    return p.read_text()[:_CLIENT_BUDGET] if p.exists() else ""


# ── MEMORY.md mirror + the daily journal ─────────────────────────────────────
def memory_digest(cfg, root="."):
    """Human-readable curated memory (auto-refreshed each cycle from the brain)."""
    try:
        from . import brain
        b = brain.load(cfg)["entries"]
    except Exception:
        return None
    if not b:
        return None
    lab = {"preference": "Taste", "playbook": "Playbooks", "lesson": "Lessons", "fact": "Facts"}
    L = ["# MEMORY.md — what your employee has learned here  *(auto-curated; source: `brain`)*", ""]
    for kind in ("fact", "preference", "playbook", "lesson"):
        rows = sorted([e for e in b if e["kind"] == kind], key=lambda e: -e["score"])[:6]
        if rows:
            L.append(f"## {lab[kind]}")
            L += [f"- {e['text']}" for e in rows]
            L.append("")
    Path(root, "MEMORY.md").write_text("\n".join(L))
    return "MEMORY.md"


def journal(cfg, lines, root="."):
    """Append today's diary entry (memory/YYYY-MM-DD.md) — the OpenClaw daily note."""
    d = Path(root) / "memory"
    d.mkdir(exist_ok=True)
    p = d / f"{datetime.date.today().isoformat()}.md"
    stamp = datetime.datetime.now().strftime("%H:%M")
    body = (p.read_text() if p.exists() else f"# {datetime.date.today().isoformat()}\n")
    p.write_text(body + f"\n## {stamp}\n" + "\n".join(f"- {l}" for l in lines) + "\n")
    return str(p)


def recent_journal(cfg, root=".", days=2):
    """Today + yesterday's notes — the session-start read."""
    d = Path(root) / "memory"
    out = []
    for i in range(days):
        p = d / f"{(datetime.date.today() - datetime.timedelta(days=i)).isoformat()}.md"
        if p.exists():
            out.append(p.read_text())
    return "\n\n".join(out)
