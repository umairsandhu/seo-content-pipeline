"""Link acquisition — moves beyond backlink *analysis* into *prospecting*. Digital PR
is 2026's highest-leverage link tactic, but analysis alone never earns a link. This
mines referring domains that link to competitors but not to you (the backlink gap),
ranks them, and returns an outreach packet (angle + personalized pitch) the agent
writes. Snapshots prospects so status (contacted / replied / won) is tracked run to
run.

Needs DataForSEO (or an alt) for competitor referring domains; degrades to an
agent-mode strategy packet when absent. Site-agnostic."""
from urllib.parse import urlparse

from . import history, providers, store


def _dom(u):
    return urlparse(u if "//" in u else "//" + u).netloc.replace("www.", "").lower() or u


def gap(cfg, limit=60):
    """Referring domains linking to competitors but not to the target site."""
    site = _dom(cfg.get("site", ""))
    competitors = cfg.get("competitors", [])
    if not providers._dfs_auth() or not competitors:
        return None
    own = {_dom(d.get("domain") or d.get("referring_domain") or "")
           for d in (providers.referring_domains(site, limit=300) or [])}
    prospects = {}
    for c in competitors:
        for d in (providers.referring_domains(_dom(c), limit=200) or []):
            dom = _dom(d.get("domain") or d.get("referring_domain") or "")
            if not dom or dom in own or dom == site:
                continue
            p = prospects.setdefault(dom, {"domain": dom, "links_to": [], "rank": d.get("rank") or d.get("domain_rank") or 0})
            if c not in p["links_to"]:
                p["links_to"].append(c)
            p["rank"] = max(p["rank"], d.get("rank") or d.get("domain_rank") or 0)
    rows = sorted(prospects.values(), key=lambda p: (-len(p["links_to"]), -p["rank"]))[:limit]
    return rows


def run(cfg, limit=60):
    rows = gap(cfg, limit)
    if rows is None:
        return {"mode": "agent", "packet": _strategy_packet(cfg)}
    history.snapshot(cfg, "prospects", rows)
    store.record(cfg, "prospects", [{"domain": r["domain"], "n": len(r["links_to"])} for r in rows],
                 key_field="domain", value_fields=["n"])
    return {"mode": "live", "prospects": rows, "packet": _outreach_packet(cfg, rows)}


def _outreach_packet(cfg, rows):
    brand = (cfg.get("brand", {}) or {}).get("name", "the brand")
    top = "\n".join(f"- **{r['domain']}** (links to {', '.join(r['links_to'])}; DR {r['rank']})"
                    for r in rows[:25]) or "- (none found)"
    return (f"# Link-acquisition prospects — {brand}\n\n"
            f"These domains link to competitors but not to {cfg.get('site','')}. For each of the top "
            f"prospects, write a personalized pitch: identify WHY they linked to the competitor (roundup, "
            f"resource page, stat citation, integration), then offer a specific, better reason to add "
            f"{brand} — a unique data point, a free tool, an integration, or a superior resource.\n\n"
            f"## Prospects (highest overlap first)\n{top}\n\n"
            f"## Deliverable\nFor the top 10: prospect, likely link type, a one-line angle, and a 3–4 "
            f"sentence outreach email. Track status (contacted/replied/won) so re-runs diff progress.")


def _strategy_packet(cfg):
    brand = (cfg.get("brand", {}) or {}).get("name", "the brand")
    return (f"# Link-acquisition strategy — {brand}\n\n"
            f"No competitor backlink data (set DataForSEO / an alt, and `competitors` in config). "
            f"Meanwhile, the durable 2026 tactic is **digital PR**: turn the site's proprietary data into "
            f"a linkable asset (an industry stat study, a benchmark, a free tool), then pitch journalists "
            f"and resource-page owners. Draft 3 data-hook angles from what this site uniquely knows.")


def render_md(cfg, r):
    return r.get("packet", "_no prospects_")
