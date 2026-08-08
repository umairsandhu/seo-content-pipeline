"""Always-on agent mode — the OpenClaw shape, scoped to SEO. One long-running local
process instead of cron lines: it keeps a heartbeat, polls your review channels,
pushes NEW high-severity anomalies to Slack/WhatsApp/email the tick they appear,
runs the full autopilot cycle once a day at your hour, and delivers the weekly
report — all through the same autonomy/review gates as the CLI.

    python -m seo_agent agent            # start it in the workspace (Ctrl-C to stop)
    config: {"agent": {"interval": 600, "hour": 8, "report_weekday": 4}}   # Fri=4

Safe to kill and restart any time — schedule state lives in state/agent.json, so a
restart never double-runs the day. Phase 2 (roadmap): two-way chat control — reply
"approve 3", "status", "diagnose" from Slack/WhatsApp. Stdlib only."""
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

from . import state


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _defaults(cfg):
    a = cfg.get("agent", {}) or {}
    return {"interval": int(a.get("interval", 600)), "hour": int(a.get("hour", 8)),
            "report_weekday": int(a.get("report_weekday", 4)),
            "sf_crawl": bool(a.get("sf_crawl", False)),
            "sf_crawl_weekday": int(a.get("sf_crawl_weekday", 0))}  # Monday


# ── background process management (pidfile in state/) ───────────────────────
def _pidfile(cfg):
    d = Path(cfg.get("state_dir", "state"))
    d.mkdir(parents=True, exist_ok=True)
    return d / "agent.pid"


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def status(cfg):
    p = _pidfile(cfg)
    pid = int(p.read_text()) if p.exists() and p.read_text().strip().isdigit() else None
    running = bool(pid and _alive(pid))
    st = state.read(cfg, "agent", {}) or {}
    return {"running": running, "pid": pid if running else None,
            "last_daily": st.get("last_daily", "—"), "last_weekly": st.get("last_weekly", "—")}


def start_background(cfg, interval=None):
    """Detach the agent as a background process (survives closing the terminal;
    for surviving reboots use --install)."""
    s = status(cfg)
    if s["running"]:
        return {"ok": False, "error": f"already running (pid {s['pid']}) — `agent --stop` first"}
    log = open("agent.log", "a")
    args = [sys.executable, "-m", "seo_agent", "agent"]
    if interval:
        args += ["--interval", str(interval)]
    p = subprocess.Popen(args, stdout=log, stderr=log, start_new_session=True, cwd=os.getcwd())
    return {"ok": True, "pid": p.pid, "log": "agent.log",
            "note": "running in the background — `agent --status` / `agent --stop`"}


def stop(cfg):
    s = status(cfg)
    if not s["running"]:
        return {"ok": False, "error": "not running"}
    os.kill(s["pid"], 15)
    _pidfile(cfg).unlink(missing_ok=True)
    return {"ok": True, "stopped": s["pid"]}


def install_launchd(cfg, interval=None):
    """macOS: install a LaunchAgent so the agent starts at login and survives
    reboots — the real 'always-on' (Linux: use a systemd user unit, see docs)."""
    if sys.platform != "darwin":
        return {"ok": False, "error": "launchd is macOS-only — on Linux use a systemd user unit "
                                      "(ExecStart=python3 -m seo_agent agent, WorkingDirectory=<workspace>)"}
    from urllib.parse import urlparse
    slug = (urlparse(cfg.get("site") or "").netloc.replace("www.", "").replace(".", "-")
            or Path.cwd().name)
    label = f"com.seo-agent.{slug}"
    args = [sys.executable, "-m", "seo_agent", "agent"] + (["--interval", str(interval)] if interval else [])
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key><array>{''.join(f'<string>{a}</string>' for a in args)}</array>
  <key>WorkingDirectory</key><string>{os.getcwd()}</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{os.getcwd()}/agent.log</string>
  <key>StandardErrorPath</key><string>{os.getcwd()}/agent.log</string>
</dict></plist>
"""
    dest = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(plist)
    _safe(lambda: subprocess.run(["launchctl", "unload", str(dest)], capture_output=True))
    subprocess.run(["launchctl", "load", "-w", str(dest)], capture_output=True)
    return {"ok": True, "plist": str(dest), "label": label,
            "note": "starts at login, restarts if it dies — remove with "
                    f"`launchctl unload -w {dest}` + delete the plist"}


def _actions(cfg):
    """The real side-effects, injectable for tests."""
    from . import anomaly, autopilot, channels, deliver, report, review
    return {
        "poll": lambda: review.poll(cfg),
        "detect": lambda: anomaly.detect(cfg),
        "alert": lambda text: channels.send(cfg, text, subject="SEO agent alert"),
        "daily": lambda: autopilot.cycle(cfg, cadence="daily", deliver=True),
        "weekly": lambda: (lambda html: deliver.deliver(
            cfg, [report.to_pdf(html)[0] or html], note="Weekly SEO report from your local agent"))(
            report.build(cfg)),
    }


def tick(cfg, do=None, now=None):
    """One heartbeat. Returns the actions taken (for logs + tests); schedule state
    persists in state/agent.json so restarts never double-run."""
    do = do or _actions(cfg)
    now = now or datetime.datetime.now()
    opts = _defaults(cfg)
    st = state.read(cfg, "agent", None) or {"last_daily": "", "last_weekly": "", "seen_alerts": []}
    took = []

    _safe(do["poll"])  # 1 · ingest approvals / CHANGES notes / FEEDBACK replies

    # 1b · auto-import any new Screaming Frog exports dropped in sf-exports/
    sf = _safe(do.get("sf") or (lambda: __import__("seo_agent.sfimport", fromlist=["x"]).auto_import(cfg)))
    if sf and not sf.get("error"):
        took.append(f"imported Screaming Frog export ({sf.get('pages', '?')} pages, {sf.get('mode')})")

    # 2 · NEW high-sev anomalies alert immediately (dedupe on message)
    for a in _safe(do["detect"]) or []:
        if a.get("sev") == "high" and a["msg"] not in st["seen_alerts"]:
            _safe(lambda: do["alert"](f"🔴 {a.get('kind', 'alert')}: {a['msg']}"))
            st["seen_alerts"] = (st["seen_alerts"] + [a["msg"]])[-50:]
            took.append(f"alert: {a['msg'][:60]}")

    # 3 · the daily autopilot cycle, once per day at/after the configured hour
    today = now.date().isoformat()
    if st["last_daily"] != today and now.hour >= opts["hour"]:
        _safe(do["daily"])
        st["last_daily"] = today
        took.append("daily autopilot cycle")

    # 4 · weekly report + delivery (email/Drive), once per ISO week on report day
    week = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]}"
    if now.weekday() == opts["report_weekday"] and st["last_weekly"] != week \
            and now.hour >= opts["hour"]:
        _safe(do["weekly"])
        st["last_weekly"] = week
        took.append("weekly report delivered")

    # 5 · weekly Screaming Frog headless pull (opt-in: agent.sf_crawl = true)
    if opts["sf_crawl"] and now.weekday() == opts["sf_crawl_weekday"] \
            and st.get("last_sf") != week and now.hour >= opts["hour"]:
        r = _safe(do.get("sf_crawl") or (lambda: __import__("seo_agent.sfimport", fromlist=["x"]).crawl(cfg)))
        st["last_sf"] = week
        took.append("Screaming Frog crawl pulled" if r and not r.get("error")
                    else f"SF crawl skipped ({(r or {}).get('error', 'unknown')[:60]})")

    state.write(cfg, "agent", st)
    return took


def run(cfg, interval=None):
    opts = _defaults(cfg)
    interval = interval or opts["interval"]
    site = cfg.get("site", "site")
    _pidfile(cfg).write_text(str(os.getpid()))
    print(f"🤖 SEO agent watching {site} — daily cycle at {opts['hour']:02d}:00, weekly report "
          f"on weekday {opts['report_weekday']}, heartbeat every {interval}s. Ctrl-C to stop.\n"
          f"   (dashboard: `serve` in another terminal · background: `agent --background` · "
          f"boot-persistent: `agent --install`)")
    try:
        while True:
            took = tick(cfg)
            stamp = datetime.datetime.now().strftime("%H:%M")
            print(f"  [{stamp}] " + ("; ".join(took) if took else "quiet — watching"), flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nagent stopped. (state kept — restart any time)")
    finally:
        _pidfile(cfg).unlink(missing_ok=True)
