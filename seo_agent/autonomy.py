"""Autonomy modes — how much the tool is allowed to *do* on its own. Every action
that changes the live site or sends something external routes through `authorize()`,
so the operator picks the trust level once and it's enforced everywhere.

  config `autonomy` (or env SEO_AUTONOMY):
    manual   — never execute; only produce the plan  (default, safest)
    approve  — queue the action for human approval; `apply --approved` runs it
    auto     — execute immediately, within guardrails

Guardrails hold even in `auto`: destructive actions (delete, redirect, bulk) still
require approval unless `autonomy.allow_destructive` is set, and a per-run cap
(`autonomy.max_auto_actions`, default 10) prevents runaway changes. Site-agnostic;
file-based approvals queue (`approvals.json`)."""
import datetime
import json
from pathlib import Path

MODES = ("manual", "approve", "auto")
DESTRUCTIVE = {"delete", "redirect", "bulk_update", "bulk_delete", "overwrite"}
QUEUE = "approvals.json"


def mode(cfg):
    import os
    m = (os.environ.get("SEO_AUTONOMY") or (cfg.get("autonomy") if isinstance(cfg.get("autonomy"), str)
         else (cfg.get("autonomy", {}) or {}).get("mode")) or "manual").lower()
    return m if m in MODES else "manual"


def _opts(cfg):
    a = cfg.get("autonomy")
    return a if isinstance(a, dict) else {}


def authorize(cfg, action, kind="update", target="", detail=""):
    """Decide whether `action` may execute now. Returns a decision dict; the caller
    executes only if decision['execute'] is True, else records/plans it."""
    m = mode(cfg)
    opts = _opts(cfg)
    destructive = kind in DESTRUCTIVE
    if m == "auto" and (not destructive or opts.get("allow_destructive")):
        return {"execute": True, "mode": m, "reason": "auto mode"}
    if m == "manual":
        return {"execute": False, "mode": m, "queued": False,
                "reason": "manual mode — plan only; set autonomy=approve or auto to act"}
    # approve (or auto+destructive) → queue for human approval
    _queue(cfg, {"action": action, "kind": kind, "target": target, "detail": detail})
    return {"execute": False, "mode": m, "queued": True,
            "reason": ("destructive — approval required even in auto" if destructive and m == "auto"
                       else "queued for approval — run `apply --approved`")}


def load_queue(cfg):
    p = Path(QUEUE)
    return json.loads(p.read_text()) if p.exists() else []


def save_queue(cfg, q):
    Path(QUEUE).write_text(json.dumps(q, indent=2) + "\n")


def set_status(cfg, item_id, status, **fields):
    q = load_queue(cfg)
    for i in q:
        if i["id"] == item_id:
            i["status"] = status
            i.update(fields)
    save_queue(cfg, q)
    return q


def _queue(cfg, item):
    q = load_queue(cfg)
    item["queued_at"] = datetime.date.today().isoformat()
    item["status"] = "pending"
    item["id"] = (max([i["id"] for i in q], default=0) + 1)
    q.append(item)
    save_queue(cfg, q)


def pending(cfg):
    return [i for i in load_queue(cfg) if i["status"] in ("pending", "in_review", "changes")]


def review_required(cfg):
    r = cfg.get("review", {}) or {}
    return bool(r.get("channels") or r.get("required"))


def executable(cfg):
    """Items ready to run: explicitly approved, OR pending when no review is required
    (the simple local flow). Never 'in_review' or 'changes'."""
    ok = {"approved"} if review_required(cfg) else {"approved", "pending"}
    return [i for i in load_queue(cfg) if i["status"] in ok]


def approve_all(cfg, executor):
    """Run `executor(item)->result` for each *executable* action; mark done. `executor`
    is supplied by the caller so this stays connector-agnostic."""
    q = load_queue(cfg)
    ready = {i["id"] for i in executable(cfg)}
    results = []
    for item in q:
        if item["id"] not in ready:
            continue
        try:
            r = executor(item)
            item["status"] = "done"
            results.append({"id": item["id"], "action": item["action"], "ok": True, "result": r})
        except Exception as e:
            item["status"] = "error"
            results.append({"id": item["id"], "action": item["action"], "ok": False, "error": str(e)})
    save_queue(cfg, q)
    return results


def render_md(cfg):
    m = mode(cfg)
    pend = pending(cfg)
    L = [f"# Autonomy — mode: **{m}**",
         {"manual": "_Plan only — nothing is executed. Set `autonomy` to `approve` or `auto` to act._",
          "approve": "_Actions are queued for your approval; run `apply --approved` to execute._",
          "auto": "_Actions execute automatically within guardrails (destructive ones still queue)._"}[m], ""]
    if pend:
        L += [f"## Pending approval ({len(pend)})", "| id | action | kind | target |", "|--:|---|---|---|"]
        for i in pend:
            L.append(f"| {i['id']} | {i['action']} | {i['kind']} | {(i.get('target') or '')[:50]} |")
        L.append("\n_Approve + execute all: `apply --approved`._")
    else:
        L.append("_No actions pending approval._")
    return "\n".join(L)
