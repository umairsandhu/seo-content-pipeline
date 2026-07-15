"""Structured-data (JSON-LD) generation + validation. The Site Doctor detects
presence; this GENERATES ready-to-embed schema.org JSON-LD (BlogPosting,
Organization, BreadcrumbList, FAQPage-from-PAA) from page/site data, and
VALIDATES existing JSON-LD for the required fields per @type.

Deterministic + offline (works off corpus.json). Output is a `<script
type="application/ld+json">` block to paste into <head> — proposed, not applied."""
import json
import re
from urllib.parse import urlparse

from .index import load_corpus

REQUIRED = {  # minimum fields Google wants per common type
    "BlogPosting": ["headline", "datePublished"], "Article": ["headline", "datePublished"],
    "Organization": ["name", "url"], "Product": ["name"],
    "BreadcrumbList": ["itemListElement"], "FAQPage": ["mainEntity"],
}


def organization(cfg):
    b = cfg.get("brand", {})
    return {"@context": "https://schema.org", "@type": "Organization",
            "name": b.get("name", "Site"), "url": cfg.get("site", "")}


def breadcrumb(url):
    parts = [p for p in urlparse(url).path.split("/") if p]
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    items, acc = [], base
    for i, p in enumerate(["home"] + parts, 1):
        acc = base if p == "home" else acc + "/" + p
        items.append({"@type": "ListItem", "position": i,
                      "name": p.replace("-", " ").title(), "item": acc})
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}


def blogposting(cfg, rec):
    url = rec.get("final_url") or rec["url"]
    d = {"@context": "https://schema.org", "@type": "BlogPosting",
         "headline": (rec.get("h1") or [rec.get("title", "")])[0][:110],
         "description": rec.get("description", ""),
         "mainEntityOfPage": url,
         "author": {"@type": "Organization", "name": cfg.get("brand", {}).get("name", "Site")},
         "publisher": organization(cfg)}
    return d


def faqpage(paa):
    if not paa:
        return None
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": ""}} for q in paa[:8]]}


def _script(obj):
    return '<script type="application/ld+json">\n' + json.dumps(obj, indent=2, ensure_ascii=False) + "\n</script>"


def generate(cfg, url, corpus_path="corpus.json"):
    """JSON-LD for one page (BlogPosting + BreadcrumbList) + site Organization."""
    rec = None
    try:
        for c in load_corpus(corpus_path):
            if url in (c.get("url"), c.get("final_url")):
                rec = c
                break
    except Exception:
        pass
    blocks = []
    if rec:
        blocks.append(blogposting(cfg, rec))
        blocks.append(breadcrumb(rec.get("final_url") or rec["url"]))
    else:
        blocks.append(organization(cfg))
    return "\n".join(_script(b) for b in blocks)


def validate(jsonld_str):
    """Parse + check required fields per @type. Returns list of issues."""
    issues = []
    for m in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', jsonld_str, re.S | re.I) or [jsonld_str]:
        try:
            data = json.loads(m)
        except Exception as e:
            issues.append(f"invalid JSON: {e}")
            continue
        for obj in (data if isinstance(data, list) else [data]):
            t = obj.get("@type")
            for field in REQUIRED.get(t, []):
                if not obj.get(field):
                    issues.append(f"{t}: missing required '{field}'")
    return issues


def missing(cfg, corpus_path="corpus.json"):
    """Indexable pages with no JSON-LD — candidates for `generate`."""
    try:
        corpus = load_corpus(corpus_path)
    except Exception:
        return []
    return [c["url"] for c in corpus
            if c.get("status", 200) == 200 and "noindex" not in (c.get("robots") or "") and not c.get("jsonld")]
