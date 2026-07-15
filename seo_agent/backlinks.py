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
