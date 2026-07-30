"""Deliver work to the person who buys/uses the tool — and learn from what they say
back. Two local-first channels (nothing hosted):

  email — via `notify` (SMTP / Resend / SendGrid), the default
  drive — upload into a Google Drive folder they gave you:
            · service account (reuse the GSC one: share the folder with its email,
              set drive.folder_id; creds = drive.credentials or gsc_credentials)
            · or an `rclone` remote (drive.rclone_remote = "gdrive:SEO reports")

Every delivery is logged to state/deliveries.json. When the client gets back —
an email reply (`review --poll` picks up "FEEDBACK …"), or `feedback "…"` typed
straight in — the note attaches to the last delivery and distills into the brain
as client TASTE, so the next report/draft matches how they like to work. That
closes the loop: deliver → they react → we learn → output improves."""
import datetime
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from . import notify, state


def _log(cfg):
    return state.read(cfg, "deliveries", []) or []


def deliver(cfg, files, note="", to=None):
    """Send files (report PDF/HTML, drafts, plans) to the client via every configured
    channel. Returns per-channel results + the delivery record."""
    files = [f for f in (files if isinstance(files, list) else [files]) if Path(f).exists()]
    if not files:
        return {"ok": False, "error": "no existing files to deliver (build one: `report --pdf`)"}
    res = {}
    if (cfg.get("report", {}) or {}).get("email_to") or to:
        body = note or (f"Latest SEO deliverables for {cfg.get('site', 'your site')} attached. "
                        "Reply with feedback — it is read and applied to the next round "
                        "(start the line with FEEDBACK so it's picked up automatically).")
        res["email"] = notify.send(cfg, to, f"SEO deliverables — {cfg.get('site', '')}", body, attachments=files)
    dr = _drive(cfg, files)
    if dr:
        res["drive"] = dr
    if not res:
        res["dry_run"] = {"ok": False, "error":
                          "no delivery channel — set report.email_to (+ SMTP_*/RESEND_API_KEY) "
                          "and/or drive.folder_id / drive.rclone_remote"}
    log = _log(cfg)
    rec = {"id": (max([d["id"] for d in log], default=0) + 1),
           "date": datetime.date.today().isoformat(), "files": [str(f) for f in files],
           "channels": {k: bool(v.get("ok")) for k, v in res.items()},
           "links": [v.get("link") for v in res.values() if v.get("link")],
           "note": note, "feedback": None}
    log.append(rec)
    state.write(cfg, "deliveries", log)
    return {"ok": any(v.get("ok") for v in res.values()), "delivery": rec, "results": res}


# ── Google Drive ─────────────────────────────────────────────────────────────
def _drive(cfg, files):
    d = cfg.get("drive", {}) or {}
    if d.get("rclone_remote") and shutil.which("rclone"):
        try:
            for f in files:
                subprocess.run(["rclone", "copy", str(f), d["rclone_remote"]],
                               check=True, capture_output=True, timeout=120)
            return {"ok": True, "transport": "rclone", "remote": d["rclone_remote"],
                    "files": [Path(f).name for f in files]}
        except Exception as e:
            return {"ok": False, "transport": "rclone", "error": str(e)}
    if not d.get("folder_id"):
        return None  # Drive not configured — that's fine, email may still run
    tok = _drive_token(cfg)
    if not tok:
        return {"ok": False, "transport": "drive-api",
                "error": "no Google credentials — set drive.credentials (or reuse gsc_credentials) "
                         "and share the folder with the service-account email"}
    out = {"ok": True, "transport": "drive-api", "uploaded": [], "link": None}
    for f in files:
        try:
            out["uploaded"].append(_drive_upload(tok, d["folder_id"], Path(f)))
        except Exception as e:
            out["ok"] = False
            out["error"] = f"{Path(f).name}: {e}"
    if out["uploaded"]:
        out["link"] = out["uploaded"][0].get("webViewLink")
    return out


def _drive_token(cfg):
    cred = (cfg.get("drive", {}) or {}).get("credentials") or cfg.get("gsc_credentials")
    if not cred or not Path(cred).exists():
        return None
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests
        creds = service_account.Credentials.from_service_account_file(
            cred, scopes=["https://www.googleapis.com/auth/drive.file"])
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token
    except Exception:
        return None


_MIME = {".pdf": "application/pdf", ".html": "text/html", ".md": "text/markdown",
         ".json": "application/json", ".csv": "text/csv"}


def _drive_upload(token, folder_id, path):
    """Multipart upload (stdlib) → file id + webViewLink."""
    meta = json.dumps({"name": path.name, "parents": [folder_id]}).encode()
    mime = _MIME.get(path.suffix.lower(), "application/octet-stream")
    boundary = b"seoagentboundary31337"
    body = (b"--" + boundary + b"\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
            + meta + b"\r\n--" + boundary + b"\r\nContent-Type: " + mime.encode() + b"\r\n\r\n"
            + path.read_bytes() + b"\r\n--" + boundary + b"--")
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        "&supportsAllDrives=true&fields=id,webViewLink",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": f"multipart/related; boundary={boundary.decode()}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


# ── the feedback half of the loop ────────────────────────────────────────────
def feedback(cfg, text, about=""):
    """Record what the client said about delivered work → attaches to the latest
    delivery and distills into the brain as taste. This is how the tool learns how
    someone works — every reply makes the next deliverable more 'them'."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty feedback"}
    log = _log(cfg)
    attached = None
    for d in reversed(log):  # newest delivery without feedback yet
        if not d.get("feedback"):
            d["feedback"] = text
            d["feedback_date"] = datetime.date.today().isoformat()
            attached = d["id"]
            break
    state.write(cfg, "deliveries", log)
    from . import brain
    brain.add(cfg, "preference",
              f"Client feedback{(' on ' + about) if about else ''}: {text}",
              source="client-feedback", tag=f"dl-{attached}" if attached else "")
    brain.cycle(cfg)
    return {"ok": True, "attached_to_delivery": attached,
            "learned": "distilled into the brain as client taste — applied to every future draft/report"}


def render_md(cfg, r=None):
    log = _log(cfg)
    L = ["# Deliveries — what went out, and what the client said"]
    if r:
        d = r.get("delivery", {})
        ok = "✅ delivered" if r.get("ok") else "⚠ not delivered"
        L += ["", f"{ok} #{d.get('id')} — {', '.join(Path(f).name for f in d.get('files', []))} "
              f"via {', '.join(k for k, v in d.get('channels', {}).items() if v) or 'no channel'}"]
        for k, v in (r.get("results") or {}).items():
            if not v.get("ok"):
                L.append(f"  - {k}: {v.get('error', 'not configured')}")
            elif v.get("link"):
                L.append(f"  - {k}: {v['link']}")
    if log:
        L += ["", "| # | date | files | channels | feedback |", "|--:|---|---|---|---|"]
        for d in log[-10:][::-1]:
            L.append(f"| {d['id']} | {d['date']} | {', '.join(Path(f).name for f in d['files'])[:40]} | "
                     f"{', '.join(k for k, v in d['channels'].items() if v) or '—'} | "
                     f"{(d.get('feedback') or '—')[:48]} |")
    else:
        L += ["", "_Nothing delivered yet. `deliver report.pdf` emails it and/or drops it in the "
              "client's Drive folder._"]
    L += ["", "_Client replies = learning signal: `feedback \"their words\"` (or an email reply "
          "starting with FEEDBACK, picked up by `review --poll`) → distilled into the brain as "
          "taste → every future draft/report matches how they work._"]
    return "\n".join(L)
