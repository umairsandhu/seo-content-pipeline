"""Competitor watch — monthly sitemap diff: what did each competitor newly publish
since last run? Content gaps tell you what they *rank* for; this tells you what they're
*doing right now* — the leading indicator. Snapshots each competitor's URL set to
history and diffs run-over-run. Stdlib (urllib) — no paid API needed. Site-agnostic."""
import re
import urllib.request
from urllib.parse import urlparse

from . import history, ingest


def _find_sitemap(domain):
    base = domain if domain.startswith("http") else "https://" + domain
    base = base.rstrip("/")
    for url in (base + "/sitemap.xml", base + "/sitemap_index.xml"):
        try:
            head = urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15).read(2000).decode("utf-8", "ignore")
            if "<urlset" in head.lower() or "<sitemapindex" in head.lower():
                return url
        except Exception:
            pass
    try:  # robots.txt reference
        robots = urllib.request.urlopen(
            urllib.request.Request(base + "/robots.txt", headers={"User-Agent": "Mozilla/5.0"}), timeout=15).read().decode("utf-8", "ignore")
        m = re.search(r"(?im)^sitemap:\s*(\S+)", robots)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return None


def delta(cfg, cap=3000):
    """For each competitor, snapshot URLs and return what's new vs the last snapshot."""
    out = []
    for comp in cfg.get("competitors", []):
        dom = urlparse(comp if "//" in comp else "//" + comp).netloc.replace("www.", "") or comp
        sm = _find_sitemap(comp)
        urls = set(ingest.sitemap_urls(sm, cap=cap)) if sm else set()
        prev = history.latest(cfg, f"comp_urls_{dom}")
        prev_urls = set((prev or {}).get("data") or [])
        new = sorted(urls - prev_urls) if prev_urls else []
        history.snapshot(cfg, f"comp_urls_{dom}", sorted(urls))
        out.append({"competitor": dom, "sitemap": sm, "total": len(urls),
                    "new_since_last": new[:40], "new_count": len(new),
                    "first_run": not prev_urls})
    return out


def render_md(cfg, rows):
    L = [f"# Competitor watch — sitemap delta — {cfg.get('site','site')}", ""]
    if not rows:
        return "\n".join(L + ["_No competitors set — add `competitors` to config.json._"])
    for r in rows:
        if not r["sitemap"]:
            L.append(f"## {r['competitor']} — ⚠ no sitemap found"); continue
        if r["first_run"]:
            L.append(f"## {r['competitor']} — baselined {r['total']} URLs (deltas from next run)")
        else:
            L.append(f"## {r['competitor']} — **{r['new_count']} new** of {r['total']} URLs")
            for u in r["new_since_last"][:20]:
                L.append(f"- 🆕 {u}")
        L.append("")
    L.append("_Run monthly. New URLs = what competitors are betting on — mine them for your own plan._")
    return "\n".join(L)
