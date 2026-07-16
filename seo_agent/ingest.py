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


def extract(url, doc):
    body = SCRIPT.sub(" ", doc)
    title = _first(r"<title[^>]*>(.*?)</title>", doc)
    desc = ""
    m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', doc, re.I | re.S)
    if m:
        desc = html.unescape(m.group(1)).strip()
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
    robots = ""
    m = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'](.*?)["\']', doc, re.I | re.S)
    if m:
        robots = html.unescape(m.group(1)).strip().lower()
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
    au = re.search(r'<meta[^>]+(?:name|property)=["\'](?:author|article:author)["\'][^>]+content=["\'](.*?)["\']', doc, re.I)
    author = html.unescape(au.group(1)).strip() if au else ""
    _mt = lambda p: (re.search(r'<meta[^>]+property=["\']' + p + r'["\'][^>]+content=["\'](.*?)["\']', doc, re.I) or [None, ""])[1]
    published, modified = _mt("article:published_time"), _mt("article:modified_time")
    heading_levels = [int(x) for x in re.findall(r'<h([1-6])[^>]*>', body, re.I)]
    lists = len(re.findall(r'<(?:ul|ol)\b', body, re.I))
    tables = len(re.findall(r'<table\b', body, re.I))
    words = len(text.split())
    # CSR heuristic: near-empty raw body + a SPA mount marker → likely client-rendered.
    csr = words < 50 and bool(re.search(
        r'id=["\'](root|app|__next|__nuxt)["\']|__NEXT_DATA__|ng-version|data-reactroot', doc, re.I))
    return {"url": url, "title": title, "description": desc,
            "headings": headings, "h1": h1, "canonical": canonical, "robots": robots,
            "links": links, "hreflang": hreflang, "words": words, "jsonld": jsonld,
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
