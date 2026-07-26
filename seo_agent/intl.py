"""International SEO — hreflang validation. Misconfigured hreflang is one of the most
common enterprise-SEO defects: missing return tags, no x-default, self-reference
gaps, and locale clusters that don't point back at each other. Engines then serve the
wrong-language page or ignore the cluster.

Deterministic, offline (corpus.json stores each page's `hreflang` list). Validates
reciprocity, x-default, and self-reference; maps locale clusters. Degrades to
"single-locale site — nothing to validate" when no hreflang exists anywhere.
Site-agnostic."""
from urllib.parse import urlparse

from .index import load_corpus


def _norm(u):
    return (u or "").split("#")[0].rstrip("/")


def report(cfg, corpus_path="corpus.json"):
    corpus = load_corpus(corpus_path)
    by_url = {_norm(c["url"]): c for c in corpus}
    tagged = [c for c in corpus if c.get("hreflang")]
    if not tagged:
        return {"has_hreflang": False, "pages_tagged": 0}
    issues = []
    langs = set()
    clusters = 0
    for c in tagged:
        src = _norm(c["url"])
        entries = c["hreflang"]
        alts = {e["lang"]: _norm(e["href"]) for e in entries if e.get("href")}
        for lg in alts:
            langs.add(lg)
        clusters += 1
        # self-reference
        if src not in alts.values():
            issues.append({"url": c["url"], "issue": "missing self-referencing hreflang"})
        # x-default
        if "x-default" not in alts:
            issues.append({"url": c["url"], "issue": "no x-default"})
        # return-tag reciprocity (only checkable for URLs in the corpus)
        for lg, href in alts.items():
            tgt = by_url.get(href)
            if tgt is not None:
                back = {e.get("href") and _norm(e["href"]) for e in (tgt.get("hreflang") or [])}
                if src not in back:
                    issues.append({"url": c["url"], "issue": f"no return tag from {href} ({lg})"})
    return {"has_hreflang": True, "pages_tagged": len(tagged), "languages": sorted(langs),
            "clusters": clusters, "issues": issues}


def render_md(cfg, r):
    if not r.get("has_hreflang"):
        return (f"# International (hreflang) — {cfg.get('site','site')}\n\n"
                "_No hreflang found — single-locale site, nothing to validate. "
                "Add hreflang only if you publish per-locale versions._")
    L = [f"# International (hreflang) — {cfg.get('site','site')}",
         f"{r['pages_tagged']} pages tagged · languages: {', '.join(r['languages'])} · "
         f"{len(r['issues'])} issues", ""]
    if not r["issues"]:
        L.append("✅ hreflang looks healthy (self-ref, x-default, and return tags present).")
    else:
        by = {}
        for it in r["issues"]:
            by.setdefault(it["issue"].split(" from ")[0], 0)
            by[it["issue"].split(" from ")[0]] += 1
        L.append("## Issue counts")
        for k, n in sorted(by.items(), key=lambda kv: -kv[1]):
            L.append(f"- {k}: {n}")
        L += ["", "## Examples"]
        for it in r["issues"][:12]:
            L.append(f"- {it['url']} — {it['issue']}")
    return "\n".join(L)
