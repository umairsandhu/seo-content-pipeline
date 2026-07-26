"""Human-in-the-loop review across channels. Any queued change or draft can be sent to
reviewers on CLI / email / Slack / Mattermost / WhatsApp; they reply **approve** or
**request changes with notes**, and only APPROVED items are pushed by `apply --approved`.

Inbound today is poll-based (no server needed): `review --poll` reads email replies
(IMAP) and a local `review-responses.json` drop-file for "APPROVE <id>" / "CHANGES <id>
<notes>". The standalone app will add real-time webhooks (Slack/WhatsApp). The local
reviewer can always just run `approve <id>` / `changes <id> "notes"`. Site-agnostic."""
import json
import os
import re
from pathlib import Path

from . import autonomy, channels

RESP_FILE = "review-responses.json"
_APPROVE = re.compile(r"\bapprove[d]?\b\s*#?(\d+)", re.I)
_CHANGES = re.compile(r"\bchanges?\b\s*#?(\d+)\s*(.*)", re.I | re.S)


def request(cfg, ids=None):
    """Send pending items to reviewers and mark them in_review. Returns per-item results."""
    q = autonomy.load_queue(cfg)
    items = [i for i in q if i["status"] == "pending" and (ids is None or i["id"] in ids)]
    out = []
    for it in items:
        msg = _message(cfg, it)
        res = channels.send(cfg, msg, subject=f"SEO review #{it['id']} — {it['action'][:60]}")
        autonomy.set_status(cfg, it["id"], "in_review")
        out.append({"id": it["id"], "sent": {c: r.get("ok") or r.get("dry_run") for c, r in res.items()}})
    return {"requested": out, "count": len(out)}


def _message(cfg, it):
    return (f"*SEO review needed — #{it['id']}*\n"
            f"Action: {it['action']}\nType: {it['kind']}\nTarget: {it.get('target','')}\n"
            f"Detail: {it.get('detail','')}\n\n"
            f"Reply to approve or request changes:\n"
            f"  • `APPROVE {it['id']}`\n"
            f"  • `CHANGES {it['id']} <your notes>`\n"
            f"(or run `apply --approved` after approving locally with `approve {it['id']}`)")


def respond(cfg, item_id, decision, feedback=""):
    status = "approved" if decision.lower().startswith("appr") else "changes"
    autonomy.set_status(cfg, int(item_id), status, feedback=feedback)
    return {"id": int(item_id), "status": status, "feedback": feedback}


def poll(cfg):
    """Ingest inbound approvals from email (IMAP) and the local drop-file."""
    applied = []
    # 1) local drop-file: [{id, decision:"approve"|"changes", feedback}]
    p = Path(RESP_FILE)
    if p.exists():
        for r in json.loads(p.read_text() or "[]"):
            respond(cfg, r["id"], r.get("decision", "approve"), r.get("feedback", ""))
            applied.append(r["id"])
    # 2) email replies via IMAP
    applied += _poll_email(cfg)
    return {"processed": applied, "count": len(applied)}


def _poll_email(cfg):
    host = os.environ.get("IMAP_HOST")
    if not host:
        return []
    import imaplib
    import email as emaillib
    done = []
    try:
        M = imaplib.IMAP4_SSL(host, int(os.environ.get("IMAP_PORT", 993)))
        M.login(os.environ.get("IMAP_USER", ""), os.environ.get("IMAP_PASSWORD", ""))
        M.select("INBOX")
        _typ, data = M.search(None, "UNSEEN")
        for num in data[0].split():
            _t, msgdata = M.fetch(num, "(RFC822)")
            body = _text(emaillib.message_from_bytes(msgdata[0][1]))
            for m in _APPROVE.finditer(body):
                respond(cfg, m.group(1), "approve"); done.append(int(m.group(1)))
            for m in _CHANGES.finditer(body):
                respond(cfg, m.group(1), "changes", (m.group(2) or "").strip()[:500]); done.append(int(m.group(1)))
        M.logout()
    except Exception:
        return done
    return done


def _text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", "ignore")
        return ""
    return (msg.get_payload(decode=True) or b"").decode("utf-8", "ignore")


_ICON = {"pending": "○", "in_review": "⏳", "approved": "✅", "changes": "✏️", "done": "☑", "error": "🔴"}


def status_md(cfg):
    q = autonomy.load_queue(cfg)
    active = [i for i in q if i["status"] != "done"]
    L = [f"# Review queue — autonomy: {autonomy.mode(cfg)}"
         + ("  ·  review channels: " + ", ".join((cfg.get('review', {}) or {}).get('channels', []) or channels.configured(cfg) or ['cli']))]
    if not active:
        return "\n".join(L + ["", "_Nothing awaiting review._"])
    L += ["", "| id | status | action | notes |", "|--:|---|---|---|"]
    for i in active:
        L.append(f"| {i['id']} | {_ICON.get(i['status'],'?')} {i['status']} | {i['action'][:44]} | {(i.get('feedback') or '')[:40]} |")
    L += ["", "_`review` (send to reviewers) · `review --poll` (ingest replies) · "
          "`approve <id>` / `changes <id> \"notes\"` · `apply --approved` (push approved)._"]
    return "\n".join(L)
