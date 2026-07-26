"""Entity / knowledge-graph builder. In 2026, entity clarity gates inclusion in AI
Overviews, AI Mode and Gemini: engines resolve your brand to a node in a knowledge
graph via `sameAs` triangulation, a Wikidata QID, and a consistent Organization
entity. The highest-ROI fixes here are cheap.

This resolves the brand against **Wikidata (free, no key)**, reads the site's existing
`Organization` schema (`sameAs`, logo), scores how many authoritative profiles it
triangulates to, generates a complete `Organization` JSON-LD block, and flags a
brand-salience problem (brand barely present on its own home page). Site-agnostic —
brand + site come from config."""
import json
import re
import urllib.parse
import urllib.request
from urllib.parse import urlparse

from . import providers

# Authoritative profiles engines use to triangulate an org entity.
_SAMEAS_HINTS = ["linkedin.com/company", "crunchbase.com/organization", "x.com", "twitter.com",
                 "github.com", "wikipedia.org", "wikidata.org", "facebook.com", "youtube.com",
                 "g2.com", "capterra.com"]


def _brand(cfg):
    return (cfg.get("brand", {}) or {}).get("name") or urlparse(cfg.get("site", "")).netloc.replace("www.", "")


def wikidata(name):
    """Resolve a name to a Wikidata QID (free API, no key). Returns best match or None."""
    url = ("https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=en&limit=5"
           "&search=" + urllib.parse.quote(name))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "seo-agent"}), timeout=20) as r:
            d = json.load(r)
    except Exception:
        return None
    for it in d.get("search", []):
        return {"qid": it.get("id"), "label": it.get("label"), "description": it.get("description"),
                "url": "https://www.wikidata.org/wiki/" + it.get("id", "")}
    return None


def _home_org(cfg):
    """Read the Organization node from the homepage's JSON-LD (sameAs, logo, name)."""
    site = cfg.get("site", "")
    try:
        with urllib.request.urlopen(urllib.request.Request(site, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
            doc = r.read().decode("utf-8", "ignore")
    except Exception:
        return {}, ""
    org = {}
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', doc, re.I | re.S):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:
            continue
        stack = [data]
        while stack:
            n = stack.pop()
            if isinstance(n, list):
                stack.extend(n)
            elif isinstance(n, dict):
                if isinstance(n.get("@graph"), list):
                    stack.extend(n["@graph"])
                t = n.get("@type", "")
                if "Organization" in (t if isinstance(t, str) else " ".join(t or [])):
                    org = n
    return org, doc


def report(cfg):
    brand, site = _brand(cfg), cfg.get("site", "")
    org, doc = _home_org(cfg)
    same = org.get("sameAs") or []
    if isinstance(same, str):
        same = [same]
    have = {h for h in _SAMEAS_HINTS if any(h in s for s in same)}
    missing = [h for h in _SAMEAS_HINTS if h not in have]
    wd = wikidata(brand)
    # salience proxy: brand mentions on the home page relative to length
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<script[\s\S]*?</script>", " ", doc))
    mentions = len(re.findall(re.escape(brand), text, re.I)) if brand else 0
    words = len(text.split()) or 1
    salience = round(min(1.0, mentions / max(words / 400, 1)), 2)
    generated = _org_jsonld(cfg, brand, org, same, wd)
    return {"brand": brand, "site": site, "wikidata": wd, "sameAs_present": sorted(have),
            "sameAs_missing": missing, "salience": salience, "mentions": mentions,
            "has_org_schema": bool(org), "generated": generated}


def _org_jsonld(cfg, brand, org, same, wd):
    block = {"@context": "https://schema.org", "@type": "Organization", "name": brand,
             "url": cfg.get("site", ""),
             "sameAs": sorted(set(same) | ({wd["url"]} if wd else set()))}
    if org.get("logo"):
        block["logo"] = org["logo"]
    if org.get("description"):
        block["description"] = org["description"]
    return block


def render_md(cfg, r):
    L = [f"# Entity / knowledge-graph — {r['brand']}", ""]
    if r["wikidata"]:
        L.append(f"- ✅ Wikidata: **{r['wikidata']['qid']}** — {r['wikidata']['url']} "
                 f"({r['wikidata'].get('description','')})")
    else:
        L.append("- 🔴 **No Wikidata entity** — the single highest-impact entity fix. Create one so AI "
                 "engines can resolve the brand to a knowledge-graph node.")
    L.append(f"- Organization schema on homepage: {'✅ present' if r['has_org_schema'] else '🔴 missing'}")
    L.append(f"- `sameAs` triangulation: {len(r['sameAs_present'])} present"
             + (f" ({', '.join(p.split('.')[0].split('/')[0] for p in r['sameAs_present'])})" if r['sameAs_present'] else ""))
    if r["sameAs_missing"]:
        L.append(f"- 🟡 add authoritative `sameAs` profiles: {', '.join(r['sameAs_missing'][:8])}")
    flag = "🔴 low — restructure so the brand is the clear entity" if r["salience"] < 0.25 else "✅"
    L.append(f"- brand salience on homepage: **{r['salience']}** {flag} ({r['mentions']} mentions)")
    L += ["", "## Generated Organization JSON-LD (paste in <head>)", "```json",
          json.dumps(r["generated"], indent=2), "```"]
    return "\n".join(L)
