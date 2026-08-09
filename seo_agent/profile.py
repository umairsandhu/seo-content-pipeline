"""Site profiler — auto-understand the site BEFORE crawling, then fix the crawler's
capabilities to match (the LibreCrawl/Screaming-Frog capability, native — no
proprietary tools, no external deps):

  · fingerprint the platform (WordPress, Webflow, Shopify, Ghost, Wix, Squarespace,
    HubSpot, Drupal, Joomla, Next.js, Nuxt, React SPA, Angular …) from the homepage
  · detect whether the site NEEDS JavaScript rendering (CSR shell) and auto-enable
    Playwright when it's installed — else warn loudly instead of under-auditing
  · read robots.txt (Crawl-delay honored, Disallow rules respected by the spider)
  · size the crawl from the sitemap (workers / delay / max_pages) and pick the
    discovery mode: sitemap when one exists, link-following SPIDER when not
  · suggest include-sections, the matching CMS connector, and flag parameter traps

`profile` shows it; `profile --apply` writes the crawler settings into config.json
(render/workers/crawl-delay/mode — capability fixes are auto; cms/include stay
suggestions because they change strategy, not crawlability). `ingest` auto-profiles
on first run. Stdlib only. Site-agnostic."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from . import ingest, state

# marker-regex → (platform, cms-connector suggestion, notes)
_FP = [
    (r"wp-content/|wp-includes/|wp-json", "WordPress", "wordpress"),
    (r"cdn\.shopify\.com|Shopify\.theme|/cdn/shop/", "Shopify", "shopify"),
    (r"website-files\.com|data-wf-page|data-wf-site", "Webflow", "webflow"),
    (r'content=["\']Ghost', "Ghost", "ghost"),
    (r"static\.wixstatic\.com|wix\.com", "Wix", "wix"),
    (r"squarespace\.com|static1\.squarespace", "Squarespace", "file"),
    (r"hs-scripts\.com|hubspot", "HubSpot", "hubspot"),
    (r'content=["\']Drupal', "Drupal", "drupal"),
    (r'content=["\']Joomla', "Joomla", "joomla"),
    (r"__NEXT_DATA__|/_next/", "Next.js", None),
    (r"__nuxt|/_nuxt/", "Nuxt", None),
    (r"ng-version=", "Angular", None),
    (r'data-reactroot|id=["\']root["\']', "React app", None),
]


def _crawl_delay(robots_txt):
    applies, delay = False, None
    for line in (robots_txt or "").splitlines():
        line = line.split("#")[0].strip()
        k, _, v = line.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            applies = v == "*"
        elif k == "crawl-delay" and applies:
            try:
                delay = float(v)
            except ValueError:
                pass
    return delay


def run(cfg):
    site = (cfg.get("site") or "").rstrip("/")
    p = {"site": site, "platform": "unknown", "generator": "", "cms_suggestion": None,
         "needs_render": False, "render_available": False, "sitemap_urls": 0,
         "crawl_delay": None, "disallows": 0, "discovery": "spider",
         "include_suggestion": [], "param_urls_pct": 0, "plan": {}}
    try:
        status, final, doc = ingest._fetch(site)
    except Exception as e:
        return {**p, "error": f"could not fetch {site}: {e}"}
    for pat, name, cms in _FP:
        if re.search(pat, doc, re.I):
            p["platform"], p["cms_suggestion"] = name, cms
            break
    gen = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', doc, re.I) \
        or re.search(r'content=["\']([^"\']+)["\'][^>]+name=["\']generator["\']', doc, re.I)
    p["generator"] = gen.group(1) if gen else ""
    home = ingest.extract(site, doc)
    p["needs_render"] = bool(home.get("csr")) or (home.get("words", 0) < 40
                                                  and p["platform"] in ("Next.js", "Nuxt", "React app", "Angular"))
    try:
        import playwright  # noqa: F401
        p["render_available"] = True
    except ImportError:
        pass
    robots = ""
    try:
        robots = ingest._get(site + "/robots.txt")
    except Exception:
        pass
    p["crawl_delay"] = _crawl_delay(robots)
    p["disallows"] = sum(1 for l in robots.splitlines() if l.strip().lower().startswith("disallow:")
                         and l.split(":", 1)[1].strip())
    urls = []
    try:
        urls = ingest.sitemap_urls(cfg.get("sitemap") or site + "/sitemap.xml")
    except Exception:
        pass
    if not urls:
        for sm in ingest.robots_sitemaps(site):
            try:
                urls = ingest.sitemap_urls(sm)
            except Exception:
                continue
            if urls:
                break
    p["sitemap_urls"] = len(urls)
    p["discovery"] = "sitemap" if urls else "spider"
    if urls:
        p["param_urls_pct"] = round(100 * sum(1 for u in urls if "?" in u) / len(urls))
        secs = {}
        for u in urls:
            path = urlparse(u).path.strip("/")
            sec = path.split("/")[0] if path else ""
            if sec:
                secs[sec] = secs.get(sec, 0) + 1
        p["include_suggestion"] = [f"/{s}/" for s, n in
                                   sorted(secs.items(), key=lambda kv: -kv[1])[:3] if n >= 5]
    n = p["sitemap_urls"]
    p["plan"] = {"mode": p["discovery"],
                 "render": p["needs_render"] and p["render_available"],
                 "workers": 4 if (n and n < 100) else 8 if n < 2000 else 12,
                 "delay": max(p["crawl_delay"] or 0, 0.3 if p["platform"] == "WordPress" else 0.15),
                 "max_pages": min(max(n, 100), cfg.get("max_pages", 400)) if n else cfg.get("max_pages", 400)}
    state.write(cfg, "profile", p)
    return p


def apply(cfg, config_path="config.json"):
    """Write the CAPABILITY fixes into config.json (crawlability = auto); strategy
    fields (cms.type, include) stay suggestions in the report."""
    p = run(cfg)
    if p.get("error"):
        return p
    path = Path(config_path)
    raw = json.loads(path.read_text()) if path.exists() else {}
    raw.setdefault("render", {})["enabled"] = bool(p["plan"]["render"])
    raw.setdefault("ingest", {})["workers"] = p["plan"]["workers"]
    raw.setdefault("crawl", {})
    raw["crawl"].update({"mode": p["plan"]["mode"], "delay": p["plan"]["delay"]})
    raw["max_pages"] = p["plan"]["max_pages"]
    path.write_text(json.dumps(raw, indent=2) + "\n")
    return {**p, "applied": ["render.enabled", "ingest.workers", "crawl.mode", "crawl.delay", "max_pages"]}


def ensure(cfg):
    """Auto-profile on first crawl (cached in state/) — `ingest` calls this."""
    return state.read(cfg, "profile", None) or run(cfg)


def render_md(cfg, p=None):
    p = p or run(cfg)
    if p.get("error"):
        return f"# Site profile\n\n- ⚠ {p['error']}"
    L = [f"# Site profile — {p['site']}",
         f"- **Platform:** {p['platform']}" + (f" ({p['generator']})" if p["generator"] else ""),
         f"- **Rendering:** " + ("⚠ CLIENT-RENDERED — " +
                                 ("Playwright found → rendering AUTO-ENABLED" if p["plan"]["render"]
                                  else "install Playwright (`pip install playwright && playwright install chromium`) "
                                       "or the audit will under-report") if p["needs_render"]
                                 else "server-rendered ✓ (no headless browser needed)"),
         f"- **Discovery:** {p['discovery']}" + (f" — {p['sitemap_urls']} sitemap URLs"
                                                 if p["sitemap_urls"] else " — no usable sitemap; the "
                                                 "link-following spider will map the site (depth + inlinks)"),
         f"- **Politeness:** delay {p['plan']['delay']}s" +
         (f" (robots Crawl-delay: {p['crawl_delay']}s honored)" if p["crawl_delay"] else "") +
         f" · {p['plan']['workers']} workers · {p['disallows']} robots Disallow rules (spider respects them)"]
    if p["param_urls_pct"] > 10:
        L.append(f"- ⚠ **Parameter trap risk:** {p['param_urls_pct']}% of sitemap URLs carry query "
                 "strings — check faceted-navigation canonicals (`audit`)")
    if p["cms_suggestion"] and p["cms_suggestion"] != "file":
        L.append(f"- **Suggestion:** set `cms.type: \"{p['cms_suggestion']}\"` (run `cms` for its keys) "
                 "so approved fixes ship straight into the CMS")
    if p["include_suggestion"]:
        L.append(f"- **Suggestion:** `include: {json.dumps(p['include_suggestion'])}` to focus content analysis")
    L.append("\n_`profile --apply` writes the crawler settings into config.json; `ingest` "
             "auto-profiles on first crawl. Capabilities fix themselves — strategy stays yours._")
    return "\n".join(L)
