"""Agentic remediation planner — turns audit findings into an ordered, PR-sized work
plan mapping each issue class to the fix action + the command that produces it. It
does NOT auto-apply changes: the guardrail (and the product promise) is human-in-the-
loop review, so it emits the plan and the agent applies fixes as reviewed PRs, one
drip at a time. Chains the existing modules; site-agnostic."""
from . import audit

# issue category → (how to fix, which command surfaces the fix, is it safe to batch)
_PLAYBOOK = {
    "meta": ("Rewrite missing/duplicate titles + metas (agent writes them)", "retitle", False),
    "headings": ("Collapse multiple H1s to one; demote section headers to H2", "audit", True),
    "duplicate": ("Consolidate cannibalized cluster; 301 the losers into the winner", "consolidate", False),
    "links": ("Add internal links to orphan/under-linked pages", "autolink", True),
    "a11y": ("Add alt text; fix heading-level skips", "audit", True),
    "sitemap": ("Fix lastmod / drop noindex+404 URLs from the sitemap", "sitemap", True),
    "robots": ("Fix robots.txt / add sitemap reference", "audit", False),
    "schema": ("Generate + validate structured data", "schema", True),
    "speed": ("Address the worst Core Web Vital (usually INP)", "speed", False),
}
_SEV = {"high": 0, "med": 1, "low": 2}


def plan(cfg):
    rep = audit.report(cfg)
    findings = rep.get("findings", [])
    tasks = []
    for f in sorted(findings, key=lambda x: _SEV.get(x.get("sev"), 3)):
        cat = f.get("cat", "other")
        fix, cmd, batchable = _PLAYBOOK.get(cat, ("Review manually", "audit", False))
        tasks.append({"sev": f.get("sev"), "cat": cat, "issue": f.get("msg"),
                      "fix": fix, "cmd": cmd, "batchable": batchable, "target": f.get("url")})
    return {"counts": rep.get("counts", {}), "tasks": tasks}


def render_md(cfg, r):
    L = [f"# Remediation plan — {cfg.get('site','site')}",
         "Ordered by severity. **Nothing is auto-applied** — apply as reviewed PRs, drip cadence.",
         f"\nSeverity: {r['counts'].get('high','?')} high · {r['counts'].get('med','?')} med · "
         f"{r['counts'].get('low','?')} low", "",
         "| # | sev | issue | fix | via | batch |", "|--:|---|---|---|---|:--:|"]
    for i, t in enumerate(r["tasks"][:40], 1):
        L.append(f"| {i} | {t['sev']} | {(t['issue'] or '')[:60]} | {t['fix']} | `{t['cmd']}` | "
                 f"{'✓' if t['batchable'] else '—'} |")
    L.append("\n_Batchable (✓) fixes are low-risk template changes; the rest need a human editorial "
             "call. Generated content stays gated behind the safety gate + review._")
    return "\n".join(L)
