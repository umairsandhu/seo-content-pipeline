"""Site ingestion — crawl a target's sitemap and build a corpus the rest of the
pipeline reads. Works on ANY site (no CMS coupling): sitemap → page URLs →
title / meta description / headings / body text → corpus.json.

Lightweight: urllib + regex only, no bs4/lxml."""
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (compatible; seo-content-pipeline/1.0; +https://claude.com/claude-code)"
TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")
SCRIPT = re.compile(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", re.S | re.I)
LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def sitemap_urls(sitemap, cap=8000, _depth=0):
    """Return page URLs from a sitemap or sitemap-index (recurses one level)."""
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
    text = WS.sub(" ", html.unescape(TAG.sub(" ", body))).strip()
    return {"url": url, "title": title, "description": desc,
            "headings": headings, "text": text[:12000]}


def _match(url, include, exclude, site):
    path = url[len(site):] if site and url.startswith(site) else url
    if exclude and any(x in url for x in exclude):
        return False
    if include and not any(path.startswith(p) for p in include):
        return False
    return True


def build(cfg, out="corpus.json", delay=0.15):
    site = (cfg.get("site") or "").rstrip("/")
    urls = sitemap_urls(cfg["sitemap"])
    urls = [u for u in dict.fromkeys(urls) if _match(u, cfg.get("include", []),
                                                     cfg.get("exclude", []), site)]
    urls = urls[: cfg.get("max_pages", 400)]
    print(f"ingesting {len(urls)} pages from {cfg['sitemap']}")
    corpus = []
    for i, u in enumerate(urls, 1):
        try:
            corpus.append(extract(u, _get(u)))
        except Exception as e:
            print(f"  ! {u}: {e}", file=sys.stderr)
        if i % 25 == 0:
            print(f"  …{i}/{len(urls)}")
        time.sleep(delay)
    Path(out).write_text(json.dumps(corpus, ensure_ascii=False, indent=1))
    print(f"wrote {out} ({len(corpus)} pages)")
    return corpus
