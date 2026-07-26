"""Optional JavaScript rendering (build-loop roadmap #4). SPA / client-rendered
pages return near-empty HTML to a raw fetch, so the Site Doctor mis-reports them
(missing content, no H1, "thin"). When enabled, each page is rendered in headless
Chromium first — matching what Googlebot does — before extraction.

Optional + graceful, like the GSC/embeddings backends: needs
`pip install playwright && playwright install chromium` and render.enabled=true
(or SEO_RENDER=1). Without it, ingest uses raw HTML and the audit's CSR heuristic
(ingest sets `csr`) flags likely client-rendered pages so you know to turn it on.

One browser is reused across the crawl via `session(cfg)` (a context manager that
yields a renderer, or None when disabled/unavailable)."""
import os
import sys
from contextlib import contextmanager

UA = "Mozilla/5.0 (compatible; seo-content-pipeline/1.0; +https://claude.com/claude-code)"


def enabled(cfg):
    if os.environ.get("SEO_RENDER", "").lower() in ("1", "true"):
        return True
    return bool((cfg or {}).get("render", {}).get("enabled"))


def available():
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


class _Renderer:
    def __init__(self, browser, cfg):
        self.browser = browser
        r = (cfg or {}).get("render", {})
        self.wait = r.get("wait", "networkidle")
        self.timeout = int(r.get("timeout", 15)) * 1000

    def render(self, url):
        """(status, final_url, html) like ingest._fetch, or None to fall back."""
        page = self.browser.new_page(user_agent=UA)
        try:
            resp = page.goto(url, wait_until=self.wait, timeout=self.timeout)
            return (resp.status if resp else 200), page.url, page.content()
        except Exception as e:
            print(f"  ! render {url}: {e}", file=sys.stderr)
            return None
        finally:
            page.close()


@contextmanager
def session(cfg):
    """Yield a renderer (browser reused across the crawl) or None if off/unavailable."""
    if not (enabled(cfg) and available()):
        yield None
        return
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            yield _Renderer(browser, cfg)
        finally:
            browser.close()


def diff(cfg, url):
    """Rendered-vs-raw DOM diff for one URL: what content/links/schema exist only
    AFTER JS runs — i.e. what a raw-HTML audit is blind to. Requires Playwright."""
    import re
    import urllib.request
    from . import ingest
    if not available():
        return {"error": "no headless browser — pip install playwright && playwright install chromium"}
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        return {"error": f"raw fetch failed: {e}"}
    force = dict(cfg or {}, render={"enabled": True})
    with session(force) as r:
        if not r:
            return {"error": "renderer unavailable"}
        out = r.render(url)
    if not out:
        return {"error": "render failed"}
    rendered = out[2]
    ex_raw, ex_ren = ingest.extract(url, raw), ingest.extract(url, rendered)
    words_gain = (ex_ren.get("words", 0) or 0) - (ex_raw.get("words", 0) or 0)
    links_gain = len(set(ex_ren.get("links", [])) - set(ex_raw.get("links", [])))
    schema_gain = bool(re.search(r"application/ld\+json", rendered, re.I)) and not \
        bool(re.search(r"application/ld\+json", raw, re.I))
    h1_gain = len(ex_ren.get("h1", []) or []) - len(ex_raw.get("h1", []) or [])
    return {"url": url, "raw_words": ex_raw.get("words", 0), "rendered_words": ex_ren.get("words", 0),
            "words_gain": words_gain, "links_only_in_rendered": links_gain,
            "schema_only_in_rendered": schema_gain, "h1_gain": h1_gain,
            "csr_risk": words_gain > 200 or links_gain > 10 or schema_gain}


def render_md(cfg, d):
    if d.get("error"):
        return f"# Render diff\n\n_{d['error']}_"
    flag = "🔴 client-rendered — audit with render.enabled" if d["csr_risk"] else "✅ raw HTML is representative"
    return (f"# Rendered-vs-raw diff — {d['url']}\n\n{flag}\n\n"
            f"- words: raw {d['raw_words']} → rendered {d['rendered_words']} (+{d['words_gain']})\n"
            f"- links only after JS: {d['links_only_in_rendered']}\n"
            f"- H1s gained after JS: {d['h1_gain']}\n"
            f"- JSON-LD injected by JS: {'yes' if d['schema_only_in_rendered'] else 'no'}")
