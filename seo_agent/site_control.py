"""Full website control — not just publish, but *operate* the live site: update a
page's title/meta, edit body content, create or delete pages, and add redirects,
through the CMS's own API (WordPress / Webflow / Ghost) or the git-PR file flow. Every
mutating call routes through `autonomy.authorize()`, so the operator's chosen mode
(manual / approve / auto) is enforced here.

Design mirrors `publish`: connector-agnostic. The default `file` connector writes each
change to `site-changes/` as a reviewable diff (→ a PR) plus a portable `_redirects`
file — so full control works with zero API creds. Site-agnostic."""
import base64
import json
import os
import urllib.request
from pathlib import Path

from . import autonomy, publish

CHANGES_DIR = "site-changes"


def _http(url, method, headers, payload=None, timeout=60):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "ignore")
        return json.loads(body) if body.strip() else {}


# ── the public API — each is autonomy-gated ─────────────────────────────────
def change(cfg, op, **kw):
    """Propose/apply a single site change. op ∈ create|update_meta|update_content|delete|redirect.
    Returns {executed|queued|planned, ...}. Destructive ops require approval unless auto+allow."""
    kind = {"delete": "delete", "redirect": "redirect"}.get(op, "update")
    target = kw.get("id") or kw.get("url") or kw.get("from_path") or ""
    detail = kw.get("title") or kw.get("to_path") or op
    dec = autonomy.authorize(cfg, f"{op} {target}", kind=kind, target=str(target), detail=str(detail))
    change = {"op": op, **kw}
    if not dec["execute"]:
        if dec.get("queued"):
            return {"status": "queued", "reason": dec["reason"], "change": change}
        _write_change_file(change, applied=False)  # plan/preview even in manual mode
        return {"status": "planned", "reason": dec["reason"], "change": change,
                "preview": f"{CHANGES_DIR}/ (proposed; not applied)"}
    res = _execute(cfg, change)
    if res.get("ok"):  # log to the causal ledger for attribution later
        try:
            from . import ledger
            ledger.record(cfg, str(target), op, str(detail))
        except Exception:
            pass
    return {"status": "executed", **res}


def _execute(cfg, change):
    op = change["op"]
    cms = (cfg.get("cms", {}) or {}).get("type", "file")
    if cms == "wordpress" and op in ("update_meta", "update_content", "delete", "create"):
        return _wp(cfg, change)
    if cms == "file" or op == "redirect":
        return _file(cfg, change)
    # webflow / ghost create delegate to publish; other ops fall back to a change file
    if op == "create":
        return publish.publish(cfg, change.get("post", {}), skip_gate=change.get("skip_gate", False))
    return _file(cfg, change)


def _wp(cfg, change):
    base = cfg["cms"]["base_url"].rstrip("/")
    user, pw = os.environ.get("WP_USER"), os.environ.get("WP_APP_PASSWORD")
    if not (user and pw):
        return {"ok": False, "error": "set WP_USER + WP_APP_PASSWORD"}
    auth = {"Authorization": "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()}
    pid, op = change.get("id"), change["op"]
    ptype = change.get("type", "posts")
    if op == "delete":
        return {"ok": True, **_http(f"{base}/wp-json/wp/v2/{ptype}/{pid}?force=false", "DELETE", auth)}
    if op == "create":
        return publish.publish(cfg, change.get("post", {}))
    fields = {}
    if op == "update_meta":
        if change.get("title"):
            fields["title"] = change["title"]
        if change.get("description"):
            fields["excerpt"] = change["description"]
    if op == "update_content" and change.get("content"):
        fields["content"] = change["content"]
    r = _http(f"{base}/wp-json/wp/v2/{ptype}/{pid}", "POST", auth, fields)
    return {"ok": True, "id": r.get("id"), "url": r.get("link")}


def _file(cfg, change):
    """Portable git-PR flow: write the change as a reviewable file (+ maintain _redirects)."""
    _write_change_file(change, applied=True)
    if change["op"] == "redirect":
        rp = Path(cfg.get("cms", {}).get("dir", "content")).parent / "_redirects"
        line = f"{change['from_path']} {change['to_path']} 301\n"
        with open(rp, "a") as f:
            f.write(line)
        return {"ok": True, "wrote": str(rp), "rule": line.strip()}
    return {"ok": True, "wrote": f"{CHANGES_DIR}/{_fname(change)}"}


def _fname(change):
    t = (str(change.get("id") or change.get("url") or change.get("from_path") or "change")
         .rstrip("/").rsplit("/", 1)[-1] or "change")
    return f"{change['op']}--{t}.json"


def _write_change_file(change, applied):
    d = Path(CHANGES_DIR)
    d.mkdir(parents=True, exist_ok=True)
    rec = {"applied": applied, **change}
    (d / _fname(change)).write_text(json.dumps(rec, indent=2) + "\n")


def apply_approved(cfg):
    """Execute everything in the approvals queue (used by `apply --approved`)."""
    return autonomy.approve_all(cfg, lambda item: _execute(cfg, _item_to_change(item)))


def _item_to_change(item):
    # queued items store action string + kind; reconstruct minimally from detail if present
    return item.get("change") or {"op": item.get("kind", "update"), "url": item.get("target"),
                                   "title": item.get("detail")}


def render_md(cfg, r):
    L = [f"# Site control — {r['status']}"]
    if r["status"] == "executed":
        L.append(f"- ✅ applied: {r.get('change',{}).get('op')} → {r.get('url') or r.get('wrote') or r.get('rule') or 'ok'}")
    elif r["status"] == "queued":
        L.append(f"- ⏳ queued for approval ({r['reason']}). Run `apply --approved`.")
    else:
        L.append(f"- 📝 planned only ({r['reason']}). Preview in `{CHANGES_DIR}/`.")
    return "\n".join(L)
