"""Layer 1 — Observe (goal #6). Backlink profile + competitor link-gap via the
DataForSEO Backlinks API. Degrades to empty without creds. The link-gap is the
outreach queue: referring domains that point at competitors but not at us."""
from . import providers


def _host(url):
    return (url or "").replace("https://", "").replace("http://", "").rstrip("/").split("/")[0]


def profile(cfg):
    site = _host(cfg.get("site"))
    return {"target": site,
            "summary": providers.backlinks_summary(site),
            "referring_domains": providers.referring_domains(site)}


SPAM_TLDS = (".xyz", ".top", ".loan", ".work", ".click", ".gq", ".tk", ".ml", ".cf",
             ".ga", ".buzz", ".bid", ".stream", ".download", ".racing", ".party", ".review")


def toxicity(cfg, limit=30):
    """Conservative flag of suspicious referring domains (spammy TLDs).

    IMPORTANT (2026 reality): disavow is rarely necessary — Google's SpamBrain
    ignores spam links automatically, and low authority is NOT toxicity. Only
    disavow after a manual action in Search Console or a documented negative-SEO
    event. This surfaces candidates for review, not a disavow-everything list."""
    site = _host(cfg.get("site"))
    domains = providers.referring_domains(site, limit=500)
    suspect = [d for d in domains if any((d.get("domain") or "").endswith(t) for t in SPAM_TLDS)]
    suspect.sort(key=lambda d: (d.get("rank") or 0))
    return {"note": "Disavow is rarely needed in 2026 (SpamBrain auto-ignores spam; low authority ≠ "
                    "toxic). Only act on a manual action or documented negative SEO.",
            "referring_domains": len(domains), "suspect_count": len(suspect),
            "suspect": suspect[:limit]}


def link_gap(cfg, limit=50):
    """Domains linking to competitors but not to us, ranked by how many
    competitors they link (consensus) then domain authority. Outreach targets."""
    site = _host(cfg.get("site"))
    ours = {d.get("domain") for d in providers.referring_domains(site)}
    gaps = {}
    for comp in cfg.get("competitors", []):
        c = _host(comp)
        for d in providers.referring_domains(c):
            dom = d.get("domain")
            if not dom or dom in ours or dom == c:
                continue
            g = gaps.setdefault(dom, {"domain": dom, "links_to": [], "rank": d.get("rank")})
            g["links_to"].append(c)
            g["rank"] = max(g["rank"] or 0, d.get("rank") or 0)
    out = sorted(gaps.values(), key=lambda g: (-len(g["links_to"]), -(g["rank"] or 0)))
    return out[:limit]
