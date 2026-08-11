"""Site ingestion — crawl a target's sitemap and build a corpus the rest of the
pipeline reads. Works on ANY site (no CMS coupling): sitemap → page URLs →
title / meta / headings / body text, plus the signals the Site Doctor needs
(canonical, meta-robots, H1s, the internal-link graph, word count, JSON-LD,
HTTP status) → corpus.json.

Lightweight: urllib + regex only, no bs4/lxml."""
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

from . import render

UA = "Mozilla/5.0 (compatible; seo-content-pipeline/1.0; +https://claude.com/claude-code)"
_MAX_BYTES = 8 * 1024 * 1024   # SEC-M3: cap response size (parser/memory DoS on hostile sites)


def _url_ok(url):
    """SEC-M3: only fetch http(s) to public hosts. Blocks file://, ftp://, data:, and
    SSRF to loopback / private / link-local (cloud-metadata) / internal addresses fed via
    a malicious sitemap or spider-discovered link."""
    import ipaddress
    import socket
    try:
        pu = urlparse(url)
    except ValueError:
        return False
    if pu.scheme not in ("http", "https"):
        return False
    host = pu.hostname or ""
    if not host or host.lower() == "localhost":
        return False
    try:  # resolve; reject if ANY resolved address is non-public
        for fam, _t, _p, _c, sa in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(sa[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
    except Exception:
        return False
    return True


TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")
SCRIPT = re.compile(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", re.S | re.I)
LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
LASTMOD = re.compile(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", re.I)
URLBLOCK = re.compile(r"<url>(.*?)</url>", re.S | re.I)
HREF = re.compile(r'<a\b[^>]*\bhref=["\'](.*?)["\']', re.I)


def _get(url, timeout=30):
    if not _url_ok(url):
        raise ValueError(f"blocked non-public/non-http URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(_MAX_BYTES).decode("utf-8", "ignore")


def _fetch(url, timeout=30):
    """(status, final_url, html) — captures redirects + HTTP errors for the audit."""
    if not _url_ok(url):
        return 0, url, ""   # SEC-M3: refuse file://, loopback, private/link-local, etc.
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            final = r.geturl()
            if final != url and not _url_ok(final):   # a redirect can't smuggle us to an internal host
                return 0, url, ""
            return r.getcode(), final, r.read(_MAX_BYTES).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, url, ""


def sitemap_urls(sitemap, cap=8000, _depth=0):
    """Page URLs from a sitemap or sitemap-index (recurses one level)."""
    try:
        xml = _get(sitemap)
    except Exception as e:
        print(f"  ! sitemap {sitemap}: {e}", file=sys.stderr)
        return []
    locs = LOC.findall(xml)
    if "<sitemapindex" in xml.lower() and _depth < 3:
        urls = []
        for child in locs:
            urls += sitemap_urls(child, cap, _depth + 1)
            if len(urls) >= cap:
                break
        return urls[:cap]
    return locs[:cap]


def sitemap_entries(sitemap, cap=8000, _depth=0):
    """[{loc, lastmod, sitemap}] across a sitemap or sitemap-index — the raw
    input to the sitemap doctor (lastmod format/freshness + coverage)."""
    try:
        xml = _get(sitemap)
    except Exception:
        return []
    if "<sitemapindex" in xml.lower() and _depth < 3:
        out = []
        for child in LOC.findall(xml):
            out += sitemap_entries(child, cap, _depth + 1)
            if len(out) >= cap:
                break
        return out[:cap]
    ents = []
    for block in URLBLOCK.findall(xml):
        loc = LOC.search(block)
        if loc:
            lm = LASTMOD.search(block)
            ents.append({"loc": loc.group(1).strip(),
                         "lastmod": lm.group(1).strip() if lm else None,
                         "sitemap": sitemap})
    if not ents:  # sitemaps that list <loc> without <url> wrappers
        ents = [{"loc": l, "lastmod": None, "sitemap": sitemap} for l in LOC.findall(xml)]
    return ents[:cap]


def _first(pattern, text, flags=re.S | re.I):
    m = re.search(pattern, text, flags)
    return html.unescape(TAG.sub("", m.group(1))).strip() if m else ""


def _meta_content(doc, *keys, attrs=("name", "property")):
    """Extract a <meta> tag's `content` by its name/property key, regardless of
    attribute order. Naive `name=...content=...` regexes miss CMSs (Webflow, Ghost,
    many Wix/Squarespace themes) that emit `content=...` BEFORE `name=...`."""
    want = {k.lower() for k in keys}
    for tag in re.findall(r'<meta\b[^>]*>', doc, re.I):
        kv = {m.group(1).lower(): m.group(2)
              for m in re.finditer(r'([A-Za-z][\w:-]*)\s*=\s*["\'](.*?)["\']', tag)}
        key = next((kv[a] for a in attrs if a in kv), None)
        if key and key.lower() in want and kv.get("content"):
            return html.unescape(kv["content"]).strip()
    return ""


def _jsonld_nodes(doc):
    """Yield every JSON-LD object in the page, flattening @graph and arrays."""
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', doc, re.I | re.S):
        raw = m.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        stack = [data]
        while stack:
            n = stack.pop()
            if isinstance(n, list):
                stack.extend(n)
            elif isinstance(n, dict):
                if isinstance(n.get("@graph"), list):
                    stack.extend(n["@graph"])
                yield n


_ARTICLE_TYPES = {"article", "blogposting", "newsarticle", "techarticle", "liveblogposting"}


def _jsonld_meta(doc):
    """Dates + author from Article/BlogPosting JSON-LD — where Webflow, Ghost and many
    CMSs put them instead of OG meta. Without this the E-E-A-T / GEO checks under-count
    dated + authored pages. Returns {published, modified, author} (blank if absent)."""
    out = {"published": "", "modified": "", "author": ""}
    for n in _jsonld_nodes(doc):
        t = n.get("@type", "")
        types = {x.lower() for x in (t if isinstance(t, list) else [t]) if isinstance(x, str)}
        if not types & _ARTICLE_TYPES:
            continue
        au = n.get("author")
        name = ""
        if isinstance(au, dict):
            name = au.get("name") or ""
        elif isinstance(au, list) and au:
            name = (au[0].get("name") if isinstance(au[0], dict) else str(au[0])) or ""
        elif isinstance(au, str):
            name = au
        pub, mod = n.get("datePublished") or n.get("dateCreated") or "", n.get("dateModified") or ""
        out["published"] = out["published"] or (pub if isinstance(pub, str) else "")
        out["modified"] = out["modified"] or (mod if isinstance(mod, str) else "")
        out["author"] = out["author"] or (name.strip() if isinstance(name, str) else "")
        if out["published"] and out["author"]:
            break
    return out


def extract(url, doc):
    body = SCRIPT.sub(" ", doc)
    title = _first(r"<title[^>]*>(.*?)</title>", doc)
    desc = _meta_content(doc, "description")
    headings = [html.unescape(TAG.sub("", h)).strip()
                for h in re.findall(r"<h[12][^>]*>(.*?)</h[12]>", body, re.S | re.I)]
    headings = [h for h in headings if h][:20]
    h1 = [html.unescape(TAG.sub("", h)).strip()
          for h in re.findall(r"<h1[^>]*>(.*?)</h1>", body, re.S | re.I)]
    h1 = [h for h in h1 if h]
    text = WS.sub(" ", html.unescape(TAG.sub(" ", body))).strip()
    canonical = ""
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*>', doc, re.I)
    if m:
        hm = re.search(r'href=["\'](.*?)["\']', m.group(0), re.I)
        canonical = html.unescape(hm.group(1)).strip() if hm else ""
    robots = _meta_content(doc, "robots").lower()
    links = [h for h in HREF.findall(doc)
             if h and not h.startswith(("#", "mailto:", "tel:", "javascript:"))]
    hreflang = []
    for tag in re.findall(r'<link[^>]+rel=["\']alternate["\'][^>]*>', doc, re.I):
        la = re.search(r'hreflang=["\'](.*?)["\']', tag, re.I)
        hr = re.search(r'href=["\'](.*?)["\']', tag, re.I)
        if la and hr:
            hreflang.append({"lang": la.group(1).lower(), "href": hr.group(1)})
    jsonld = bool(re.search(r'<script[^>]+type=["\']application/ld\+json["\']', doc, re.I))
    # E-E-A-T / accessibility signals
    host = urlparse(url).netloc.lower()
    ext_links = sum(1 for h in links if h.startswith("http")
                    and urlparse(h).netloc.lower() not in ("", host))
    lang_m = re.search(r'<html[^>]+lang=["\']([a-zA-Z-]+)["\']', doc, re.I)
    lang = lang_m.group(1).lower() if lang_m else ""
    imgs = re.findall(r'<img\b[^>]*>', doc, re.I)
    img_alt = sum(1 for tg in imgs if re.search(r'\balt=["\'][^"\']+["\']', tg, re.I))
    author = _meta_content(doc, "author", "article:author")
    published = _meta_content(doc, "article:published_time")
    modified = _meta_content(doc, "article:modified_time")
    if not (author and published and modified):  # fall back to Article/BlogPosting JSON-LD
        _ld = _jsonld_meta(doc)
        published = published or _ld["published"]
        modified = modified or _ld["modified"]
        author = author or _ld["author"]
    heading_levels = [int(x) for x in re.findall(r'<h([1-6])[^>]*>', body, re.I)]
    lists = len(re.findall(r'<(?:ul|ol)\b', body, re.I))
    tables = len(re.findall(r'<table\b', body, re.I))
    words = len(text.split())
    # CSR heuristic: near-empty raw body + a SPA mount marker → likely client-rendered.
    csr = words < 50 and bool(re.search(
        r'id=["\'](root|app|__next|__nuxt)["\']|__NEXT_DATA__|ng-version|data-reactroot', doc, re.I))
    viewport = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', doc, re.I))
    jsonld_types = sorted(set(re.findall(r'"@type"\s*:\s*"([A-Za-z]+)"', doc)))[:12]
    return {"url": url, "title": title, "description": desc,
            "headings": headings, "h1": h1, "canonical": canonical, "robots": robots,
            "links": links, "hreflang": hreflang, "words": words, "jsonld": jsonld,
            "jsonld_types": jsonld_types, "viewport": viewport,
            "csr": csr, "lang": lang, "img_total": len(imgs), "img_alt": img_alt,
            "ext_links": ext_links, "author": author, "published": published,
            "modified": modified, "heading_levels": heading_levels,
            "lists": lists, "tables": tables, "text": text[:12000]}


def robots_sitemaps(site):
    """Sitemap: URLs declared in robots.txt — the canonical discovery path when
    the default /sitemap.xml 404s (common)."""
    try:
        txt = _get(site.rstrip("/") + "/robots.txt")
    except Exception:
        return []
    return [l.split(":", 1)[1].strip() for l in txt.splitlines()
            if l.strip().lower().startswith("sitemap:")]


def _match(url, include, exclude, site):
    path = url[len(site):] if site and url.startswith(site) else url
    if exclude and any(x in url for x in exclude):
        return False
    if include and not any(path.startswith(p) for p in include):
        return False
    return True


def _internal_links(rec, host):
    """Resolve a record's raw hrefs to absolute same-host URLs (fragments stripped)."""
    from urllib.parse import urljoin
    base = rec.get("final_url") or rec["url"]
    out = []
    for h in rec.get("links", []) or []:
        try:
            u = urljoin(base, h).split("#")[0]
        except ValueError:
            continue
        pu = urlparse(u)
        if pu.scheme in ("http", "https") and pu.netloc.lower().replace("www.", "") == host:
            out.append(u.rstrip("/"))
    return out


def annotate_graph(corpus, site):
    """Native crawl-depth + inlinks for EVERY crawl mode (the Screaming Frog fields,
    computed ourselves): inlinks = internal pages linking to a URL; crawl_depth =
    BFS clicks from the homepage through the resolved link graph."""
    host = urlparse(site).netloc.lower().replace("www.", "")
    by_url = {(c.get("final_url") or c["url"]).rstrip("/"): c for c in corpus}
    graph, inlinks = {}, {}
    for c in corpus:
        src = (c.get("final_url") or c["url"]).rstrip("/")
        tgts = set(_internal_links(c, host))
        graph[src] = tgts
        for t in tgts:
            if t != src and t in by_url:
                inlinks[t] = inlinks.get(t, 0) + 1
    for u, c in by_url.items():
        c["inlinks"] = inlinks.get(u, 0)
    root = site.rstrip("/")
    frontier, depth = [root], {root: 0}
    while frontier:
        nxt = []
        for u in frontier:
            for t in graph.get(u, ()):
                if t in by_url and t not in depth:
                    depth[t] = depth[u] + 1
                    nxt.append(t)
        frontier = nxt
    for u, c in by_url.items():
        if "crawl_depth" not in c or c["crawl_depth"] is None:
            c["crawl_depth"] = depth.get(u)  # None = unreachable from home (orphan signal)
    return corpus


def build(cfg, out="corpus.json", delay=0.15):
    site = (cfg.get("site") or "").rstrip("/")
    # auto-understand the site first: platform, rendering needs, scale, politeness
    prof = None
    try:
        from . import profile as profmod
        prof = profmod.ensure(cfg)
    except Exception:
        pass
    plan = (prof or {}).get("plan", {})
    crawl_cfg = cfg.get("crawl", {}) or {}
    delay = float(crawl_cfg.get("delay", plan.get("delay", delay)))
    if plan.get("render") and not (cfg.get("render", {}) or {}).get("enabled"):
        cfg.setdefault("render", {})["enabled"] = True
        print("  (profiler: client-rendered site + Playwright present → JS rendering AUTO-ENABLED)")
    elif (prof or {}).get("needs_render") and not plan.get("render") \
            and not (cfg.get("render", {}) or {}).get("enabled"):
        print("  ⚠ profiler: site looks CLIENT-RENDERED and Playwright is not installed — "
              "the crawl will under-report. `pip install playwright && playwright install chromium`")
    urls = sitemap_urls(cfg["sitemap"]) if cfg.get("sitemap") else []
    if not urls and site:                      # configured sitemap missing/404 → discover from robots.txt
        for sm in robots_sitemaps(site):
            urls = sitemap_urls(sm)
            if urls:
                print(f"  (sitemap auto-discovered from robots.txt: {sm})")
                break
    spider_mode = crawl_cfg.get("mode") == "spider" or not urls
    urls = [u for u in dict.fromkeys(urls) if _match(u, cfg.get("include", []),
                                                     cfg.get("exclude", []), site)]
    urls = urls[: cfg.get("max_pages", 400)]
    workers = int(cfg.get("ingest", {}).get("workers", plan.get("workers", 8)))
    if spider_mode:
        return _spider_build(cfg, site, out, delay, workers)
    print(f"ingesting {len(urls)} pages from {cfg.get('sitemap')}")
    corpus = []

    def record(u, status, final, doc):
        rec = extract(u, doc)
        rec["status"], rec["final_url"] = status, final
        return rec

    prevp = Path(out)
    if prevp.exists() and prevp.stat().st_size > 2:  # keep last crawl → `sitediff` change tracking
        Path(out.replace(".json", ".prev.json")).write_text(prevp.read_text())

    def checkpoint(n):                          # interrupt-safe: partial crawls stay usable
        Path(out).write_text(json.dumps(corpus, ensure_ascii=False, indent=1))
        print(f"  …{n}/{len(urls)} (checkpointed)")

    with render.session(cfg) as r:
        if r:  # rendering reuses one browser → serial
            print("  (JavaScript rendering enabled — headless Chromium; serial)")
            for i, u in enumerate(urls, 1):
                try:
                    corpus.append(record(u, *(r.render(u) or _fetch(u))))
                except Exception as e:
                    print(f"  ! {u}: {e}", file=sys.stderr)
                if i % 50 == 0:
                    checkpoint(i)
                time.sleep(delay)
        else:  # raw fetch → parallel (5–10× faster; the crawl bottleneck)
            print(f"  (parallel fetch — {workers} workers)")

            def fetch_one(u):
                return record(u, *_fetch(u))

            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(fetch_one, u): u for u in urls}
                for i, fu in enumerate(as_completed(futs), 1):
                    try:
                        corpus.append(fu.result())
                    except Exception as e:
                        print(f"  ! {futs[fu]}: {e}", file=sys.stderr)
                    if i % 50 == 0:
                        checkpoint(i)
    annotate_graph(corpus, site)               # native crawl_depth + inlinks (all modes)
    Path(out).write_text(json.dumps(corpus, ensure_ascii=False, indent=1))
    print(f"wrote {out} ({len(corpus)} pages)")
    return corpus


def _spider_build(cfg, site, out, delay, workers):
    """Link-following BFS crawl — the LibreCrawl/Screaming-Frog mode, native: for sites
    with no (or partial) sitemaps. Respects robots.txt Disallow + include/exclude,
    tracks true click depth as it goes, and is interrupt-safe like the sitemap crawl."""
    from . import render
    disallows = []
    try:
        from .indexability import _star_disallows
        disallows = _star_disallows(_get(site + "/robots.txt"))
    except Exception:
        pass
    host = urlparse(site).netloc.lower().replace("www.", "")
    inc, exc = cfg.get("include", []), cfg.get("exclude", [])
    max_pages = cfg.get("max_pages", 400)
    print(f"spidering {site} (link-following, ≤{max_pages} pages, {workers} workers, "
          f"{len(disallows)} robots rules honored)")
    corpus, seen = [], {site.rstrip("/"): 0}
    frontier = [site.rstrip("/")]

    def ok(u):
        pu = urlparse(u)
        if pu.netloc.lower().replace("www.", "") != host:
            return False
        if any(pu.path.startswith(d) for d in disallows):
            return False
        return _match(u, inc, exc, site)

    prevp = Path(out)
    if prevp.exists() and prevp.stat().st_size > 2:
        Path(out.replace(".json", ".prev.json")).write_text(prevp.read_text())
    with render.session(cfg) as r:
        while frontier and len(corpus) < max_pages:
            batch, frontier = frontier[:workers], frontier[workers:]

            def fetch_one(u):
                res = (r.render(u) if r else None) or _fetch(u)
                rec = extract(u, res[2])
                rec["status"], rec["final_url"] = res[0], res[1]
                rec["crawl_depth"] = seen.get(u.rstrip("/"), 0)
                return rec
            with ThreadPoolExecutor(max_workers=1 if r else workers) as ex:
                for fu in as_completed({ex.submit(fetch_one, u): u for u in batch}):
                    try:
                        rec = fu.result()
                    except Exception as e:
                        print(f"  ! {e}", file=sys.stderr)
                        continue
                    corpus.append(rec)
                    d = rec["crawl_depth"]
                    for link in _internal_links(rec, host):
                        if link not in seen and ok(link) and len(seen) < max_pages * 3:
                            seen[link] = d + 1
                            frontier.append(link)
            if len(corpus) % 50 < workers:
                Path(out).write_text(json.dumps(corpus, ensure_ascii=False, indent=1))
                print(f"  …{len(corpus)} crawled · {len(frontier)} queued (checkpointed)")
            time.sleep(delay)
    annotate_graph(corpus, site)
    Path(out).write_text(json.dumps(corpus, ensure_ascii=False, indent=1))
    print(f"wrote {out} ({len(corpus)} pages, max depth "
          f"{max((c.get('crawl_depth') or 0) for c in corpus) if corpus else 0})")
    return corpus
