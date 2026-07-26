"""Durable job queue + scheduler (SQLite, stdlib). AI-visibility runs, renders, batch
drafts and outreach are long-running and rate-limited; a queue lets `run`/`mcp` fan
work out with retries and interval scheduling instead of blocking. Portable — one
`jobs.db` file, no broker. Site-agnostic.

    enqueue(cfg, "aivis")                 # one-off
    enqueue(cfg, "gsc", every_hours=168)  # weekly recurring
    due(cfg) / mark(cfg, id, "done")      # a worker/cron drains it
"""
import datetime
import json
import sqlite3
from pathlib import Path


def _con(cfg):
    con = sqlite3.connect(str(Path(cfg.get("jobs_path", "jobs.db"))))
    con.execute("CREATE TABLE IF NOT EXISTS job("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, cmd TEXT, args TEXT, status TEXT, "
                "attempts INTEGER DEFAULT 0, every_hours REAL, next_run TEXT, last_run TEXT, note TEXT)")
    return con


def _now():
    # scripts can't call datetime.now() in some sandboxes; jobs run in the CLI, where it's fine
    return datetime.datetime.utcnow()


def enqueue(cfg, cmd, args=None, every_hours=None, run_at=None):
    con = _con(cfg)
    nxt = (run_at or _now()).isoformat() if isinstance(run_at, datetime.datetime) else (run_at or _now().isoformat())
    with con:
        cur = con.execute("INSERT INTO job(cmd,args,status,every_hours,next_run) VALUES (?,?,?,?,?)",
                          (cmd, json.dumps(args or {}), "queued", every_hours, nxt))
    con.close()
    return cur.lastrowid


def due(cfg):
    con = _con(cfg)
    now = _now().isoformat()
    rows = con.execute("SELECT id,cmd,args,attempts,every_hours FROM job "
                       "WHERE status IN ('queued','scheduled') AND next_run<=? ORDER BY next_run", (now,)).fetchall()
    con.close()
    return [{"id": r[0], "cmd": r[1], "args": json.loads(r[2] or "{}"),
             "attempts": r[3], "every_hours": r[4]} for r in rows]


def mark(cfg, job_id, status, note=""):
    con = _con(cfg)
    with con:
        row = con.execute("SELECT every_hours FROM job WHERE id=?", (job_id,)).fetchone()
        every = row[0] if row else None
        if status == "done" and every:  # reschedule recurring jobs
            nxt = (_now() + datetime.timedelta(hours=every)).isoformat()
            con.execute("UPDATE job SET status='scheduled', next_run=?, last_run=?, note=? WHERE id=?",
                        (nxt, _now().isoformat(), note, job_id))
        else:
            con.execute("UPDATE job SET status=?, attempts=attempts+1, last_run=?, note=? WHERE id=?",
                        (status, _now().isoformat(), note, job_id))
    con.close()


def listing(cfg):
    con = _con(cfg)
    rows = con.execute("SELECT id,cmd,status,attempts,every_hours,next_run FROM job ORDER BY next_run").fetchall()
    con.close()
    return [{"id": r[0], "cmd": r[1], "status": r[2], "attempts": r[3],
             "every_hours": r[4], "next_run": r[5]} for r in rows]


def render_md(cfg):
    rows = listing(cfg)
    if not rows:
        return "# Job queue\n\n_empty — `enqueue` work or schedule recurring runs._"
    L = ["# Job queue", "| id | cmd | status | attempts | every | next |", "|--:|---|---|--:|--:|---|"]
    for r in rows:
        L.append(f"| {r['id']} | {r['cmd']} | {r['status']} | {r['attempts']} | "
                 f"{(str(r['every_hours'])+'h') if r['every_hours'] else '—'} | {r['next_run'][:16]} |")
    return "\n".join(L)
