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
import time

from . import state


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _defaults(cfg):
    a = cfg.get("agent", {}) or {}
    return {"interval": int(a.get("interval", 600)), "hour": int(a.get("hour", 8)),
            "report_weekday": int(a.get("report_weekday", 4))}


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

    state.write(cfg, "agent", st)
    return took


def run(cfg, interval=None):
    opts = _defaults(cfg)
    interval = interval or opts["interval"]
    site = cfg.get("site", "site")
    print(f"🤖 SEO agent watching {site} — daily cycle at {opts['hour']:02d}:00, weekly report "
          f"on weekday {opts['report_weekday']}, heartbeat every {interval}s. Ctrl-C to stop.\n"
          f"   (dashboard: `serve` in another terminal · this replaces the cron lines)")
    try:
        while True:
            took = tick(cfg)
            stamp = datetime.datetime.now().strftime("%H:%M")
            print(f"  [{stamp}] " + ("; ".join(took) if took else "quiet — watching"))
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nagent stopped. (state kept — restart any time)")
