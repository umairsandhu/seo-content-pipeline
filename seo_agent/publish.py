"""Layer 4 — Publish (goal #4). One publish() interface over pluggable CMS
connectors, so the same pipeline posts anywhere. Connectors:

  file      — write a Markdown file with front-matter (the git-PR flow; the safe
              default — "auto-publish = an automated PR", nothing goes live alone)
  wordpress — WP REST API (env: WP_USER, WP_APP_PASSWORD)
  webflow   — Webflow CMS API v2 (env: WEBFLOW_TOKEN)
  ghost     — Ghost Admin API, JWT-signed (env: GHOST_ADMIN_KEY = "id:secret")

Secrets come from env, never config. A post is
  {title, slug, markdown|html, meta_description, status}. Every connector returns
  {ok, connector, ...}. This module is also what the MCP server exposes so any
  MCP client (or another CMS) can drive publishing."""
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.request
from pathlib import Path


def publish(cfg, post):
    cms = cfg.get("cms", {})
    fn = {"file": _file, "wordpress": _wordpress, "webflow": _webflow,
          "ghost": _ghost}.get(cms.get("type", "file"))
    if not fn:
        return {"ok": False, "error": f"unknown cms type {cms.get('type')!r}"}
    try:
        return fn(cfg, cms, post)
    except Exception as e:  # network / auth / shape — surface, don't crash the run
        return {"ok": False, "connector": cms.get("type"), "error": str(e)}


def _slug(post):
    return post.get("slug") or "-".join((post.get("title", "post")).lower().split())[:80]


def _post_json(url, payload, headers, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# ── file / git-PR (default) ─────────────────────────────────────────────────
def _file(cfg, cms, post):
    d = Path(cms.get("dir", "content"))
    d.mkdir(parents=True, exist_ok=True)
    slug = _slug(post)
    fm = {"title": post.get("title", ""), "slug": slug,
          "description": post.get("meta_description", ""),
          "draft": post.get("status", "draft") != "publish"}
    front = "---\n" + "\n".join(f"{k}: {json.dumps(v)}" for k, v in fm.items()) + "\n---\n\n"
    body = post.get("markdown") or post.get("html") or ""
    p = d / f"{slug}.md"
    p.write_text(front + body)
    return {"ok": True, "connector": "file", "path": str(p),
            "note": "commit + open a PR to publish"}


# ── WordPress REST ──────────────────────────────────────────────────────────
def _wordpress(cfg, cms, post):
    base = cms["base_url"].rstrip("/")
    user, pw = os.environ.get("WP_USER"), os.environ.get("WP_APP_PASSWORD")
    if not (user and pw):
        return {"ok": False, "connector": "wordpress", "error": "set WP_USER + WP_APP_PASSWORD"}
    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    payload = {"title": post.get("title", ""), "slug": _slug(post),
               "content": post.get("html") or post.get("markdown", ""),
               "excerpt": post.get("meta_description", ""),
               "status": "publish" if post.get("status") == "publish" else "draft"}
    res = _post_json(f"{base}/wp-json/wp/v2/posts", payload,
                     {"Authorization": f"Basic {auth}"})
    return {"ok": True, "connector": "wordpress", "id": res.get("id"), "url": res.get("link")}


# ── Webflow CMS v2 ──────────────────────────────────────────────────────────
def _webflow(cfg, cms, post):
    token = os.environ.get("WEBFLOW_TOKEN")
    if not token:
        return {"ok": False, "connector": "webflow", "error": "set WEBFLOW_TOKEN"}
    fields = cms.get("field_map", {})
    payload = {"isArchived": False, "isDraft": post.get("status") != "publish",
               "fieldData": {fields.get("name", "name"): post.get("title", ""),
                             fields.get("slug", "slug"): _slug(post),
                             fields.get("body", "post-body"): post.get("html") or post.get("markdown", ""),
                             fields.get("summary", "post-summary"): post.get("meta_description", "")}}
    res = _post_json(f"https://api.webflow.com/v2/collections/{cms['collection_id']}/items",
                     payload, {"Authorization": f"Bearer {token}",
                               "accept-version": "2.0.0"})
    return {"ok": True, "connector": "webflow", "id": res.get("id")}


# ── Ghost Admin API ─────────────────────────────────────────────────────────
def _ghost_jwt(admin_key):
    kid, secret = admin_key.split(":")
    now = int(time.time())
    seg = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=")
    signing = (seg({"alg": "HS256", "typ": "JWT", "kid": kid}) + b"."
               + seg({"iat": now, "exp": now + 300, "aud": "/admin/"}))
    sig = hmac.new(bytes.fromhex(secret), signing, hashlib.sha256).digest()
    return (signing + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()


def _ghost(cfg, cms, post):
    key = os.environ.get("GHOST_ADMIN_KEY")
    if not key:
        return {"ok": False, "connector": "ghost", "error": "set GHOST_ADMIN_KEY (id:secret)"}
    base = cms["base_url"].rstrip("/")
    payload = {"posts": [{"title": post.get("title", ""), "slug": _slug(post),
                          "custom_excerpt": (post.get("meta_description") or "")[:300],
                          "html": post.get("html") or post.get("markdown", ""),
                          "status": "published" if post.get("status") == "publish" else "draft"}]}
    res = _post_json(f"{base}/ghost/api/admin/posts/?source=html", payload,
                     {"Authorization": f"Ghost {_ghost_jwt(key)}"})
    p = (res.get("posts") or [{}])[0]
    return {"ok": True, "connector": "ghost", "id": p.get("id"), "url": p.get("url")}
