"""Bing Webmaster Tools — the second search engine, as dated history next to GSC.

`bing` pulls seven Bing Webmaster API methods for the site and writes one dated JSON per kind to
history/ (same envelope as the gsc snapshots: {date, kind, data}):

  GetRankAndTrafficStats -> history/bing_traffic   daily Impressions / Clicks
  GetQueryStats          -> history/bing_queries   Query, Impressions, Clicks, positions, Date
  GetPageStats           -> history/bing_pages     same shape, `Query` holds the page URL
  GetCrawlStats          -> history/bing_crawl     daily CrawledPages, InIndex, Code2xx/301/4xx/5xx, CrawlErrors
  GetFeeds               -> history/bing_feeds     the registered sitemaps: Status, UrlCount, LastCrawled
  GetCrawlIssues, GetUrlSubmissionQuota -> inside the summary only (no snapshot)

Why it exists (LEARNINGS #37): on superx.pk Bing grew while Google fell, and Bing held an emptied
sitemap at its old URL count. Nothing in the tool looked at Bing.

The key (BING_WEBMASTER_API_KEY) goes in the query string, so it is NEVER printed, logged or put in
an exception: every error text passes through `_scrub`. Absent key -> a one-line skip, exit 0.
Site-agnostic: the property is cfg["bing_site"], else cfg["site"], with a trailing slash."""
import datetime
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from . import history, ingest

API = "https://ssl.bing.com/webmaster/api.svc/json/"
ENV = "BING_WEBMASTER_API_KEY"
NO_KEY = f"bing: {ENV} is not set (add it to .env), skipping."
# method -> history kind (None = summary only)
METHODS = {"GetRankAndTrafficStats": "bing_traffic", "GetQueryStats": "bing_queries",
           "GetPageStats": "bing_pages", "GetCrawlStats": "bing_crawl", "GetFeeds": "bing_feeds",
           "GetCrawlIssues": None, "GetUrlSubmissionQuota": None}
_DATE = re.compile(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/")
_DATE_FIELDS = ("Date", "LastCrawled", "Submitted")


def key():
    return os.environ.get(ENV) or None


def _scrub(text, k):
    text = str(text)
    return text.replace(k, "***") if k else text


def site_url(cfg):
    s = (cfg.get("bing_site") or cfg.get("site") or "").strip()
    return s if s.endswith("/") else s + "/"


def iso(v):
    """'/Date(1792454400000)/' -> '2026-10-20'. Anything else is returned unchanged."""
    m = _DATE.fullmatch(v) if isinstance(v, str) else None
    if not m:
        return v
    return datetime.datetime.fromtimestamp(int(m.group(1)) / 1000, datetime.timezone.utc).date().isoformat()


def clean(rows):
    """Drop Microsoft's __type tag and turn /Date(ms)/ values into ISO dates."""
    def one(r):
        if not isinstance(r, dict):
            return r
        return {k: (iso(v) if k in _DATE_FIELDS else v) for k, v in r.items() if k != "__type"}
    return [one(r) for r in rows] if isinstance(rows, list) else one(rows)


def _http(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}),
                                timeout=timeout) as r:
        return json.load(r)


def call(method, k, site, get=None):
    """One API method -> the value under "d". Raises RuntimeError with the key scrubbed out."""
    url = API + method + "?" + urllib.parse.urlencode({"apikey": k, "siteUrl": site})
    try:
        body = (get or _http)(url)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method}: HTTP {e.code}") from None
    except Exception as e:
        raise RuntimeError(f"{method}: {_scrub(type(e).__name__ + ': ' + str(e), k)}") from None
    if not isinstance(body, dict) or "d" not in body:
        raise RuntimeError(f"{method}: no \"d\" in the answer")
    return clean(body["d"])


def pull(cfg, get=None, save=True, today=None):
    """Call every method. Returns {data:{method: value}, errors:{method: text}, saved:[kinds]}
    or None when there is no key. A failed method is an error, never an empty snapshot."""
    k = key()
    if not k:
        return None
    site = site_url(cfg)
    out = {"site": site, "data": {}, "errors": {}, "saved": []}
    for method, kind in METHODS.items():
        try:
            out["data"][method] = call(method, k, site, get)
        except RuntimeError as e:
            out["errors"][method] = _scrub(e, k)
            continue
        if save and kind:
            history.snapshot(cfg, kind, out["data"][method], date=today)
            out["saved"].append(kind)
    return out


# ── summary ──────────────────────────────────────────────────────────────────────

def _d(s):
    return datetime.date.fromisoformat(s)


def traffic_windows(rows):
    """Impressions/clicks for the last 7 days vs the 7 before, anchored on the newest row."""
    rows = [r for r in rows or [] if isinstance(r.get("Date"), str)]
    if not rows:
        return None
    end = max(_d(r["Date"]) for r in rows)
    cut = end - datetime.timedelta(days=7)
    first = end - datetime.timedelta(days=14)
    cur = [r for r in rows if cut < _d(r["Date"]) <= end]
    prev = [r for r in rows if first < _d(r["Date"]) <= cut]
    s = lambda rs, f: sum(r.get(f) or 0 for r in rs)
    return {"end": end.isoformat(), "days": len(cur), "prev_days": len(prev),
            "impressions": s(cur, "Impressions"), "clicks": s(cur, "Clicks"),
            "prev_impressions": s(prev, "Impressions"), "prev_clicks": s(prev, "Clicks")}


def top_queries(rows, n=5):
    """Aggregate per query across the returned rows; position is impression-weighted."""
    agg = {}
    for r in rows or []:
        q = r.get("Query")
        if not q:
            continue
        a = agg.setdefault(q, {"query": q, "impressions": 0, "clicks": 0, "pw": 0.0, "pn": 0})
        imp = r.get("Impressions") or 0
        a["impressions"] += imp
        a["clicks"] += r.get("Clicks") or 0
        pos = r.get("AvgImpressionPosition")
        if pos is not None and pos >= 0:
            a["pw"] += pos * imp
            a["pn"] += imp
    out = []
    for a in agg.values():
        out.append({"query": a["query"], "impressions": a["impressions"], "clicks": a["clicks"],
                    "position": round(a["pw"] / a["pn"], 1) if a["pn"] else None})
    return sorted(out, key=lambda x: (-x["impressions"], -x["clicks"], x["query"]))[:n]


def index_trend(rows):
    rows = sorted([r for r in rows or [] if r.get("InIndex") is not None and r.get("Date")],
                  key=lambda r: r["Date"])
    if not rows:
        return None
    a, b = rows[0], rows[-1]
    return {"from_date": a["Date"], "from": a["InIndex"], "to_date": b["Date"], "to": b["InIndex"]}


def crawl_errors(rows):
    rows = sorted([r for r in rows or [] if r.get("Date")], key=lambda r: r["Date"])
    if not rows:
        return None
    last = rows[-1]
    return {"date": last["Date"], "last": last.get("CrawlErrors") or 0,
            "total": sum(r.get("CrawlErrors") or 0 for r in rows),
            "c4xx": sum(r.get("Code4xx") or 0 for r in rows),
            "c5xx": sum(r.get("Code5xx") or 0 for r in rows), "days": len(rows)}


def sitemap_count(url, fetch=None, _depth=0):
    """(http_status, number_of_<loc>) for a sitemap; a sitemap index is followed to its children."""
    fetch = fetch or ingest._fetch
    status, _final, xml = fetch(url)
    if status != 200:
        return status, 0
    locs = ingest.LOC.findall(xml)
    if "<sitemapindex" in xml.lower():
        if _depth >= 2:
            return status, 0
        total = 0
        for child in locs[:100]:
            st, n = sitemap_count(child, fetch, _depth + 1)
            total += n
        return status, total
    return status, len(locs)


def feed_checks(feeds, fetch=None):
    """One finding per registered feed whose live sitemap disagrees with Bing's UrlCount."""
    out = []
    for f in feeds or []:
        url, held = f.get("Url"), f.get("UrlCount") or 0
        if not url:
            continue
        status, live = sitemap_count(url, fetch)
        row = {"url": url, "bing": held, "live": live, "status": status, "bing_status": f.get("Status")}
        if status != 200:
            row["problem"] = f"registered feed now answers HTTP {status}; Bing still holds {held} URLs"
        elif live == 0:
            row["problem"] = f"registered feed is now empty; Bing still holds {held} URLs"
        elif live != held:
            row["problem"] = f"Bing holds {held} URLs, the live sitemap lists {live} ({live - held:+d})"
        out.append(row)
    return out


def _pct(a, b):
    return "new" if not b and a else "n/a" if not b else f"{(a - b) / b * 100:+.0f}%"


def summary(res, fetch=None):
    """Short text lines for the pulled data."""
    D, E = res["data"], res["errors"]
    L = [f"bing: {res['site']}  ·  saved {', '.join(res['saved']) or 'nothing'}"]
    t = traffic_windows(D.get("GetRankAndTrafficStats"))
    if t:
        part = "" if t["days"] == 7 and t["prev_days"] == 7 else f" (only {t['days']} and {t['prev_days']} days of data)"
        L.append(f"traffic to {t['end']}, last 7 days vs the 7 before: impressions {t['impressions']} vs "
                 f"{t['prev_impressions']} ({_pct(t['impressions'], t['prev_impressions'])}), clicks "
                 f"{t['clicks']} vs {t['prev_clicks']} ({_pct(t['clicks'], t['prev_clicks'])}){part}")
    it = index_trend(D.get("GetCrawlStats"))
    if it:
        L.append(f"InIndex: {it['from']} on {it['from_date']} -> {it['to']} on {it['to_date']}")
    tq = top_queries(D.get("GetQueryStats"))
    if tq:
        L.append("top queries: " + "; ".join(
            f"{q['query']} ({q['impressions']} imp, {q['clicks']} clicks"
            + (f", pos {q['position']:g}" if q["position"] is not None else "") + ")" for q in tq))
    ce = crawl_errors(D.get("GetCrawlStats"))
    if ce:
        L.append(f"crawl errors: {ce['last']} on {ce['date']}; {ce['total']} over {ce['days']} days "
                 f"(4xx {ce['c4xx']}, 5xx {ce['c5xx']})")
    if "GetCrawlIssues" in D:
        L.append(f"crawl issues listed by Bing: {len(D['GetCrawlIssues'] or [])}")
    feeds = D.get("GetFeeds")
    if feeds is not None:
        checks = feed_checks(feeds, fetch)
        bad = [c for c in checks if c.get("problem")]
        L.append(f"feeds: {len(checks)} registered, {len(bad)} differ from the live sitemap")
        for c in bad:
            L.append(f"  ! {c['url']}: {c['problem']}")
        res["feed_checks"] = checks
    q = D.get("GetUrlSubmissionQuota")
    if isinstance(q, dict) and q.get("DailyQuota") is not None:
        L.append(f"URL submission quota: {q.get('DailyQuota')} a day, {q.get('MonthlyQuota')} a month")
    for m, e in E.items():
        L.append(f"  ! {e}")
    return L


def run(cfg, get=None, fetch=None, save=True, today=None):
    """CLI entry: (lines to print, ok). A missing key is a clean skip (ok); all methods failing is not."""
    res = pull(cfg, get=get, save=save, today=today)
    if res is None:
        return [NO_KEY], True
    if not res["data"]:
        return ([f"bing: every method failed for {res['site']}"]
                + [f"  ! {e}" for e in res["errors"].values()]), False
    return summary(res, fetch), True
