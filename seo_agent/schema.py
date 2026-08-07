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

REQUIRED = {  # minimum fields Google wants per common type (rich-results eligibility)
    "BlogPosting": ["headline", "datePublished"], "Article": ["headline", "datePublished"],
    "NewsArticle": ["headline", "datePublished"],
    "Organization": ["name", "url"], "BreadcrumbList": ["itemListElement"],
    "FAQPage": ["mainEntity"], "QAPage": ["mainEntity"],
    "Product": ["name", "offers"], "Offer": ["price", "priceCurrency"],
    "Review": ["itemReviewed", "reviewRating"], "AggregateRating": ["ratingValue", "ratingCount"],
    "HowTo": ["name", "step"], "Event": ["name", "startDate", "location"],
    "LocalBusiness": ["name", "address"], "VideoObject": ["name", "thumbnailUrl", "uploadDate"],
    "Recipe": ["name", "recipeIngredient", "recipeInstructions"],
    "JobPosting": ["title", "datePosted", "hiringOrganization"],
    "Course": ["name", "provider"], "SoftwareApplication": ["name", "offers"],
}

# What each page KIND should carry — powers sitewide coverage gaps in `coverage()`.
_EXPECT = {"blog": ("Article", "BlogPosting", "NewsArticle"), "post": ("Article", "BlogPosting"),
           "product": ("Product",), "shop": ("Product",), "store": ("Product",),
           "event": ("Event",), "video": ("VideoObject",), "job": ("JobPosting",),
           "careers": ("JobPosting",), "location": ("LocalBusiness",), "contact": ("LocalBusiness",)}


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


def howto(name, steps):
    """HowTo from (name, [step texts]) — feeds AI answer extraction directly."""
    return {"@context": "https://schema.org", "@type": "HowTo", "name": name,
            "step": [{"@type": "HowToStep", "position": i, "text": s}
                     for i, s in enumerate(steps, 1)]}


def product(cfg, rec, price=None, currency="USD"):
    d = {"@context": "https://schema.org", "@type": "Product",
         "name": (rec.get("h1") or [rec.get("title", "")])[0][:110],
         "description": rec.get("description", ""),
         "brand": {"@type": "Brand", "name": cfg.get("brand", {}).get("name", "Site")}}
    if price is not None:
        d["offers"] = {"@type": "Offer", "price": str(price), "priceCurrency": currency,
                       "availability": "https://schema.org/InStock"}
    return d


def localbusiness(cfg, address=None, telephone=None):
    b = cfg.get("brand", {})
    d = {"@context": "https://schema.org", "@type": "LocalBusiness",
         "name": b.get("name", "Site"), "url": cfg.get("site", "")}
    if address:
        d["address"] = {"@type": "PostalAddress", **address} if isinstance(address, dict) else address
    if telephone:
        d["telephone"] = telephone
    return d


def videoobject(name, thumbnail, upload_date, description=""):
    return {"@context": "https://schema.org", "@type": "VideoObject", "name": name,
            "thumbnailUrl": thumbnail, "uploadDate": upload_date, "description": description}


def event(name, start_date, location, url=""):
    return {"@context": "https://schema.org", "@type": "Event", "name": name,
            "startDate": start_date,
            "location": {"@type": "Place", "name": location} if isinstance(location, str) else location,
            "url": url}


def qapage(question, answer):
    """QAPage (one Q, one accepted answer) — the extraction-friendly cousin of FAQPage."""
    return {"@context": "https://schema.org", "@type": "QAPage",
            "mainEntity": {"@type": "Question", "name": question, "answerCount": 1,
                           "acceptedAnswer": {"@type": "Answer", "text": answer}}}


GENERATORS = {"HowTo": howto, "Product": product, "LocalBusiness": localbusiness,
              "VideoObject": videoobject, "Event": event, "QAPage": qapage,
              "FAQPage": faqpage, "BlogPosting": blogposting,
              "Organization": organization, "BreadcrumbList": breadcrumb}


def coverage(cfg, corpus_path="corpus.json"):
    """Sitewide structured-data coverage: which @types are present where, and which
    page sections are missing the type their content calls for."""
    try:
        corpus = load_corpus(corpus_path)
    except Exception:
        return {"types": {}, "gaps": [], "typed_pages": 0, "pages": 0}
    types, gaps = {}, []
    idx = [c for c in corpus if c.get("status", 200) == 200 and "noindex" not in (c.get("robots") or "")]
    for c in idx:
        for t in c.get("jsonld_types", []) or []:
            types[t] = types.get(t, 0) + 1
    by_sec = {}
    for c in idx:
        path = urlparse(c["url"]).path.strip("/")
        sec = (path.split("/")[0] if path else "").lower()
        by_sec.setdefault(sec, []).append(c)
    for sec, pages in by_sec.items():
        expected = next((v for k, v in _EXPECT.items() if k in sec), None)
        if not expected:
            continue
        missing_n = sum(1 for c in pages
                        if not any(t in (c.get("jsonld_types") or []) for t in expected))
        if missing_n:
            gaps.append({"section": f"/{sec}/", "expected": expected[0], "pages_missing": missing_n,
                         "of": len(pages)})
    return {"pages": len(idx), "typed_pages": sum(1 for c in idx if c.get("jsonld_types")),
            "types": dict(sorted(types.items(), key=lambda kv: -kv[1])),
            "gaps": sorted(gaps, key=lambda g: -g["pages_missing"])}


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
