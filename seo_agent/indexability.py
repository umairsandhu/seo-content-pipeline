"""Indexability decision matrix + redirect health — the findings a technical SEO
manager is paid to catch, computed from the corpus (offline) plus a bounded live
trace of redirect chains:

  · canonical chains (A→B→C: A's canonical points at a page whose canonical differs)
  · canonical → non-indexable target (404/noindex — Google drops both signals)
  · cross-domain canonicals (usually a migration leftover or a scraper template)
  · noindex + robots.txt-disallow conflict (Google can't crawl the page, so it can
    NEVER see the noindex — the page can linger in the index)
  · noindex + canonical on the same page (contradictory signals)
  · internal links that point at redirecting URLs (link equity through hops)
  · soft-404s (200-status pages that look like error pages)
  · live redirect-chain trace: hop count, 302-where-301-belongs, loops (≤15 URLs)

Findings use cat "indexability" so `plan`/`autopilot` pick them up automatically.
Stdlib only; network only for the bounded trace, every call guarded."""
import re
import urllib.parse
import urllib.request

_SOFT404 = re.compile(r"not found|404|page (?:missing|doesn.?t exist)|no longer available", re.I)


def _host(u):
    return urllib.parse.urlparse(u or "").netloc.lower().replace("www.", "")


def _star_disallows(robots_txt):
    """Path prefixes disallowed for User-agent: * (simple, prefix-only)."""
    out, applies = [], False
    for line in (robots_txt or "").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            applies = v == "*"
        elif k == "disallow" and applies and v and v != "/":
            out.append(v)
    return out


def check(cfg, corpus, trace=True, max_trace=15):
    F = []
    by_url = {c["url"].rstrip("/"): c for c in corpus}
    site_host = _host(cfg.get("site"))
    disallows = []
    if trace:
        try:
            from . import ingest
            disallows = _star_disallows(ingest._get((cfg.get("site") or "").rstrip("/") + "/robots.txt"))
        except Exception:
            pass

    redirecting = set()
    for c in corpus:
        url, status = c["url"], c.get("status", 200)
        robots = c.get("robots") or ""
        canon = (c.get("canonical") or "").strip().rstrip("/")
        final = (c.get("final_url") or "").rstrip("/")
        if final and final != url.rstrip("/"):
            redirecting.add(url.rstrip("/"))
        if canon and canon != url.rstrip("/"):
            ch = _host(canon)
            if ch and site_host and ch != site_host:
                F.append({"cat": "indexability", "sev": "med", "url": url,
                          "msg": f"cross-domain canonical → {ch} (migration leftover? verify it's intended)"})
            tgt = by_url.get(canon)
            if tgt:
                t_can = (tgt.get("canonical") or "").strip().rstrip("/")
                if t_can and t_can != canon:
                    F.append({"cat": "indexability", "sev": "med", "url": url,
                              "msg": f"canonical CHAIN {url.rsplit('/',1)[-1]} → {canon.rsplit('/',1)[-1]} → "
                                     f"{t_can.rsplit('/',1)[-1]} — point straight at the final URL"})
                if tgt.get("status", 200) != 200 or "noindex" in (tgt.get("robots") or ""):
                    F.append({"cat": "indexability", "sev": "high", "url": url,
                              "msg": f"canonical target is NON-INDEXABLE "
                                     f"({tgt.get('status')}{'/noindex' if 'noindex' in (tgt.get('robots') or '') else ''}) "
                                     "— both pages lose"})
        if "noindex" in robots:
            if canon and canon != url.rstrip("/"):
                F.append({"cat": "indexability", "sev": "low", "url": url,
                          "msg": "noindex + canonical-elsewhere on the same page — contradictory; pick one"})
            path = urllib.parse.urlparse(url).path
            if any(path.startswith(d) for d in disallows):
                F.append({"cat": "indexability", "sev": "high", "url": url,
                          "msg": "noindex AND robots.txt-disallowed — Google can't crawl it, so it can "
                                 "never see the noindex; unblock crawling OR drop the disallow"})
        if status == 200 and (c.get("words") or 0) < 40 and _SOFT404.search(c.get("title") or ""):
            F.append({"cat": "indexability", "sev": "med", "url": url,
                      "msg": "soft-404: returns 200 but looks like an error page — return a real 404/410"})

    # internal links whose target redirects (equity through hops; fix at the source)
    stale = {}
    for c in corpus:
        for l in c.get("links", []) or []:
            if l.rstrip("/") in redirecting:
                stale.setdefault(l.rstrip("/"), 0)
                stale[l.rstrip("/")] += 1
    for tgt, n in sorted(stale.items(), key=lambda kv: -kv[1])[:8]:
        F.append({"cat": "indexability", "sev": "low", "url": tgt,
                  "msg": f"{n} internal link(s) point at this REDIRECTING URL — update them to the destination"})

    if trace and redirecting:
        F += _trace_chains(sorted(redirecting)[:max_trace])
    return F


def _trace_chains(urls, max_hops=6, timeout=10):
    """Follow each redirect hop-by-hop: chains >1 hop, 302-where-permanent, loops."""
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(_NoRedirect)
    F = []
    for u in urls:
        hops, codes, seen, cur = [], [], set(), u
        try:
            for _ in range(max_hops):
                if cur in seen:
                    F.append({"cat": "indexability", "sev": "high", "url": u,
                              "msg": f"redirect LOOP via {cur}"})
                    break
                seen.add(cur)
                req = urllib.request.Request(cur, method="HEAD",
                                             headers={"User-Agent": "Mozilla/5.0 seo-agent"})
                try:
                    opener.open(req, timeout=timeout)
                    break  # 2xx — chain ended
                except urllib.error.HTTPError as e:
                    if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                        codes.append(e.code)
                        cur = urllib.parse.urljoin(cur, e.headers["Location"])
                        hops.append(cur)
                    else:
                        break
        except Exception:
            continue
        if len(hops) > 1:
            F.append({"cat": "indexability", "sev": "med", "url": u,
                      "msg": f"redirect chain of {len(hops)} hops ({' → '.join(str(c) for c in codes)}) — "
                             "redirect straight to the final URL"})
        if codes and codes[0] in (302, 303, 307) and len(hops) >= 1:
            F.append({"cat": "indexability", "sev": "low", "url": u,
                      "msg": f"{codes[0]} (temporary) redirect that looks permanent — use 301/308 to pass signals"})
    return F
