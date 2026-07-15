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
