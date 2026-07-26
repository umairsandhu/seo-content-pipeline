"""Multi-channel messaging — deliver digests, review requests, and alerts wherever the
team lives: CLI, email, Slack, Mattermost, or WhatsApp. One `send()`; each channel
lights up per configured webhook/token and degrades to a dry-run that says what to set.

Outbound only — inbound review replies are handled by `review.poll` (email/IMAP now,
webhooks in the standalone app). Site-agnostic; stdlib (urllib) + `notify` for email."""
import json
import os
import urllib.request

from . import notify


def configured(cfg):
    ch = []
    if os.environ.get("SLACK_WEBHOOK_URL") or os.environ.get("SLACK_BOT_TOKEN"):
        ch.append("slack")
    if os.environ.get("MATTERMOST_WEBHOOK_URL"):
        ch.append("mattermost")
    if os.environ.get("WHATSAPP_TOKEN") and os.environ.get("WHATSAPP_PHONE_ID"):
        ch.append("whatsapp")
    if (os.environ.get("SMTP_HOST") or os.environ.get("RESEND_API_KEY")
            or os.environ.get("SENDGRID_API_KEY")):
        ch.append("email")
    return ch


def send(cfg, text, channels=None, subject="SEO pipeline", attachments=None, to=None):
    channels = channels or (cfg.get("review", {}) or {}).get("channels") or configured(cfg) or ["cli"]
    return {c: _dispatch(cfg, c, text, subject, attachments, to) for c in channels}


def _dispatch(cfg, c, text, subject, attachments, to):
    try:
        if c == "slack":
            return _slack(text)
        if c == "mattermost":
            return _mattermost(text)
        if c == "whatsapp":
            return _whatsapp(cfg, text, to)
        if c == "email":
            return notify.send(cfg, to, subject, text, attachments)
        if c == "cli":
            print("\n" + text + "\n")
            return {"ok": True, "transport": "cli"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": f"unknown channel {c}"}


def _post(url, payload, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")


def _slack(text):
    hook = os.environ.get("SLACK_WEBHOOK_URL")
    if hook:
        _post(hook, {"text": text})
        return {"ok": True, "transport": "slack-webhook"}
    tok, chan = os.environ.get("SLACK_BOT_TOKEN"), os.environ.get("SLACK_CHANNEL")
    if tok and chan:
        _post("https://slack.com/api/chat.postMessage", {"channel": chan, "text": text},
              {"Authorization": f"Bearer {tok}"})
        return {"ok": True, "transport": "slack-api"}
    return {"ok": False, "dry_run": True, "error": "set SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN+SLACK_CHANNEL"}


def _mattermost(text):
    hook = os.environ.get("MATTERMOST_WEBHOOK_URL")
    if hook:
        _post(hook, {"text": text})
        return {"ok": True, "transport": "mattermost"}
    return {"ok": False, "dry_run": True, "error": "set MATTERMOST_WEBHOOK_URL"}


def _whatsapp(cfg, text, to):
    tok, pid = os.environ.get("WHATSAPP_TOKEN"), os.environ.get("WHATSAPP_PHONE_ID")
    to = to or (cfg.get("review", {}) or {}).get("whatsapp_to")
    if tok and pid and to:
        _post(f"https://graph.facebook.com/v20.0/{pid}/messages",
              {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
              {"Authorization": f"Bearer {tok}"})
        return {"ok": True, "transport": "whatsapp"}
    return {"ok": False, "dry_run": True,
            "error": "set WHATSAPP_TOKEN + WHATSAPP_PHONE_ID + review.whatsapp_to"}


def render_md(cfg, results):
    L = ["# Channel delivery"]
    for c, r in results.items():
        if r.get("ok"):
            L.append(f"- ✅ {c}: sent ({r.get('transport', c)})")
        elif r.get("dry_run"):
            L.append(f"- ○ {c}: dry-run — {r['error']}")
        else:
            L.append(f"- 🔴 {c}: {r.get('error')}")
    return "\n".join(L)
