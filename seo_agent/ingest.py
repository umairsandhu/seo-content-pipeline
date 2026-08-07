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
TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")
SCRIPT = re.compile(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", re.S | re.I)
LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
LASTMOD = re.compile(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", re.I)
URLBLOCK = re.compile(r"<url>(.*?)</url>", re.S | re.I)
HREF = re.compile(r'<a\b[^>]*\bhref=["\'](.*?)["\']', re.I)


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _fetch(url, timeout=30):
    """(status, final_url, html) — captures redirects + HTTP errors for the audit."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.geturl(), r.read().decode("utf-8", "ignore")
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


def build(cfg, out="corpus.json", delay=0.15):
    site = (cfg.get("site") or "").rstrip("/")
    urls = sitemap_urls(cfg["sitemap"]) if cfg.get("sitemap") else []
    if not urls and site:                      # configured sitemap missing/404 → discover from robots.txt
        for sm in robots_sitemaps(site):
            urls = sitemap_urls(sm)
            if urls:
                print(f"  (sitemap auto-discovered from robots.txt: {sm})")
                break
    urls = [u for u in dict.fromkeys(urls) if _match(u, cfg.get("include", []),
                                                     cfg.get("exclude", []), site)]
    urls = urls[: cfg.get("max_pages", 400)]
    workers = int(cfg.get("ingest", {}).get("workers", 8))
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
    Path(out).write_text(json.dumps(corpus, ensure_ascii=False, indent=1))
    print(f"wrote {out} ({len(corpus)} pages)")
    return corpus
