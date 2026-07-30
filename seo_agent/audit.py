"""Site Doctor — the technical/on-page audit (onboarding stages 5 & 6). Runs
off corpus.json (extend `ingest` first) + a live sitemap/robots/llms fetch. All
deterministic and offline-capable; DataForSEO/speed layer in separately.

Checks, ordered the way findings should be fixed (crawl/index → content →
links): sitemap health (limits, lastmod, coverage/orphans, robots reference),
robots.txt, llms.txt, metadata (title/meta presence·length·duplicates·noindex),
H1 (presence·uniqueness), canonical, cannibalization (via the TF-IDF index),
content length/depth, internal linking (orphans·inbound·click-depth·pillars),
structured data. Output: findings + `audit.md`.

Findings are {cat, sev(high|med|low), url, msg}; fixes are proposed, not applied
(human merge gate)."""
import datetime
import json
import re
from urllib.parse import urljoin, urlparse

from . import ingest
from .index import Index, load_corpus

DEF = {"title_min": 30, "title_max": 60, "meta_min": 70, "meta_max": 160,
       "thin_words": 300, "min_inbound": 3, "max_depth": 4}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}.*)?$")
CATS = ["sitemap", "crawl", "index", "meta", "headings", "canonical",
        "duplicate", "content", "links", "structured", "a11y"]


def _norm(base, href=""):
    try:
        p = urlparse(urljoin(base, href))
    except Exception:
        return None
    if p.scheme not in ("http", "https"):
        return None
    return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/") or f"{p.scheme}://{p.netloc}"


def _host(u):
    return urlparse(u).netloc.lower()


def _indexable(c):
    return c.get("status", 200) == 200 and "noindex" not in (c.get("robots") or "")


# ── individual checks (each appends to F) ───────────────────────────────────
def sitemap_health(cfg, corpus, F):
    entries = ingest.sitemap_entries(cfg["sitemap"]) if cfg.get("sitemap") else []
    locs = [e["loc"] for e in entries]
    info = {"entries": len(entries), "over_50k": len(entries) > 50000}
    if info["over_50k"]:
        F.append({"cat": "sitemap", "sev": "high", "url": cfg["sitemap"],
                  "msg": f"{len(entries)} URLs in one sitemap — split via a sitemap index (50k/file max)"})
    lastmods = [e["lastmod"] for e in entries if e["lastmod"]]
    bad = [e["loc"] for e in entries if e["lastmod"] and not ISO.match(e["lastmod"])]
    if bad:
        F.append({"cat": "sitemap", "sev": "med", "url": bad[0],
                  "msg": f"{len(bad)} lastmod values not ISO-8601 (Google ignores malformed dates)"})
    if lastmods and len(set(lastmods)) == 1 and len(lastmods) > 5:
        F.append({"cat": "sitemap", "sev": "med", "url": cfg["sitemap"],
                  "msg": "every lastmod is identical — Google will ignore lastmod site-wide; set it per-URL on real change"})
    # coverage: sitemap URLs whose fetched page is non-200 / noindex / canonicalises away
    by = {_norm(c.get("final_url") or c["url"]): c for c in corpus}
    bad_in_sm = []
    for e in entries:
        c = by.get(_norm(e["loc"]))
        if c and not _indexable(c):
            bad_in_sm.append(e["loc"])
    if bad_in_sm:
        F.append({"cat": "sitemap", "sev": "high", "url": bad_in_sm[0],
                  "msg": f"{len(bad_in_sm)} sitemap URLs are non-200 or noindex — sitemaps must list only indexable pages"})
    # indexable corpus pages missing from the sitemap
    sm_set = {_norm(l) for l in locs}
    missing = [c["url"] for c in corpus if _indexable(c) and _norm(c.get("final_url") or c["url"]) not in sm_set]
    if entries and missing:
        F.append({"cat": "sitemap", "sev": "med", "url": missing[0],
                  "msg": f"{len(missing)} indexable pages are not in the sitemap"})
    info["missing_from_sitemap"] = len(missing)
    info["non_indexable_in_sitemap"] = len(bad_in_sm)
    return info


AI_BOTS = ("gptbot", "oai-searchbot", "chatgpt-user", "claudebot", "anthropic-ai",
           "perplexitybot", "ccbot", "google-extended", "bytespider", "amazonbot",
           "applebot-extended", "meta-externalagent")


def _root_disallowers(txt):
    """User-agents (lowercased) that have `Disallow: /` — grouped correctly so a
    `Disallow: /` under `User-agent: GPTBot` isn't mistaken for a site-wide block."""
    here, blocked, saw_directive = [], set(), False
    for raw in txt.splitlines():
        l = raw.split("#")[0].strip()
        if not l or ":" not in l:
            continue
        k, v = [x.strip() for x in l.split(":", 1)]
        kl = k.lower()
        if kl == "user-agent":
            if saw_directive:            # a rule line closed the previous group
                here, saw_directive = [], False
            here.append(v.lower())
        elif kl in ("allow", "disallow"):   # BOTH close the group (Allow: / on * is not a block)
            saw_directive = True
            if kl == "disallow" and v == "/":
                blocked.update(here)
    return blocked


def robots_txt(cfg, F):
    site = (cfg.get("site") or "").rstrip("/")
    try:
        txt = ingest._get(site + "/robots.txt")
    except Exception:
        F.append({"cat": "crawl", "sev": "high", "url": site + "/robots.txt",
                  "msg": "robots.txt not reachable"})
        return {"exists": False}
    has_sm = "sitemap:" in txt.lower()
    if not has_sm:
        F.append({"cat": "crawl", "sev": "med", "url": site + "/robots.txt",
                  "msg": "robots.txt does not reference a Sitemap:"})
    blocked = _root_disallowers(txt)
    if "*" in blocked:
        F.append({"cat": "crawl", "sev": "high", "url": site + "/robots.txt",
                  "msg": "'Disallow: /' under User-agent: * — the whole site is blocked from crawling"})
    ai_blocked = sorted({b for b in blocked for a in AI_BOTS if a in b})
    if ai_blocked:
        F.append({"cat": "crawl", "sev": "low", "url": site + "/robots.txt",
                  "msg": f"robots.txt blocks AI crawlers ({', '.join(ai_blocked)}) via Disallow: / — "
                         f"intentional? this removes you from those AI answers (ChatGPT/Perplexity/…)"})
    return {"exists": True, "references_sitemap": has_sm, "ai_blocked": ai_blocked}


def js_render(corpus, F):
    csr = [c for c in corpus if c.get("csr")]
    if csr:
        F.append({"cat": "crawl", "sev": "high", "url": csr[0]["url"],
                  "msg": f"{len(csr)} pages look client-rendered (near-empty raw HTML) — enable JS "
                         f"rendering (render.enabled) for an accurate audit; otherwise Google/AI "
                         f"crawlers may see them nearly empty too"})


def llms_txt(cfg, F):
    site = (cfg.get("site") or "").rstrip("/")
    try:
        ingest._get(site + "/llms.txt")
        return {"exists": True}
    except Exception:
        F.append({"cat": "crawl", "sev": "low", "url": site + "/llms.txt",
                  "msg": "no llms.txt — optional; not a Google ranking factor but helps AI assistants "
                         "(Perplexity/Claude/ChatGPT) navigate the site. Offer to generate one."})
        return {"exists": False}


def metadata(corpus, F, t):
    seen_t, seen_d = {}, {}
    for c in corpus:
        if not _indexable(c):
            if c.get("status", 200) == 200 and "noindex" in (c.get("robots") or ""):
                pass  # noindex is a valid choice; only flagged if it's in the sitemap
            continue
        u, title, desc = c["url"], c.get("title", ""), c.get("description", "")
        if not title:
            F.append({"cat": "meta", "sev": "high", "url": u, "msg": "missing <title>"})
        elif len(title) > t["title_max"]:
            F.append({"cat": "meta", "sev": "low", "url": u, "msg": f"title {len(title)} chars (>{t['title_max']} — truncates in SERP)"})
        elif len(title) < t["title_min"]:
            F.append({"cat": "meta", "sev": "low", "url": u, "msg": f"title only {len(title)} chars (<{t['title_min']} — thin)"})
        if not desc:
            F.append({"cat": "meta", "sev": "med", "url": u, "msg": "missing meta description"})
        elif len(desc) > t["meta_max"]:
            F.append({"cat": "meta", "sev": "low", "url": u, "msg": f"meta description {len(desc)} chars (>{t['meta_max']})"})
        if title:
            seen_t.setdefault(title.lower(), []).append(u)
        if desc:
            seen_d.setdefault(desc.lower(), []).append(u)
    for title, us in seen_t.items():
        if len(us) > 1:
            F.append({"cat": "meta", "sev": "med", "url": us[0], "msg": f"duplicate title on {len(us)} pages: “{title[:60]}”"})
    for desc, us in seen_d.items():
        if len(us) > 1:
            F.append({"cat": "meta", "sev": "low", "url": us[0], "msg": f"duplicate meta description on {len(us)} pages"})


def freshness(corpus, F, year=None):
    """Stale year references — sitewide. A "… in 2024" title in 2026 depresses CTR and
    freshness signals even when the metadata says the page was updated yesterday.
    Rule: a title/H1 with a past year AND no current-or-newer year → per-page finding
    (retitle-able); pages whose newest year anywhere in the body is ≥2 years old
    aggregate into one refresh finding. (This was a real blind spot: `refresh <url>`
    checked it per-page, but no sitewide sweep ever ran — 44 stale titles slipped
    through a 400-page audit. Encoded per LEARNINGS #23.)"""
    import datetime
    year = year or datetime.date.today().year
    pat = re.compile(r"\b(20[123]\d)\b")
    stale_body = []
    for c in corpus:
        if not _indexable(c):
            continue
        head = (c.get("title") or "") + " " + " ".join(c.get("h1") or [])
        yrs = [int(y) for y in pat.findall(head)]
        if yrs and max(yrs) < year:
            F.append({"cat": "freshness", "sev": "med", "url": c["url"],
                      "msg": f"title/H1 says {max(yrs)} — it's {year}; retitle (stale years depress CTR + freshness)"})
            continue
        byrs = [int(y) for y in pat.findall(c.get("text", "") or "")]
        if byrs and max(byrs) < year - 1:
            stale_body.append(c["url"])
    if stale_body:
        F.append({"cat": "freshness", "sev": "low", "url": stale_body[0],
                  "msg": f"{len(stale_body)} pages whose newest year reference is ≤{year-2} — "
                         f"update stats/dates (`refresh <url>` per page)"})


def headings(corpus, F):
    seen = {}
    for c in corpus:
        if not _indexable(c):
            continue
        h1 = c.get("h1", [])
        if len(h1) == 0:
            F.append({"cat": "headings", "sev": "med", "url": c["url"], "msg": "no H1"})
        elif len(h1) > 1:
            F.append({"cat": "headings", "sev": "low", "url": c["url"], "msg": f"{len(h1)} H1 tags (use one)"})
        if h1:
            seen.setdefault(h1[0].lower(), []).append(c["url"])
    for h, us in seen.items():
        if len(us) > 1:
            F.append({"cat": "headings", "sev": "low", "url": us[0], "msg": f"duplicate H1 on {len(us)} pages: “{h[:60]}”"})


def canonicals(corpus, F):
    for c in corpus:
        if not _indexable(c):
            continue
        can = c.get("canonical", "")
        if not can:
            F.append({"cat": "canonical", "sev": "low", "url": c["url"], "msg": "no canonical tag"})
        elif _norm(can) and _norm(c.get("final_url") or c["url"]) and _norm(can) != _norm(c.get("final_url") or c["url"]):
            F.append({"cat": "canonical", "sev": "med", "url": c["url"], "msg": f"canonical points elsewhere → {can} (this page may be de-indexed)"})


def content_depth(corpus, F, t):
    for c in corpus:
        if not _indexable(c):
            continue
        w = c.get("words", 0)
        if w < t["thin_words"] // 2:
            F.append({"cat": "content", "sev": "med", "url": c["url"], "msg": f"very thin — {w} words"})
        elif w < t["thin_words"]:
            F.append({"cat": "content", "sev": "low", "url": c["url"], "msg": f"thin — {w} words (<{t['thin_words']})"})


def internal_links(corpus, cfg, F, t):
    site = (cfg.get("site") or "").rstrip("/")
    host = _host(site) if site else None
    ids = {}
    for c in corpus:
        ids[_norm(c.get("final_url") or c["url"])] = c
    inbound = {k: 0 for k in ids}
    adj = {k: set() for k in ids}
    for c in corpus:
        src = _norm(c.get("final_url") or c["url"])
        for href in c.get("links", []):
            tgt = _norm(c["url"], href)
            if tgt and tgt in ids and tgt != src and (not host or _host(tgt) == host) and tgt not in adj[src]:
                adj[src].add(tgt)
                inbound[tgt] += 1
    root = _norm(site) if site and _norm(site) in ids else (min(ids, key=lambda k: len(k)) if ids else None)
    depth = {}
    if root:
        depth[root] = 0
        q = [root]
        while q:
            n = q.pop(0)
            for m in adj[n]:
                if m not in depth:
                    depth[m] = depth[n] + 1
                    q.append(m)
    orphans = [u for u, n in inbound.items() if n == 0 and u != root and _indexable(ids[u])]
    if orphans:
        F.append({"cat": "links", "sev": "high", "url": orphans[0],
                  "msg": f"{len(orphans)} orphan pages (no internal links point to them), e.g. "
                         + ", ".join(u.rsplit('/', 1)[-1] or u for u in orphans[:3])})
    under = [u for u, n in inbound.items() if 0 < n < t["min_inbound"] and _indexable(ids[u])]
    if under:
        F.append({"cat": "links", "sev": "low", "url": under[0], "msg": f"{len(under)} pages have <{t['min_inbound']} inbound internal links"})
    deep = [u for u, d in depth.items() if d > t["max_depth"] and _indexable(ids[u])]
    if deep:
        F.append({"cat": "links", "sev": "med", "url": deep[0], "msg": f"{len(deep)} pages are >{t['max_depth']} clicks from the root"})
    return {"orphans": len(orphans), "under_linked": len(under), "too_deep": len(deep),
            "unreachable": sum(1 for u in ids if u not in depth)}


def redirects_broken(corpus, F):
    by = {_norm(c.get("final_url") or c["url"]): c for c in corpus}
    redirs = [c for c in corpus if c.get("final_url")
              and _norm(c["url"]) != _norm(c.get("final_url")) and c.get("status") == 200]
    if redirs:
        F.append({"cat": "crawl", "sev": "med", "url": redirs[0]["url"],
                  "msg": f"{len(redirs)} sitemap/crawled URLs redirect — point internal links + the "
                         f"sitemap at the final URL to save crawl budget and link equity"})
    broken = []
    for c in corpus:
        for href in c.get("links", []):
            tgt = _norm(c["url"], href)
            tc = by.get(tgt)
            if tc and tc.get("status", 200) >= 400:
                broken.append((c["url"], tgt))
    if broken:
        F.append({"cat": "links", "sev": "high", "url": broken[0][0],
                  "msg": f"{len(broken)} internal links point to broken (4xx/5xx) pages"})


def hreflang_audit(corpus, F):
    withhl = [c for c in corpus if c.get("hreflang")]
    no_default = [c for c in withhl if "x-default" not in [h["lang"] for h in c["hreflang"]]]
    if no_default:
        F.append({"cat": "index", "sev": "low", "url": no_default[0]["url"],
                  "msg": f"{len(no_default)} pages set hreflang without an x-default (add one for unmatched locales)"})


def cannibalization(F, corpus_path):
    try:
        idx = Index(load_corpus(corpus_path))
    except Exception:
        return
    for g in idx.clusters(0.55, space="title")[:12]:
        F.append({"cat": "duplicate", "sev": "med", "url": g["members"][0],
                  "msg": "cannibalization cluster: " + " · ".join(m.rsplit("/", 1)[-1] for m in g["members"])})


def structured(corpus, F):
    idx = [c for c in corpus if _indexable(c)]
    no = [c for c in idx if not c.get("jsonld")]
    if idx and len(no) > len(idx) * 0.5:
        F.append({"cat": "structured", "sev": "low", "url": no[0]["url"],
                  "msg": f"{len(no)}/{len(idx)} indexable pages have no JSON-LD structured data"})


def _heading_skip(levels):
    prev = 0
    for lv in levels:
        if prev and lv > prev + 1:
            return True
        prev = lv
    return False


def accessibility(corpus, F):
    """WCAG-adjacent checks Google's parser also values (alt text, lang, heading order).
    Not a direct ranking factor, but the structure it rewards — and image SEO."""
    idx = [c for c in corpus if _indexable(c)]
    alt = [c for c in idx if c.get("img_total", 0) and c.get("img_alt", 0) < c["img_total"]]
    if alt:
        missing = sum(c["img_total"] - c.get("img_alt", 0) for c in alt)
        F.append({"cat": "a11y", "sev": "low", "url": alt[0]["url"],
                  "msg": f"{missing} images across {len(alt)} pages missing alt text (WCAG A + image SEO)"})
    no_lang = [c for c in idx if not c.get("lang")]
    if no_lang:
        F.append({"cat": "a11y", "sev": "low", "url": no_lang[0]["url"],
                  "msg": f"{len(no_lang)} pages missing <html lang> (accessibility + Google language processing)"})
    skips = [c for c in idx if _heading_skip(c.get("heading_levels", []))]
    if skips:
        F.append({"cat": "a11y", "sev": "low", "url": skips[0]["url"],
                  "msg": f"{len(skips)} pages skip heading levels (e.g. H2→H4) — confuses screen readers + parsers"})


# ── driver + render ─────────────────────────────────────────────────────────
def report(cfg, corpus_path="corpus.json"):
    t = {**DEF, **cfg.get("audit", {})}
    corpus = load_corpus(corpus_path)
    F = []
    sm = sitemap_health(cfg, corpus, F)
    robots_txt(cfg, F)
    llms_txt(cfg, F)
    js_render(corpus, F)
    metadata(corpus, F, t)
    freshness(corpus, F)
    headings(corpus, F)
    canonicals(corpus, F)
    content_depth(corpus, F, t)
    redirects_broken(corpus, F)
    hreflang_audit(corpus, F)
    cannibalization(F, corpus_path)
    link_stats = internal_links(corpus, cfg, F, t)
    structured(corpus, F)
    accessibility(corpus, F)
    counts = {s: sum(1 for f in F if f["sev"] == s) for s in ("high", "med", "low")}
    return {"pages": len(corpus), "sitemap": sm, "links": link_stats,
            "findings": F, "counts": counts}


def render_md(cfg, a):
    order = {"high": 0, "med": 1, "low": 2}
    L = [f"# Site Doctor — {cfg.get('site','site')} — {datetime.date.today().isoformat()}",
         f"{a['pages']} pages · **{a['counts']['high']} high · {a['counts']['med']} medium · "
         f"{a['counts']['low']} low**", "",
         f"Sitemap: {a['sitemap'].get('entries','?')} URLs · orphans: {a['links'].get('orphans','?')} · "
         f"unreachable: {a['links'].get('unreachable','?')}", ""]
    for cat in CATS:
        fs = sorted([f for f in a["findings"] if f["cat"] == cat], key=lambda f: order[f["sev"]])
        if not fs:
            continue
        L.append(f"## {cat} ({len(fs)})")
        for f in fs[:25]:
            tag = {"high": "🔴", "med": "🟠", "low": "🟡"}[f["sev"]]
            L.append(f"- {tag} {f['msg']} — {f['url'].rsplit('/', 1)[-1] or f['url']}")
        if len(fs) > 25:
            L.append(f"- …and {len(fs) - 25} more")
        L.append("")
    if not a["findings"]:
        L.append("_No issues found — clean bill of health._")
    L.append("_Fixes are proposed, not applied. Review, then apply as PRs (human merge gate)._")
    return "\n".join(L)


def llms_txt_template(cfg, corpus_path="corpus.json"):
    """Generate an llms.txt from the corpus (top pages by inbound links)."""
    brand = cfg.get("brand", {}).get("name", "Site")
    L = [f"# {brand}", "", f"> {cfg.get('site','')}", "", "## Pages"]
    try:
        corpus = load_corpus(corpus_path)
    except Exception:
        corpus = []
    for c in corpus[:40]:
        if _indexable(c) and c.get("title"):
            L.append(f"- [{c['title']}]({c.get('final_url') or c['url']})")
    return "\n".join(L) + "\n"
