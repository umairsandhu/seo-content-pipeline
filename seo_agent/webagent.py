"""Physical web control — drive a real browser to operate sites that have no clean
API (legacy CMS admins, dashboards, GBP, directory listings). Two paths, both
site-agnostic:

1. **Scripted (Playwright).** Run a declarative task — goto / fill / click / wait /
   screenshot / extract — headless or headed. Mutating tasks route through
   `autonomy.authorize()`. Needs `pip install playwright && playwright install chromium`.

2. **Computer-use (MCP).** When a task needs judgment (a novel admin UI), expose this
   tool's data over its MCP server AND connect a computer-use MCP server; the agent
   then *sees* the screen and clicks. This module returns a computer-use **task packet**
   (goal + context + guardrails) for that agent to execute when Playwright isn't enough.

Read-only tasks run freely; anything that submits/saves is gated by autonomy."""
from . import autonomy, render

MUTATING = {"click", "fill", "submit", "press", "select"}


def available():
    return render.available()


def run_task(cfg, task, headed=False):
    """task = {"name":..., "steps":[{"action":"goto","url":..}, {"action":"fill","selector":..,"value":..}, ...]}
    Actions: goto · fill · click · press · wait · screenshot(path) · extract(selector→text)."""
    steps = task.get("steps", [])
    mutates = any(s.get("action") in MUTATING for s in steps)
    if mutates:
        dec = autonomy.authorize(cfg, f"web task: {task.get('name','')}", kind="update",
                                 target=next((s.get("url") for s in steps if s.get("action") == "goto"), ""))
        if not dec["execute"]:
            return {"status": "queued" if dec.get("queued") else "planned", "reason": dec["reason"], "task": task}
    if not available():
        return {"status": "needs_setup", "error": "pip install playwright && playwright install chromium",
                "task": task, "computer_use": computer_use_packet(cfg, task)}
    from playwright.sync_api import sync_playwright
    log, extracted = [], {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        page = browser.new_page()
        try:
            for s in steps:
                a = s.get("action")
                if a == "goto":
                    page.goto(s["url"], timeout=30000); log.append(f"goto {s['url']}")
                elif a == "fill":
                    page.fill(s["selector"], s.get("value", "")); log.append(f"fill {s['selector']}")
                elif a == "click":
                    page.click(s["selector"]); log.append(f"click {s['selector']}")
                elif a == "press":
                    page.press(s.get("selector", "body"), s["key"]); log.append(f"press {s['key']}")
                elif a == "wait":
                    page.wait_for_timeout(int(s.get("ms", 1000)))
                elif a == "screenshot":
                    page.screenshot(path=s.get("path", "web-task.png")); log.append("screenshot")
                elif a == "extract":
                    extracted[s["selector"]] = (page.text_content(s["selector"]) or "").strip()
        except Exception as e:
            browser.close()
            return {"status": "error", "error": str(e), "log": log}
        browser.close()
    return {"status": "done", "log": log, "extracted": extracted}


def computer_use_packet(cfg, task):
    """A task brief for a computer-use MCP agent to execute with screen + mouse/keyboard."""
    return (f"# Computer-use task — {task.get('name','web task')}\n\n"
            f"Site: {cfg.get('site','')}. Autonomy: {autonomy.mode(cfg)}.\n\n"
            f"Goal: {task.get('goal', task.get('name',''))}\n\n"
            "Operate the browser to accomplish the goal. Guardrails: do not submit/save any change "
            "unless autonomy is `auto` or the change was approved; verify each screen before acting; "
            "stop and report if a login, payment, or destructive confirmation is requested unexpectedly. "
            "Return: what you did, screenshots of key states, and the final result.")


def render_md(cfg, r):
    st = r["status"]
    if st == "done":
        return "# Web task ✅\n\n- " + "\n- ".join(r["log"]) + (
            ("\n\n## Extracted\n" + "\n".join(f"- {k}: {v[:80]}" for k, v in r["extracted"].items()))
            if r.get("extracted") else "")
    if st == "needs_setup":
        return (f"# Web task — Playwright not installed\n\n_{r['error']}_\n\n"
                "Or drive it with a computer-use MCP agent using this packet:\n\n" + r["computer_use"])
    if st in ("queued", "planned"):
        return f"# Web task — {st}\n\n_{r['reason']}_"
    return f"# Web task failed\n\n- {r.get('error')}"
