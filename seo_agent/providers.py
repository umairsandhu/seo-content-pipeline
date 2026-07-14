"""External data providers.

DataForSEO — search volume, SERP, and keyword suggestions (discovery/trend pull).
Activates when DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD are set; degrades to empty.

GSC — Google Search Console performance (queries/pages: clicks, impressions, CTR,
position). Needs a service-account JSON (config.gsc_credentials) with the property
shared to that service account. Google libs are imported lazily so the core
pipeline has no google dependency."""
import base64
import json
import os
import sys
import urllib.request


# ── DataForSEO ──────────────────────────────────────────────────────────────
def _dfs_auth():
    lo, pw = os.environ.get("DATAFORSEO_LOGIN"), os.environ.get("DATAFORSEO_PASSWORD")
    return base64.b64encode(f"{lo}:{pw}".encode()).decode() if lo and pw else None


def _dfs_post(path, payload, timeout=60):
    auth = _dfs_auth()
    if not auth:
        return None
    req = urllib.request.Request("https://api.dataforseo.com/v3/" + path,
                                 data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": f"Basic {auth}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception as e:
        print(f"  ! DataForSEO {path}: {e}", file=sys.stderr)
        return None


def search_volume(keywords, loc="United States", lang="English"):
    res = _dfs_post("keywords_data/google_ads/search_volume/live",
                    [{"keywords": list(keywords), "location_name": loc, "language_name": lang}])
    out = {k: {"volume": None, "difficulty": None, "cpc": None} for k in keywords}
    if not res:
        return out
    for it in (res.get("tasks") or [{}])[0].get("result") or []:
        if it.get("keyword") in out:
            out[it["keyword"]] = {"volume": it.get("search_volume"),
                                  "difficulty": it.get("competition_index"), "cpc": it.get("cpc")}
    return out


def serp(keyword, loc="United States", lang="English", depth=10):
    res = _dfs_post("serp/google/organic/live/advanced",
                    [{"keyword": keyword, "location_name": loc, "language_name": lang, "depth": depth}])
    if not res:
        return {"error": "no DataForSEO creds / call failed"}
    result = (res.get("tasks") or [{}])[0].get("result") or []
    items = result[0].get("items", []) if result else []
    organic, paa, related = [], [], []
    for it in items:
        t = it.get("type")
        if t == "organic" and len(organic) < depth:
            organic.append({"title": it.get("title"), "url": it.get("url")})
        elif t == "people_also_ask":
            paa += [q.get("title") for q in it.get("items", []) or [] if isinstance(q, dict) and q.get("title")]
        elif t == "related_searches":
            for kw in it.get("items", []) or []:
                related.append(kw if isinstance(kw, str) else kw.get("keyword"))
    return {"organic": organic, "paa": [q for q in paa if q], "related": [r for r in related if r]}


def suggestions(seed, loc="United States", lang="English", limit=50):
    """Discovery / trend pull — expand a seed into ranked keyword ideas + volumes."""
    res = _dfs_post("dataforseo_labs/google/keyword_suggestions/live",
                    [{"keyword": seed, "location_name": loc, "language_name": lang, "limit": limit}])
    if not res:
        return []
    items = ((res.get("tasks") or [{}])[0].get("result") or [{}])[0].get("items") or []
    out = []
    for it in items:
        kw = it.get("keyword")
        info = (it.get("keyword_info") or {})
        if kw:
            out.append({"keyword": kw, "volume": info.get("search_volume"),
                        "competition": info.get("competition")})
    out.sort(key=lambda r: -(r["volume"] or 0))
    return out


# ── Google Search Console ───────────────────────────────────────────────────
def gsc_service(credentials_path):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("  ! GSC needs: pip install google-api-python-client google-auth", file=sys.stderr)
        return None
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def gsc_query(service, prop, start, end, dimensions=("query",), row_limit=5000):
    if not service:
        return []
    body = {"startDate": start, "endDate": end, "dimensions": list(dimensions),
            "rowLimit": row_limit}
    resp = service.searchanalytics().query(siteUrl=prop, body=body).execute()
    rows = []
    for r in resp.get("rows", []):
        keys = r.get("keys", [])
        rows.append({**{d: keys[i] for i, d in enumerate(dimensions)},
                     "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0),
                     "ctr": r.get("ctr", 0), "position": r.get("position", 0)})
    return rows


def striking_distance(rows, pos_min=5, pos_max=15, min_impr=100):
    """Queries one push from page 1 — high impressions, position 5–15."""
    hit = [r for r in rows if pos_min <= r["position"] <= pos_max and r["impressions"] >= min_impr]
    return sorted(hit, key=lambda r: -r["impressions"])


def low_ctr(rows, min_impr=500, ctr_below=0.02):
    """High-impression, low-CTR rows — retitle/meta candidates."""
    hit = [r for r in rows if r["impressions"] >= min_impr and r["ctr"] < ctr_below]
    return sorted(hit, key=lambda r: -r["impressions"])
