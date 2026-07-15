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


def http_json(url, method="GET", headers=None, body=None, timeout=60):
    """Generic authenticated JSON HTTP call — the primitive for integrating ANY
    new API (see integrations.py). Returns parsed JSON or None on failure."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception as e:
        print(f"  ! http {url}: {e}", file=sys.stderr)
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
    organic, paa, related, ai_overview = [], [], [], False
    for it in items:
        t = it.get("type") or ""
        if t == "organic" and len(organic) < depth:
            organic.append({"title": it.get("title"), "url": it.get("url")})
        elif t == "people_also_ask":
            paa += [q.get("title") for q in it.get("items", []) or [] if isinstance(q, dict) and q.get("title")]
        elif t == "related_searches":
            for kw in it.get("items", []) or []:
                related.append(kw if isinstance(kw, str) else kw.get("keyword"))
        elif "ai_overview" in t:      # AI Overview present in this SERP
            ai_overview = True
    return {"organic": organic, "paa": [q for q in paa if q],
            "related": [r for r in related if r], "ai_overview": ai_overview}


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


# ── DataForSEO Backlinks (goal #6) ──────────────────────────────────────────
def backlinks_summary(target):
    res = _dfs_post("backlinks/summary/live", [{"target": target, "internal_list_limit": 10}])
    if not res:
        return {}
    r = ((res.get("tasks") or [{}])[0].get("result") or [{}])[0] or {}
    return {"referring_domains": r.get("referring_domains"),
            "backlinks": r.get("backlinks"), "rank": r.get("rank"),
            "broken_backlinks": r.get("broken_backlinks"),
            "referring_main_domains": r.get("referring_main_domains")}


def referring_domains(target, limit=100):
    res = _dfs_post("backlinks/referring_domains/live",
                    [{"target": target, "limit": limit, "order_by": ["backlinks,desc"]}])
    if not res:
        return []
    items = ((res.get("tasks") or [{}])[0].get("result") or [{}])[0].get("items") or []
    return [{"domain": it.get("domain"), "backlinks": it.get("backlinks"),
             "rank": it.get("rank")} for it in items if it.get("domain")]


# ── DataForSEO Labs ranked keywords (competitor gap) ────────────────────────
def ranked_keywords(target, loc="United States", lang="English", limit=200, max_rank=20):
    """Keywords a domain ranks for (top `max_rank`) — the input to competitor gap."""
    res = _dfs_post("dataforseo_labs/google/ranked_keywords/live",
                    [{"target": target, "location_name": loc, "language_name": lang, "limit": limit,
                      "filters": [["ranked_serp_element.serp_item.rank_group", "<=", max_rank]]}])
    if not res:
        return []
    items = ((res.get("tasks") or [{}])[0].get("result") or [{}])[0].get("items") or []
    out = []
    for it in items:
        kd = it.get("keyword_data", {}) or {}
        kw = kd.get("keyword")
        rank = ((it.get("ranked_serp_element", {}) or {}).get("serp_item", {}) or {}).get("rank_group")
        if kw:
            out.append({"keyword": kw, "volume": (kd.get("keyword_info", {}) or {}).get("search_volume"),
                        "rank": rank})
    return out


# ── DataForSEO Google Trends (goal #8) ──────────────────────────────────────
def google_trends(keywords, loc="United States", lang="English"):
    """Return {keyword: {trend: rising|flat|falling, values:[...]}} from the
    interest-over-time graph (last point vs series mean)."""
    keywords = list(keywords)[:5]  # Google Trends compares up to 5 at a time
    out = {k: {"trend": None, "values": []} for k in keywords}
    if not keywords:
        return out
    res = _dfs_post("keywords_data/google_trends/explore/live",
                    [{"keywords": keywords, "location_name": loc, "language_name": lang,
                      "time_range": "past_12_months"}])
    if not res:
        return out
    for item in ((res.get("tasks") or [{}])[0].get("result") or [{}])[0].get("items") or []:
        if item.get("type") != "google_trends_graph":
            continue
        cols = item.get("keywords") or keywords
        series = {k: [] for k in cols}
        for row in item.get("data") or []:
            for i, v in enumerate(row.get("values") or []):
                if i < len(cols) and v is not None:
                    series[cols[i]].append(v)
        for k, vals in series.items():
            if k in out and vals:
                mean = sum(vals) / len(vals)
                last = sum(vals[-3:]) / len(vals[-3:])
                out[k] = {"values": vals,
                          "trend": "rising" if last > mean * 1.15
                          else "falling" if last < mean * 0.85 else "flat"}
    return out


# ── Optional headless text generation (Layer 3) ─────────────────────────────
# Default provider is "agent": complete() returns None so the AGENT driving the
# skill (Claude, or any LLM harness) writes the content itself — no API key
# needed when run inside Claude/OpenAI. Set llm.provider to "anthropic" or
# "openai" ONLY for headless/cron runs with no agent in the loop.
def complete(prompt, system=None, cfg_llm=None, max_tokens=8000, timeout=600):
    cfg_llm = cfg_llm or {}
    provider = (cfg_llm.get("provider") or "agent").lower()
    if provider == "anthropic":
        return _anthropic(prompt, system, cfg_llm.get("model", "claude-opus-4-8"), max_tokens, timeout)
    if provider == "openai":
        return _openai(prompt, system, cfg_llm.get("model", "gpt-4o"), max_tokens, timeout)
    return None  # "agent" — the caller writes it


def _anthropic(prompt, system, model, max_tokens, timeout):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = {"model": model, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    req = urllib.request.Request("https://api.anthropic.com/v1/messages",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.load(r)
    except Exception as e:
        print(f"  ! Anthropic: {e}", file=sys.stderr)
        return None
    return "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")


def _openai(prompt, system, model, max_tokens, timeout):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": prompt}]
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
                                 data=json.dumps({"model": model, "messages": msgs,
                                                  "max_tokens": max_tokens}).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {key}",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.load(r)
    except Exception as e:
        print(f"  ! OpenAI: {e}", file=sys.stderr)
        return None
    return (resp.get("choices") or [{}])[0].get("message", {}).get("content")
