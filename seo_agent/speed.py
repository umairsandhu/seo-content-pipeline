"""Speed / Core Web Vitals check. Two Google APIs, one free Cloud key
(PAGESPEED_API_KEY):
  - PageSpeed Insights → Lighthouse LAB data (perf score, lab LCP/CLS/TBT);
    works keyless at low quota.
  - CrUX API → real-user FIELD data (p75 LCP/INP/CLS); Google is deprecating
    field data from PSI, so field comes from CrUX directly. Needs the key.

2026 thresholds (75th percentile): LCP <2.5s, INP <200ms, CLS <0.1. Degrades to
{} without a key/quota — never blocks the audit."""
import json
import os
import urllib.parse
import urllib.request

FIELD = {"lcp": (2500, 4000), "inp": (200, 500), "cls": (0.1, 0.25)}  # good, poor (ms / unitless)


def _verdict(metric, v):
    if v is None:
        return None
    good, poor = FIELD[metric]
    return "good" if v <= good else "poor" if v > poor else "needs-improvement"


def psi(url, key=None, strategy="mobile", timeout=60):
    """Lighthouse lab data via PageSpeed Insights."""
    q = {"url": url, "strategy": strategy, "category": "performance"}
    if key:
        q["key"] = key
    api = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(api, timeout=timeout) as r:
            d = json.load(r)
    except Exception as e:
        return {"error": str(e)}
    lh = d.get("lighthouseResult", {})
    au = lh.get("audits", {})
    num = lambda k: au.get(k, {}).get("numericValue")
    return {"perf_score": round((lh.get("categories", {}).get("performance", {}).get("score") or 0) * 100),
            "lab_lcp_ms": num("largest-contentful-paint"),
            "lab_cls": num("cumulative-layout-shift"),
            "lab_tbt_ms": num("total-blocking-time")}


def crux(url, key, origin=False, timeout=60):
    """Field (real-user) p75 Core Web Vitals via the CrUX API. Needs a key."""
    if not key:
        return {}
    body = {"origin": url} if origin else {"url": url}
    req = urllib.request.Request(
        "https://chromeuxreport.googleapis.com/v1/records:queryRecord?key=" + key,
        data=json.dumps(body).encode(), method="POST",
        headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            m = json.load(r).get("record", {}).get("metrics", {})
    except Exception:
        return {}  # 404 = not enough real-user data for this URL/origin
    p75 = lambda k: m.get(k, {}).get("percentiles", {}).get("p75")
    lcp, inp, cls = p75("largest_contentful_paint"), p75("interaction_to_next_paint"), p75("cumulative_layout_shift")
    cls = float(cls) if cls is not None else None
    return {"field_lcp_ms": lcp, "field_inp_ms": inp, "field_cls": cls,
            "verdict": {"lcp": _verdict("lcp", lcp), "inp": _verdict("inp", inp),
                        "cls": _verdict("cls", cls)}}


def check(cfg, urls):
    key = os.environ.get("PAGESPEED_API_KEY")
    strat = cfg.get("speed", {}).get("strategy", "mobile")
    out = []
    for u in urls[: cfg.get("speed", {}).get("max_urls", 10)]:
        out.append({"url": u, **psi(u, key, strat), **crux(u, key)})
    origin = (cfg.get("site") or "").rstrip("/")
    return {"origin": {"url": origin, **crux(origin, key, origin=True)} if origin else {},
            "pages": out, "has_key": bool(key)}
