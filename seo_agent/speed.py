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
from pathlib import Path

FIELD = {"lcp": (2500, 4000), "inp": (200, 500), "cls": (0.1, 0.25)}  # good, poor (ms / unitless)


def _verdict(metric, v):
    if v is None:
        return None
    good, poor = FIELD[metric]
    return "good" if v <= good else "poor" if v > poor else "needs-improvement"


def psi(url, key=None, strategy="mobile", timeout=60):
    """Lighthouse lab data via PageSpeed Insights (performance + accessibility)."""
    q = [("url", url), ("strategy", strategy), ("category", "performance"), ("category", "accessibility")]
    if key:
        q.append(("key", key))
    api = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(api, timeout=timeout) as r:
            d = json.load(r)
    except Exception as e:
        return {"error": str(e)}
    lh = d.get("lighthouseResult", {})
    au = lh.get("audits", {})
    cat = lh.get("categories", {})
    num = lambda k: au.get(k, {}).get("numericValue")
    pct = lambda c: round((cat.get(c, {}).get("score") or 0) * 100)
    return {"perf_score": pct("performance"), "a11y_score": pct("accessibility"),
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


def sample_urls(cfg, corpus, n=None):
    """Representative sampling instead of 'first N crawled': homepage + the top
    GSC-traffic pages + one page per top-level template/section. On a 10k-page site a
    blind sample misses the templates that matter; this covers money pages + one of
    each layout (pages sharing a template share their CWV)."""
    n = n or cfg.get("speed", {}).get("max_urls", 10)
    site = (cfg.get("site") or "").rstrip("/")
    picked, seen = [], set()

    def add(u):
        u = (u or "").rstrip("/")
        if u and u not in seen:
            seen.add(u)
            picked.append(u)
    add(site)
    try:  # money pages first — where CWV impact is largest
        from . import history
        snap = history.latest(cfg, "gsc_pages") or {}
        for r in sorted(snap.get("data", []), key=lambda r: -r.get("clicks", 0))[: n // 2]:
            add(r.get("page"))
    except Exception:
        pass
    sections = {}
    for c in corpus:  # one representative per top-level section (template coverage)
        path = c.get("url", "").replace(site, "").strip("/")
        sec = path.split("/")[0] if path else ""
        if sec and sec not in sections:
            sections[sec] = c["url"]
    for u in sections.values():
        if len(picked) >= n:
            break
        add(u)
    for c in corpus:  # fill any remainder
        if len(picked) >= n:
            break
        add(c.get("url"))
    return picked[:n]


def _lh_parse(d):
    """Lighthouse CLI JSON → the same lab shape psi() returns."""
    au, cat = d.get("audits", {}), d.get("categories", {})
    num = lambda k: au.get(k, {}).get("numericValue")
    pct = lambda c: round((cat.get(c, {}).get("score") or 0) * 100)
    return {"perf_score": pct("performance"), "a11y_score": pct("accessibility"),
            "lab_lcp_ms": num("largest-contentful-paint"),
            "lab_cls": num("cumulative-layout-shift"),
            "lab_tbt_ms": num("total-blocking-time"), "transport": "lighthouse-local"}


def _lighthouse(url, strategy="mobile", timeout=180):
    """OSS lab data with NO key or quota: the open-source Lighthouse CLI, run locally
    (`npm i -g lighthouse` or via npx). Same engine PSI uses, on your machine."""
    import shutil
    import subprocess
    import tempfile
    binp = shutil.which("lighthouse")
    cmd = [binp] if binp else (["npx", "--yes", "lighthouse"] if shutil.which("npx") else None)
    if not cmd:
        return None
    outp = Path(tempfile.mkdtemp()) / "lh.json"
    args = cmd + [url, "--output=json", f"--output-path={outp}", "--quiet",
                  "--only-categories=performance,accessibility",
                  '--chrome-flags=--headless --no-sandbox']
    if strategy == "desktop":
        args.append("--preset=desktop")
    try:
        subprocess.run(args, check=True, capture_output=True, timeout=timeout)
        return _lh_parse(json.loads(outp.read_text()))
    except Exception:
        return None


def check(cfg, urls, snapshot=True):
    key = os.environ.get("PAGESPEED_API_KEY")
    strat = cfg.get("speed", {}).get("strategy", "mobile")
    out = []
    use_lh = not key  # keyless → prefer local OSS Lighthouse (no quota); PSI as last resort
    for i, u in enumerate(urls[: cfg.get("speed", {}).get("max_urls", 10)]):
        lab = (_lighthouse(u, strat) if use_lh and i < 3 else None) or psi(u, key, strat)
        out.append({"url": u, **lab, **crux(u, key)})
    origin = (cfg.get("site") or "").rstrip("/")
    res = {"origin": {"url": origin, **crux(origin, key, origin=True)} if origin else {},
           "pages": out, "has_key": bool(key)}
    if snapshot and out:  # CWV history — trend, not point-in-time (critique fix)
        try:
            from . import history
            history.snapshot(cfg, "cwv", [{"url": p["url"], "perf": p.get("performance"),
                                           "lcp": p.get("lcp"), "inp": p.get("inp"),
                                           "cls": p.get("cls")} for p in out])
            res["trend"] = trend(cfg)
        except Exception:
            pass
    return res


def trend(cfg):
    """Origin-level CWV movement across the two most recent snapshots."""
    import json as _json
    from . import history
    files = history.snapshots(cfg, "cwv")
    if len(files) < 2:
        return None
    prev, curr = _json.load(open(files[-2])), _json.load(open(files[-1]))
    avg = lambda s, k: (lambda v: round(sum(v) / len(v), 1) if v else None)(
        [r[k] for r in s.get("data", []) if isinstance(r.get(k), (int, float))])
    return {"from": prev.get("date"), "to": curr.get("date"),
            "perf": (avg(prev, "perf"), avg(curr, "perf")),
            "lcp": (avg(prev, "lcp"), avg(curr, "lcp"))}
