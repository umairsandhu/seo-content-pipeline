"""Extended CMS connectors + the single requirements registry for EVERY CMS the
pipeline can drive. WordPress / Webflow / Ghost live in `publish`/`site_control`;
this module adds Shopify, Contentful, Strapi, Sanity, HubSpot, Drupal, Joomla,
Wix and Notion — and documents the ones with no public content-write API
(Squarespace, Framer, Duda) so onboarding can say so honestly and route them to
the git-PR file flow.

`REQUIREMENTS` is the source of truth: integrations entries, `.env.example`,
the onboarding journey and the wizard are all generated from it — add a CMS here
and every surface updates. Secrets come from env, never config. All connectors
create DRAFTS by default (the human review gate stays between the tool and the
live site). Field slugs are site-specific — smoke-tested offline; verify the
first live call. Stdlib only."""
import json
import os
import urllib.parse
import urllib.request

# ── the registry: every CMS, its env vars, config keys, and what works ───────
REQUIREMENTS = {
    "file":        {"name": "File / git-PR (default)", "env": [], "config": ["cms.dir"],
                    "ops": "create/update/delete/redirect via reviewable files — zero creds",
                    "docs": "docs/Capabilities.md"},
    "wordpress":   {"name": "WordPress", "env": ["WP_USER", "WP_APP_PASSWORD"],
                    "config": ["cms.base_url"], "ops": "create/update/delete",
                    "docs": "https://developer.wordpress.org/rest-api/"},
    "webflow":     {"name": "Webflow", "env": ["WEBFLOW_TOKEN"],
                    "config": ["cms.collection_id", "cms.field_map"], "ops": "create/update/delete",
                    "docs": "https://developers.webflow.com/"},
    "ghost":       {"name": "Ghost", "env": ["GHOST_ADMIN_KEY"],
                    "config": ["cms.base_url"], "ops": "create",
                    "docs": "https://ghost.org/docs/admin-api/"},
    "shopify":     {"name": "Shopify (blog)", "env": ["SHOPIFY_ACCESS_TOKEN"],
                    "config": ["cms.store", "cms.blog_id"], "ops": "create/update/delete",
                    "docs": "https://shopify.dev/docs/api/admin-rest/latest/resources/article"},
    "contentful":  {"name": "Contentful", "env": ["CONTENTFUL_MANAGEMENT_TOKEN"],
                    "config": ["cms.space_id", "cms.content_type"], "ops": "create/update/delete",
                    "docs": "https://www.contentful.com/developers/docs/references/content-management-api/"},
    "strapi":      {"name": "Strapi", "env": ["STRAPI_TOKEN"],
                    "config": ["cms.base_url", "cms.collection"], "ops": "create/update/delete",
                    "docs": "https://docs.strapi.io/dev-docs/api/rest"},
    "sanity":      {"name": "Sanity", "env": ["SANITY_TOKEN"],
                    "config": ["cms.project_id", "cms.dataset"], "ops": "create/update/delete",
                    "docs": "https://www.sanity.io/docs/http-mutations"},
    "hubspot":     {"name": "HubSpot CMS (blog)", "env": ["HUBSPOT_TOKEN"],
                    "config": ["cms.blog_id"], "ops": "create/update/delete",
                    "docs": "https://developers.hubspot.com/docs/api/cms/blog-post"},
    "drupal":      {"name": "Drupal (JSON:API)", "env": ["DRUPAL_USER", "DRUPAL_PASSWORD"],
                    "config": ["cms.base_url"], "ops": "create/update/delete",
                    "docs": "https://www.drupal.org/docs/core-modules-and-themes/core-modules/jsonapi-module"},
    "joomla":      {"name": "Joomla", "env": ["JOOMLA_TOKEN"],
                    "config": ["cms.base_url", "cms.category_id"], "ops": "create/update/delete",
                    "docs": "https://docs.joomla.org/J4.x:Joomla_Core_APIs"},
    "wix":         {"name": "Wix (blog)", "env": ["WIX_API_KEY", "WIX_SITE_ID"],
                    "config": [], "ops": "create/update/delete (drafts, by item id)",
                    "docs": "https://dev.wix.com/docs/rest/business-solutions/blog/draft-posts"},
    "notion":      {"name": "Notion (as CMS)", "env": ["NOTION_TOKEN"],
                    "config": ["cms.database_id"], "ops": "create/update/archive",
                    "docs": "https://developers.notion.com/reference/post-page"},
    # honest no-write-API entries — onboarding routes these to the file/git-PR flow
    "squarespace": {"name": "Squarespace", "env": [], "config": [], "ops": "no public content-write API",
                    "manual": "export/import or paste — use the file/git-PR flow + site-changes/ diffs",
                    "docs": "https://developers.squarespace.com/"},
    "framer":      {"name": "Framer", "env": [], "config": [], "ops": "no public content-write API",
                    "manual": "paste from the produced drafts — use the file/git-PR flow",
                    "docs": "https://www.framer.com/help/"},
    "duda":        {"name": "Duda", "env": [], "config": [], "ops": "no stable public blog-write API",
                    "manual": "use the file/git-PR flow; Duda API covers site/library, not blog posts",
                    "docs": "https://developer.duda.co/"},
}


def requirements(cms_type):
    return REQUIREMENTS.get((cms_type or "file").lower())


def supported():
    """CMS types with a working write connector."""
    return [k for k, v in REQUIREMENTS.items() if "manual" not in v]


def extended():
    """CMS types this module implements (the classic four live in publish/site_control)."""
    return [k for k in supported() if k not in ("file", "wordpress", "webflow", "ghost")]


def missing_env(cms_type):
    r = requirements(cms_type) or {}
    return [e for e in r.get("env", []) if not os.environ.get(e)]


def integration_entries():
    """Generate integrations-registry entries for the CMSs added here (the classic
    three already have hand-written entries)."""
    out = []
    for key, r in REQUIREMENTS.items():
        if key in ("file", "wordpress", "webflow", "ghost"):
            continue
        purpose = ("Publish + update/delete live content" if "manual" not in r
                   else f"No write API — {r['manual']}")
        out.append({"key": f"cms_{key}", "name": r["name"], "tier": "optional",
                    "kind": "api-key" if r["env"] else "manual",
                    "purpose": purpose, "env": r["env"],
                    "config": r.get("config", []), "when": ("cms.type", key),
                    "unlocks": ["publish", "control (update/delete)"] if "manual" not in r
                               else ["file/git-PR flow only"],
                    "options": ["file/git-PR flow (default, zero creds)"],
                    "docs": r["docs"]})
    return out


# ── shared plumbing ──────────────────────────────────────────────────────────
def _http(url, method, headers, payload=None, timeout=60, ctype="application/json"):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": ctype, **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "ignore")
        return json.loads(body) if body.strip() else {}


def _fm(cms, key, default):
    return (cms.get("field_map", {}) or {}).get(key, default)


def _slugify(change):
    p = change.get("post", {})
    return (p.get("slug") or change.get("slug")
            or "-".join((p.get("title") or change.get("title") or "post").lower().split())[:80])


def _text(change):
    p = change.get("post", {})
    return change.get("content") or p.get("html") or p.get("markdown") or ""


def _paras(text, limit=2000):
    """Plain paragraphs from markdown/html-ish text (for block-based CMSs)."""
    import re
    t = re.sub(r"<[^>]+>", " ", text)
    return [p.strip()[:limit] for p in t.split("\n\n") if p.strip()][:90]


def create(cfg, post):
    """publish() entry point for the extended connectors."""
    return execute(cfg, {"op": "create", "post": post})


def execute(cfg, change):
    """site_control entry point: op ∈ create|update_meta|update_content|delete."""
    cms = cfg.get("cms", {}) or {}
    t = (cms.get("type") or "file").lower()
    r = requirements(t)
    if not r:
        return {"ok": False, "error": f"unknown cms type {t!r}"}
    if "manual" in r:
        return {"ok": False, "connector": t,
                "error": f"{r['name']}: {r['ops']} — {r['manual']}"}
    miss = missing_env(t)
    if miss:
        return {"ok": False, "connector": t, "error": "set " + " + ".join(miss)
                + (" and config " + ", ".join(r["config"]) if r.get("config") else "")}
    fn = {"shopify": _shopify, "contentful": _contentful, "strapi": _strapi,
          "sanity": _sanity, "hubspot": _hubspot, "drupal": _drupal,
          "joomla": _joomla, "wix": _wix, "notion": _notion}.get(t)
    if not fn:
        return {"ok": False, "error": f"no extended connector for {t!r}"}
    try:
        return fn(cfg, cms, change)
    except Exception as e:  # network / auth / field-shape — surface, don't crash
        return {"ok": False, "connector": t, "error": str(e)}


# ── Shopify (blog articles, Admin REST) ──────────────────────────────────────
def _shopify(cfg, cms, change):
    store = cms["store"].replace("https://", "").rstrip("/")
    hdr = {"X-Shopify-Access-Token": os.environ["SHOPIFY_ACCESS_TOKEN"]}
    base = f"https://{store}/admin/api/2025-01/blogs/{cms['blog_id']}/articles"
    op = change["op"]
    if op == "create":
        p = change.get("post", {})
        art = {"title": p.get("title", ""), "handle": _slugify(change),
               "body_html": p.get("html") or p.get("markdown", ""),
               "summary_html": p.get("meta_description", ""),
               "published": p.get("status") == "publish"}
        r = _http(f"{base}.json", "POST", hdr, {"article": art})
        a = r.get("article", {})
        return {"ok": True, "connector": "shopify", "id": a.get("id")}
    aid = change.get("id") or _shopify_resolve(base, hdr, change.get("url", ""))
    if not aid:
        return {"ok": False, "connector": "shopify", "error": "could not resolve article (pass id or a url whose handle matches)"}
    if op == "delete":
        _http(f"{base}/{aid}.json", "DELETE", hdr)
        return {"ok": True, "connector": "shopify", "deleted": aid}
    art = {"id": aid}
    if change.get("title"):
        art["title"] = change["title"]
    if change.get("description"):
        art["summary_html"] = change["description"]
    if change.get("content"):
        art["body_html"] = change["content"]
    r = _http(f"{base}/{aid}.json", "PUT", hdr, {"article": art})
    return {"ok": True, "connector": "shopify", "id": aid}


def _shopify_resolve(base, hdr, url):
    handle = (url or "").rstrip("/").rsplit("/", 1)[-1]
    if not handle:
        return None
    r = _http(f"{base}.json?handle={urllib.parse.quote(handle)}", "GET", hdr)
    arts = r.get("articles", [])
    return arts[0]["id"] if arts else None


# ── Contentful (Content Management API) ──────────────────────────────────────
def _contentful(cfg, cms, change):
    tok = os.environ["CONTENTFUL_MANAGEMENT_TOKEN"]
    env = cms.get("environment", "master")
    loc = cms.get("locale", "en-US")
    base = f"https://api.contentful.com/spaces/{cms['space_id']}/environments/{env}/entries"
    hdr = {"Authorization": f"Bearer {tok}"}
    op = change["op"]
    L = lambda v: {loc: v}
    if op == "create":
        p = change.get("post", {})
        fields = {_fm(cms, "name", "title"): L(p.get("title", "")),
                  _fm(cms, "slug", "slug"): L(_slugify(change)),
                  _fm(cms, "body", "body"): L(p.get("markdown") or p.get("html", "")),
                  _fm(cms, "summary", "description"): L(p.get("meta_description", ""))}
        r = _http(base, "POST", {**hdr, "X-Contentful-Content-Type": cms["content_type"]},
                  {"fields": fields}, ctype="application/vnd.contentful.management.v1+json")
        return {"ok": True, "connector": "contentful", "id": (r.get("sys") or {}).get("id")}
    eid = change.get("id")
    if not eid:
        return {"ok": False, "connector": "contentful", "error": "pass the entry id (Contentful has no slug lookup here)"}
    cur = _http(f"{base}/{eid}", "GET", hdr)
    ver = str((cur.get("sys") or {}).get("version", 1))
    if op == "delete":
        _http(f"{base}/{eid}", "DELETE", {**hdr, "X-Contentful-Version": ver})
        return {"ok": True, "connector": "contentful", "deleted": eid}
    fields = cur.get("fields", {})
    if change.get("title"):
        fields[_fm(cms, "name", "title")] = L(change["title"])
    if change.get("description"):
        fields[_fm(cms, "summary", "description")] = L(change["description"])
    if change.get("content"):
        fields[_fm(cms, "body", "body")] = L(change["content"])
    r = _http(f"{base}/{eid}", "PUT", {**hdr, "X-Contentful-Version": ver}, {"fields": fields},
              ctype="application/vnd.contentful.management.v1+json")
    return {"ok": True, "connector": "contentful", "id": eid}


# ── Strapi (REST, v4/v5) ─────────────────────────────────────────────────────
def _strapi(cfg, cms, change):
    base = cms["base_url"].rstrip("/") + f"/api/{cms['collection']}"
    hdr = {"Authorization": f"Bearer {os.environ['STRAPI_TOKEN']}"}
    op = change["op"]
    if op == "create":
        p = change.get("post", {})
        data = {_fm(cms, "name", "title"): p.get("title", ""),
                _fm(cms, "slug", "slug"): _slugify(change),
                _fm(cms, "body", "content"): p.get("markdown") or p.get("html", ""),
                _fm(cms, "summary", "description"): p.get("meta_description", "")}
        r = _http(base, "POST", hdr, {"data": data})
        d = r.get("data") or {}
        return {"ok": True, "connector": "strapi", "id": d.get("documentId") or d.get("id")}
    sid = change.get("id") or _strapi_resolve(cms, base, hdr, change.get("url", ""))
    if not sid:
        return {"ok": False, "connector": "strapi", "error": "could not resolve entry (pass id, or a url whose slug matches)"}
    if op == "delete":
        _http(f"{base}/{sid}", "DELETE", hdr)
        return {"ok": True, "connector": "strapi", "deleted": sid}
    data = {}
    if change.get("title"):
        data[_fm(cms, "name", "title")] = change["title"]
    if change.get("description"):
        data[_fm(cms, "summary", "description")] = change["description"]
    if change.get("content"):
        data[_fm(cms, "body", "content")] = change["content"]
    _http(f"{base}/{sid}", "PUT", hdr, {"data": data})
    return {"ok": True, "connector": "strapi", "id": sid}


def _strapi_resolve(cms, base, hdr, url):
    slug = (url or "").rstrip("/").rsplit("/", 1)[-1]
    if not slug:
        return None
    sf = _fm(cms, "slug", "slug")
    r = _http(f"{base}?filters[{sf}][$eq]={urllib.parse.quote(slug)}", "GET", hdr)
    rows = r.get("data") or []
    return (rows[0].get("documentId") or rows[0].get("id")) if rows else None


# ── Sanity (HTTP mutations + GROQ resolve) ───────────────────────────────────
def _sanity(cfg, cms, change):
    proj, ds = cms["project_id"], cms.get("dataset", "production")
    api = f"https://{proj}.api.sanity.io/v2024-01-01"
    hdr = {"Authorization": f"Bearer {os.environ['SANITY_TOKEN']}"}
    typ = cms.get("doc_type", "post")
    op = change["op"]
    blocks = lambda text: [{"_type": "block", "style": "normal", "markDefs": [],
                            "children": [{"_type": "span", "text": p, "marks": []}]}
                           for p in _paras(text)]
    if op == "create":
        p = change.get("post", {})
        doc = {"_type": typ, _fm(cms, "name", "title"): p.get("title", ""),
               _fm(cms, "slug", "slug"): {"_type": "slug", "current": _slugify(change)},
               _fm(cms, "summary", "description"): p.get("meta_description", ""),
               _fm(cms, "body", "body"): blocks(p.get("markdown") or p.get("html", ""))}
        r = _http(f"{api}/data/mutate/{ds}", "POST", hdr, {"mutations": [{"create": doc}]})
        ids = (r.get("results") or [{}])
        return {"ok": True, "connector": "sanity", "id": ids[0].get("id")}
    did = change.get("id") or _sanity_resolve(api, ds, hdr, typ, cms, change.get("url", ""))
    if not did:
        return {"ok": False, "connector": "sanity", "error": "could not resolve document (pass id, or a url whose slug matches)"}
    if op == "delete":
        _http(f"{api}/data/mutate/{ds}", "POST", hdr, {"mutations": [{"delete": {"id": did}}]})
        return {"ok": True, "connector": "sanity", "deleted": did}
    st = {}
    if change.get("title"):
        st[_fm(cms, "name", "title")] = change["title"]
    if change.get("description"):
        st[_fm(cms, "summary", "description")] = change["description"]
    if change.get("content"):
        st[_fm(cms, "body", "body")] = blocks(change["content"])
    _http(f"{api}/data/mutate/{ds}", "POST", hdr, {"mutations": [{"patch": {"id": did, "set": st}}]})
    return {"ok": True, "connector": "sanity", "id": did}


def _sanity_resolve(api, ds, hdr, typ, cms, url):
    slug = (url or "").rstrip("/").rsplit("/", 1)[-1]
    if not slug:
        return None
    sf = _fm(cms, "slug", "slug")
    q = urllib.parse.quote(f'*[_type=="{typ}" && {sf}.current=="{slug}"][0]._id')
    r = _http(f"{api}/data/query/{ds}?query={q}", "GET", hdr)
    return r.get("result")


# ── HubSpot CMS blog ─────────────────────────────────────────────────────────
def _hubspot(cfg, cms, change):
    hdr = {"Authorization": f"Bearer {os.environ['HUBSPOT_TOKEN']}"}
    base = "https://api.hubapi.com/cms/v3/blogs/posts"
    op = change["op"]
    if op == "create":
        p = change.get("post", {})
        body = {"name": p.get("title", ""), "slug": _slugify(change),
                "postBody": p.get("html") or p.get("markdown", ""),
                "metaDescription": p.get("meta_description", ""),
                "contentGroupId": str(cms["blog_id"]), "state": "DRAFT"}
        r = _http(base, "POST", hdr, body)
        return {"ok": True, "connector": "hubspot", "id": r.get("id")}
    pid = change.get("id") or _hubspot_resolve(base, hdr, change.get("url", ""))
    if not pid:
        return {"ok": False, "connector": "hubspot", "error": "could not resolve post (pass id, or a url whose slug matches)"}
    if op == "delete":
        _http(f"{base}/{pid}", "DELETE", hdr)
        return {"ok": True, "connector": "hubspot", "deleted": pid}
    body = {}
    if change.get("title"):
        body["name"] = change["title"]
    if change.get("description"):
        body["metaDescription"] = change["description"]
    if change.get("content"):
        body["postBody"] = change["content"]
    _http(f"{base}/{pid}", "PATCH", hdr, body)
    return {"ok": True, "connector": "hubspot", "id": pid}


def _hubspot_resolve(base, hdr, url):
    slug = (url or "").rstrip("/").rsplit("/", 1)[-1]
    if not slug:
        return None
    r = _http(f"{base}?slug={urllib.parse.quote(slug)}&limit=1", "GET", hdr)
    rows = r.get("results") or []
    return rows[0].get("id") if rows else None


# ── Drupal (JSON:API, basic auth) ────────────────────────────────────────────
def _drupal(cfg, cms, change):
    import base64
    base = cms["base_url"].rstrip("/")
    typ = cms.get("node_type", "article")
    auth = base64.b64encode(f"{os.environ['DRUPAL_USER']}:{os.environ['DRUPAL_PASSWORD']}".encode()).decode()
    hdr = {"Authorization": f"Basic {auth}", "Accept": "application/vnd.api+json"}
    api = f"{base}/jsonapi/node/{typ}"
    ct = "application/vnd.api+json"
    op = change["op"]
    if op == "create":
        p = change.get("post", {})
        data = {"type": f"node--{typ}",
                "attributes": {"title": p.get("title", ""), "status": p.get("status") == "publish",
                               "body": {"value": p.get("html") or p.get("markdown", ""),
                                        "summary": p.get("meta_description", ""), "format": "basic_html"}}}
        r = _http(api, "POST", hdr, {"data": data}, ctype=ct)
        return {"ok": True, "connector": "drupal", "id": (r.get("data") or {}).get("id")}
    nid = change.get("id") or _drupal_resolve(api, hdr, change.get("url", ""), change.get("title", ""))
    if not nid:
        return {"ok": False, "connector": "drupal", "error": "could not resolve node (pass the uuid `id`)"}
    if op == "delete":
        _http(f"{api}/{nid}", "DELETE", hdr)
        return {"ok": True, "connector": "drupal", "deleted": nid}
    attrs = {}
    if change.get("title"):
        attrs["title"] = change["title"]
    body = {}
    if change.get("content"):
        body["value"] = change["content"]
        body["format"] = "basic_html"
    if change.get("description"):
        body["summary"] = change["description"]
    if body:
        attrs["body"] = body
    _http(f"{api}/{nid}", "PATCH", hdr,
          {"data": {"type": f"node--{typ}", "id": nid, "attributes": attrs}}, ctype=ct)
    return {"ok": True, "connector": "drupal", "id": nid}


def _drupal_resolve(api, hdr, url, title):
    slug = (url or "").rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
    needle = title or slug
    if not needle:
        return None
    r = _http(f"{api}?filter[title]={urllib.parse.quote(needle)}&page[limit]=1", "GET", hdr)
    rows = r.get("data") or []
    return rows[0].get("id") if rows else None


# ── Joomla (Web Services API, token) ─────────────────────────────────────────
def _joomla(cfg, cms, change):
    base = cms["base_url"].rstrip("/")
    hdr = {"X-Joomla-Token": os.environ["JOOMLA_TOKEN"]}
    api = f"{base}/api/index.php/v1/content/articles"
    op = change["op"]
    if op == "create":
        p = change.get("post", {})
        body = {"title": p.get("title", ""), "alias": _slugify(change),
                "articletext": p.get("html") or p.get("markdown", ""),
                "metadesc": p.get("meta_description", ""),
                "catid": int(cms["category_id"]), "language": "*",
                "state": 1 if p.get("status") == "publish" else 0}
        r = _http(api, "POST", hdr, body)
        return {"ok": True, "connector": "joomla", "id": ((r.get("data") or {}).get("id"))}
    aid = change.get("id")
    if not aid:
        return {"ok": False, "connector": "joomla", "error": "pass the article id"}
    if op == "delete":
        _http(f"{api}/{aid}", "DELETE", hdr)  # needs state=trashed first on some setups
        return {"ok": True, "connector": "joomla", "deleted": aid}
    body = {}
    if change.get("title"):
        body["title"] = change["title"]
    if change.get("description"):
        body["metadesc"] = change["description"]
    if change.get("content"):
        body["articletext"] = change["content"]
    _http(f"{api}/{aid}", "PATCH", hdr, body)
    return {"ok": True, "connector": "joomla", "id": aid}


# ── Wix (blog draft posts) ───────────────────────────────────────────────────
def _wix(cfg, cms, change):
    hdr = {"Authorization": os.environ["WIX_API_KEY"], "wix-site-id": os.environ["WIX_SITE_ID"]}
    base = "https://www.wixapis.com/blog/v3/draft-posts"
    op = change["op"]
    rich = lambda text: {"nodes": [{"type": "PARAGRAPH", "id": f"p{i}",
                                    "nodes": [{"type": "TEXT", "id": "", "textData": {"text": p, "decorations": []}}]}
                                   for i, p in enumerate(_paras(text))]}
    if op == "create":
        p = change.get("post", {})
        draft = {"title": p.get("title", ""), "excerpt": (p.get("meta_description") or "")[:500],
                 "richContent": rich(p.get("markdown") or p.get("html", ""))}
        r = _http(base, "POST", hdr, {"draftPost": draft})
        return {"ok": True, "connector": "wix", "id": (r.get("draftPost") or {}).get("id")}
    did = change.get("id")
    if not did:
        return {"ok": False, "connector": "wix", "error": "pass the draft-post id (Wix update/delete is id-based)"}
    if op == "delete":
        _http(f"{base}/{did}", "DELETE", hdr)
        return {"ok": True, "connector": "wix", "deleted": did}
    draft = {}
    if change.get("title"):
        draft["title"] = change["title"]
    if change.get("description"):
        draft["excerpt"] = change["description"][:500]
    if change.get("content"):
        draft["richContent"] = rich(change["content"])
    _http(f"{base}/{did}", "PATCH", hdr, {"draftPost": draft})
    return {"ok": True, "connector": "wix", "id": did}


# ── Notion (database as CMS) ─────────────────────────────────────────────────
def _notion(cfg, cms, change):
    hdr = {"Authorization": f"Bearer {os.environ['NOTION_TOKEN']}", "Notion-Version": "2022-06-28"}
    op = change["op"]
    title_prop = _fm(cms, "name", "Name")
    if op == "create":
        p = change.get("post", {})
        children = [{"object": "block", "type": "paragraph",
                     "paragraph": {"rich_text": [{"type": "text", "text": {"content": para}}]}}
                    for para in _paras(p.get("markdown") or p.get("html", ""))]
        body = {"parent": {"database_id": cms["database_id"]},
                "properties": {title_prop: {"title": [{"type": "text", "text": {"content": p.get("title", "")}}]}},
                "children": children[:100]}
        r = _http("https://api.notion.com/v1/pages", "POST", hdr, body)
        return {"ok": True, "connector": "notion", "id": r.get("id"), "url": r.get("url")}
    pid = change.get("id")
    if not pid:
        return {"ok": False, "connector": "notion", "error": "pass the page id"}
    if op == "delete":
        _http(f"https://api.notion.com/v1/pages/{pid}", "PATCH", hdr, {"archived": True})
        return {"ok": True, "connector": "notion", "archived": pid}
    props = {}
    if change.get("title"):
        props[title_prop] = {"title": [{"type": "text", "text": {"content": change["title"]}}]}
    if props:
        _http(f"https://api.notion.com/v1/pages/{pid}", "PATCH", hdr, {"properties": props})
    if change.get("content"):  # append new blocks (Notion has no simple body replace)
        blocks = [{"object": "block", "type": "paragraph",
                   "paragraph": {"rich_text": [{"type": "text", "text": {"content": para}}]}}
                  for para in _paras(change["content"])][:100]
        _http(f"https://api.notion.com/v1/blocks/{pid}/children", "PATCH", hdr, {"children": blocks})
    return {"ok": True, "connector": "notion", "id": pid}


def verify(cfg):
    """W4 / gate G4 — prove the configured CMS connector end-to-end against the LIVE API:
    create a throwaway draft → update it → delete it, reporting pass/fail per step. Runs the
    exact production dispatch (publish + site_control), so a green run means the real API
    accepts our payloads. Needs the CMS creds; degrades to a clear 'not configured' per step."""
    import datetime
    t = ((cfg.get("cms", {}) or {}).get("type") or "file").lower()
    r = requirements(t) or {}
    if t == "file":
        return {"cms": "file", "skipped": True,
                "note": "file/git-PR flow writes reviewable diffs — nothing live to verify"}
    if "manual" in r:
        return {"cms": t, "skipped": True, "note": f"{r['name']}: no write API — {r.get('manual', '')}"}
    miss = missing_env(t) + [c for c in r.get("config", [])
                             if not (cfg.get("cms", {}) or {}).get(c.split(".", 1)[-1])]
    if miss:
        return {"cms": t, "skipped": True, "note": "not configured — set " + ", ".join(miss)}

    from . import publish, site_control
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    post = {"title": f"connector-verify {stamp}", "slug": f"connector-verify-{stamp}",
            "markdown": "Automated connector self-test — safe to delete. " * 20,
            "meta_description": "connector self-test", "status": "draft"}
    steps = []

    c = publish.publish(cfg, post, skip_gate=True)
    steps.append({"step": "create", "ok": bool(c.get("ok")), "id": c.get("id"), "error": c.get("error")})
    cid = c.get("id")
    if not cid:
        return {"cms": t, "ok": False, "steps": steps, "note": "create failed — later steps skipped"}

    url = post_url = c.get("url") or ""
    u = site_control.change(cfg, "update_meta", id=cid, url=post_url,
                            title=f"connector-verify {stamp} (updated)")
    steps.append({"step": "update", "ok": u.get("status") == "executed" and u.get("ok", True) is not False,
                  "error": u.get("error")})

    d = site_control.change(cfg, "delete", id=cid, url=post_url)
    steps.append({"step": "delete", "ok": d.get("status") == "executed" and d.get("ok", True) is not False,
                  "error": d.get("error"), "note": "left the draft in place if delete is unsupported"})

    return {"cms": t, "ok": all(s["ok"] for s in steps), "steps": steps, "test_id": cid}


def verify_md(cfg, r=None):
    r = r or verify(cfg)
    L = [f"# Connector verify — {r['cms']}"]
    if r.get("skipped"):
        return "\n".join(L + [f"\n_⊘ skipped — {r.get('note', '')}_"])
    icon = {True: "✅", False: "❌"}
    L.append("")
    for s in r["steps"]:
        L.append(f"- {icon[s['ok']]} **{s['step']}**" + (f" — {s['error']}" if s.get("error") else "")
                 + (f"  _(id {s.get('id')})_" if s.get("id") else ""))
    L.append(f"\n**{'✅ connector works end-to-end' if r['ok'] else '❌ connector has a problem — see above'}**"
             + (f" · test draft id {r['test_id']} (deleted if delete passed)" if r.get("test_id") else ""))
    return "\n".join(L)


def render_md(cfg):
    cur = ((cfg.get("cms", {}) or {}).get("type") or "file").lower()
    L = ["# CMS connectors — what the pipeline can drive", "",
         "| cms | write ops | env vars | config keys |", "|---|---|---|---|"]
    for k, r in REQUIREMENTS.items():
        mark = " ← **current**" if k == cur else ""
        L.append(f"| {r['name']}{mark} | {r['ops']} | {', '.join(r['env']) or '—'} | "
                 f"{', '.join(r.get('config', [])) or '—'} |")
    miss = missing_env(cur)
    if miss:
        L += ["", f"> ⚠ current cms `{cur}` is missing env: {', '.join(miss)} — add to `.env` (git-ignored)."]
    L += ["", "_Set `cms.type` in config.json. Every connector creates DRAFTS and routes through "
          "the autonomy/review gate. No write API? The file/git-PR flow always works._",
          "_Prove your connector works end-to-end: `cms --verify` (create → update → delete a "
          "throwaway draft against the live API)._"]
    return "\n".join(L)
