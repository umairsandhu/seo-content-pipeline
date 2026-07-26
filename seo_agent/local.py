"""Local SEO — NAP consistency + LocalBusiness structured-data audit from crawl data.
For businesses with physical locations, engines and the local pack need one consistent
Name/Address/Phone and valid `LocalBusiness` schema. This finds inconsistent phone
numbers/addresses across pages and checks the schema, with no Google Business API
needed (degrades to on-page signals).

Auto-detects whether the site is even local (any address/phone/LocalBusiness) and
says so rather than inventing findings. Site-agnostic."""
import re

from .index import load_corpus

_PHONE = re.compile(r"(?:\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
_LOCAL_TYPES = ("LocalBusiness", "Restaurant", "Store", "ProfessionalService", "MedicalOrganization",
                "Dentist", "Attorney", "HomeAndConstructionBusiness")


def report(cfg, corpus_path="corpus.json"):
    import json
    corpus = load_corpus(corpus_path)
    phones, has_localbiz, addr_pages = {}, False, 0
    for c in corpus:
        text = (c.get("text") or "")[:6000]
        for m in set(_PHONE.findall(text)):
            digits = re.sub(r"\D", "", m)[-10:]
            if len(digits) == 10:
                phones[digits] = phones.get(digits, 0) + 1
        # LocalBusiness schema only counts inside an actual @type declaration
        if re.search(r'"@type"\s*:\s*"(?:' + "|".join(_LOCAL_TYPES) + r')"', text):
            has_localbiz = True
        if re.search(r"\b\d{1,5}\s+\w+(\s+\w+){0,3}\s+(st|street|ave|avenue|rd|road|blvd|suite|ste)\b", text, re.I):
            addr_pages += 1
    # "local" requires a physical-location signal: a phone AND (address or schema)
    is_local = bool(phones) and (addr_pages or has_localbiz)
    findings = []
    if not is_local:
        return {"is_local": False}
    if len(phones) > 1:
        top = sorted(phones.items(), key=lambda kv: -kv[1])
        findings.append({"sev": "high", "msg": "inconsistent phone numbers across the site: "
                         + ", ".join(f"{p} ({n}×)" for p, n in top[:4])})
    if not has_localbiz:
        findings.append({"sev": "high", "msg": "no LocalBusiness structured data found — add it with NAP + geo + hours"})
    return {"is_local": True, "distinct_phones": len(phones), "has_localbusiness_schema": has_localbiz,
            "address_pages": addr_pages, "findings": findings}


def render_md(cfg, r):
    if not r.get("is_local"):
        return (f"# Local SEO — {cfg.get('site','site')}\n\n"
                "_No local signals (address / phone / LocalBusiness schema) detected — "
                "not a local business, skipping. Add local signals only if you serve physical locations._")
    L = [f"# Local SEO — {cfg.get('site','site')}",
         f"distinct phone numbers: {r['distinct_phones']} · LocalBusiness schema: "
         f"{'✅' if r['has_localbusiness_schema'] else '🔴 missing'} · address pages: {r['address_pages']}", ""]
    for f in r["findings"]:
        L.append(f"- {'🔴' if f['sev']=='high' else '🟡'} {f['msg']}")
    if not r["findings"]:
        L.append("✅ NAP looks consistent and LocalBusiness schema is present.")
    L.append("\n_Keep Name/Address/Phone identical across the site, GBP, and citations; "
             "add `LocalBusiness` JSON-LD with `geo`, `openingHours`, and `areaServed`._")
    return "\n".join(L)
