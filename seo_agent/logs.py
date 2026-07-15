"""Server log-file analysis (build-loop roadmap #2). Server logs are the only
unsampled, 100%-accurate record of real crawler behavior — and the ONLY way to
see AI crawlers (GPTBot, ClaudeBot, PerplexityBot, …) that GSC never reports.

Parses Common/Combined access logs (+ .gz), classifies bots, and reports:
  - hits by bot (search + AI), status distribution;
  - crawl WASTE — search-bot requests to non-200 / low-value URLs;
  - crawl DISTRIBUTION by section (where crawl budget goes);
  - AI-crawler COVERAGE — which of your indexable pages AI bots have/haven't fetched.

stdlib only (urllib/gzip/re). Optional reverse-DNS verify flags spoofed Googlebot."""
import gzip
import re
import socket
from collections import Counter
from urllib.parse import urlparse

from .index import load_corpus

LINE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3})'
    r'\s+\S+(?:\s+"[^"]*"\s+"(?P<ua>[^"]*)")?')

# (UA substring, label, is_ai) — most specific first.
BOTS = [
    ("gptbot", "GPTBot (OpenAI)", True), ("oai-searchbot", "OAI-SearchBot (OpenAI)", True),
    ("chatgpt-user", "ChatGPT-User (OpenAI)", True), ("claudebot", "ClaudeBot (Anthropic)", True),
    ("claude-web", "Claude-Web (Anthropic)", True), ("anthropic-ai", "anthropic-ai (Anthropic)", True),
    ("perplexitybot", "PerplexityBot", True), ("perplexity-user", "Perplexity-User", True),
    ("google-extended", "Google-Extended (AI)", True), ("bytespider", "Bytespider (ByteDance)", True),
    ("ccbot", "CCBot (Common Crawl)", True), ("meta-externalagent", "Meta-ExternalAgent (AI)", True),
    ("amazonbot", "Amazonbot", True), ("applebot-extended", "Applebot-Extended (AI)", True),
    ("googlebot", "Googlebot", False), ("bingbot", "Bingbot", False),
    ("applebot", "Applebot", False), ("yandexbot", "YandexBot", False),
    ("duckduckbot", "DuckDuckBot", False),
]


def classify(ua):
    u = (ua or "").lower()
    for sub, label, is_ai in BOTS:
        if sub in u:
            return label, is_ai
    if "bot" in u or "spider" in u or "crawler" in u:
        return "Other bot", False
    return None, False


def _open(path):
    return gzip.open(path, "rt", errors="ignore") if path.endswith(".gz") else open(path, errors="ignore")


def _section(path):
    parts = [p for p in path.split("/") if p]
    return "/" + parts[0] if parts else "/"


def _verify_googlebot(ips, sample=20):
    """Reverse-DNS a sample of Googlebot-claimed IPs; return spoofed ones (UA
    spoofing is common — legit Googlebot resolves to *.googlebot.com/*.google.com)."""
    spoofed = []
    for ip in list(ips)[:sample]:
        try:
            host = socket.gethostbyaddr(ip)[0]
            if not (host.endswith(".googlebot.com") or host.endswith(".google.com")):
                spoofed.append((ip, host))
        except Exception:
            spoofed.append((ip, "no-rdns"))
    return spoofed


def analyze(cfg, path, verify=False):
    by_bot = Counter()
    ai_hits = Counter()
    status_by = {}          # bot -> Counter(status)
    waste = Counter()       # non-200 path -> count (search bots)
    section = Counter()     # section -> count (Googlebot)
    ai_paths = set()
    gbot_ips = set()
    total = bots = 0

    for line in _open(path):
        m = LINE.search(line)
        if not m:
            continue
        total += 1
        label, is_ai = classify(m.group("ua"))
        if not label:
            continue
        bots += 1
        by_bot[label] += 1
        req = (m.group("req") or "").split()
        p = urlparse(req[1]).path if len(req) >= 2 else "/"
        status = m.group("status")
        status_by.setdefault(label, Counter())[status] += 1
        if is_ai:
            ai_hits[label] += 1
            ai_paths.add(p)
        if label == "Googlebot":
            gbot_ips.add(m.group("ip"))
            section[_section(p)] += 1
            if status != "200":
                waste[f"{status} {p}"] += 1
        elif label == "Bingbot" and status != "200":
            waste[f"{status} {p}"] += 1

    cov = _ai_coverage(cfg, ai_paths)
    return {
        "requests": total, "bot_requests": bots,
        "by_bot": by_bot.most_common(),
        "ai_crawlers": ai_hits.most_common(),
        "ai_crawler_total": sum(ai_hits.values()),
        "search_bot_status": {b: dict(c) for b, c in status_by.items() if b in ("Googlebot", "Bingbot")},
        "crawl_waste_top": waste.most_common(20),
        "crawl_distribution": section.most_common(),
        "ai_coverage": cov,
        "spoofed_googlebot": _verify_googlebot(gbot_ips) if verify else None,
    }


def _ai_coverage(cfg, ai_paths):
    """Which indexable corpus pages have / have not been fetched by an AI crawler."""
    try:
        corpus = load_corpus()
    except Exception:
        return None
    idx = [c for c in corpus if c.get("status", 200) == 200 and "noindex" not in (c.get("robots") or "")]
    seen, missing = [], []
    for c in idx:
        p = urlparse(c.get("final_url") or c["url"]).path.rstrip("/") or "/"
        (seen if p in ai_paths or p + "/" in ai_paths else missing).append(c["url"])
    return {"pages": len(idx), "seen_by_ai": len(seen),
            "not_seen_by_ai": len(missing), "sample_missing": missing[:15]}


def render_md(cfg, r):
    L = [f"# Log-file analysis — {cfg.get('site','site')}",
         f"{r['requests']} requests · {r['bot_requests']} bot · "
         f"{r['ai_crawler_total']} AI-crawler hits", "",
         "## Bots", "| bot | hits |", "|---|--:|"]
    L += [f"| {b} | {n} |" for b, n in r["by_bot"][:15]]
    if r["ai_crawlers"]:
        L += ["", "## AI crawlers (only visible in logs)", "| bot | hits |", "|---|--:|"]
        L += [f"| {b} | {n} |" for b, n in r["ai_crawlers"]]
    cov = r.get("ai_coverage")
    if cov:
        L += ["", f"## AI-crawler coverage — {cov['seen_by_ai']}/{cov['pages']} indexable pages fetched by AI bots"]
        if cov["not_seen_by_ai"]:
            L.append(f"- {cov['not_seen_by_ai']} pages NOT seen by any AI crawler (sample):")
            L += [f"    - {u}" for u in cov["sample_missing"][:8]]
    if r["crawl_waste_top"]:
        L += ["", "## Crawl waste (search bots on non-200)", "| status + path | hits |", "|---|--:|"]
        L += [f"| {p} | {n} |" for p, n in r["crawl_waste_top"][:12]]
    if r["crawl_distribution"]:
        L += ["", "## Crawl distribution (Googlebot, by section)", "| section | hits |", "|---|--:|"]
        L += [f"| {s} | {n} |" for s, n in r["crawl_distribution"][:12]]
    if r.get("spoofed_googlebot"):
        L += ["", f"## ⚠ Spoofed Googlebot ({len(r['spoofed_googlebot'])} IPs failed reverse-DNS)"]
        L += [f"- {ip} → {host}" for ip, host in r["spoofed_googlebot"][:10]]
    return "\n".join(L)
