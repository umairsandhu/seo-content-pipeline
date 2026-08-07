"""Site change tracking — the ContentKing / Screaming-Frog-'compare crawls' killer
feature, local-first. Every `ingest` rotates the previous crawl to corpus.prev.json;
this diffs the two and reports what changed on YOUR OWN site between crawls:

  pages added / removed · status flips · noindex appearing (the classic silent
  disaster) · canonical changes · title/meta rewrites · H1 changes · schema types
  dropped · content shrinking >30% · viewport lost

Severity encodes blast radius: indexability regressions are high, meta/content
drift is medium, cosmetic is low. High-sev changes surface as `anomaly` alerts, so
with the daily cron this IS 24/7 monitoring — no SaaS watching required. Also the
deploy-safety net: run `ingest && sitediff` after every site release. Stdlib only."""
import json
from pathlib import Path


def _load(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return {c["url"].rstrip("/"): c for c in json.loads(p.read_text())}
    except Exception:
        return None


def _chg(url, field, before, after, sev):
    trunc = lambda v: (str(v)[:80] if v is not None else "—")
    return {"url": url, "field": field, "before": trunc(before), "after": trunc(after), "sev": sev}


def diff(cfg, curr_path="corpus.json", prev_path="corpus.prev.json"):
    curr, prev = _load(curr_path), _load(prev_path)
    if curr is None:
        return {"error": "no corpus.json — run `ingest` first"}
    if prev is None:
        return {"error": "no corpus.prev.json yet — appears after your SECOND `ingest` "
                         "(each crawl keeps the previous one for comparison)"}
    added = sorted(set(curr) - set(prev))
    removed = sorted(set(prev) - set(curr))
    changes = []
    for url in sorted(set(curr) & set(prev)):
        c, p = curr[url], prev[url]
        cs, ps = c.get("status", 200), p.get("status", 200)
        if cs != ps:
            changes.append(_chg(url, "status", ps, cs, "high" if cs != 200 else "med"))
        cr, pr = (c.get("robots") or ""), (p.get("robots") or "")
        if ("noindex" in cr) != ("noindex" in pr):
            changes.append(_chg(url, "robots", pr or "(indexable)", cr or "(indexable)",
                                "high" if "noindex" in cr else "med"))
        if (c.get("canonical") or "") != (p.get("canonical") or ""):
            changes.append(_chg(url, "canonical", p.get("canonical"), c.get("canonical"), "med"))
        if (c.get("title") or "") != (p.get("title") or ""):
            changes.append(_chg(url, "title", p.get("title"), c.get("title"),
                                "med" if not c.get("title") else "low"))
        if (c.get("description") or "") != (p.get("description") or ""):
            changes.append(_chg(url, "meta description", p.get("description"), c.get("description"),
                                "med" if not c.get("description") else "low"))
        ch1, ph1 = (c.get("h1") or [""])[0] if c.get("h1") else "", (p.get("h1") or [""])[0] if p.get("h1") else ""
        if ch1 != ph1:
            changes.append(_chg(url, "H1", ph1, ch1, "low"))
        dropped = set(p.get("jsonld_types") or []) - set(c.get("jsonld_types") or [])
        if dropped:
            changes.append(_chg(url, "schema types dropped", ", ".join(sorted(dropped)), "(gone)", "med"))
        cw, pw = c.get("words") or 0, p.get("words") or 0
        if pw > 200 and cw < pw * 0.7:
            changes.append(_chg(url, "word count", pw, cw, "med"))
        if "viewport" in c and "viewport" in p and p.get("viewport") and not c.get("viewport"):
            changes.append(_chg(url, "viewport meta", "present", "GONE", "med"))
    order = {"high": 0, "med": 1, "low": 2}
    changes.sort(key=lambda x: order[x["sev"]])
    return {"pages_now": len(curr), "pages_before": len(prev),
            "added": added, "removed": removed, "changes": changes,
            "counts": {s: sum(1 for x in changes if x["sev"] == s) for s in ("high", "med", "low")}}


def alerts(cfg):
    """High/med regressions for the anomaly radar (noindex appeared, status flips,
    schema dropped, content shrank) — additions and cosmetic edits don't alarm."""
    d = diff(cfg)
    if d.get("error"):
        return []
    out = [{"sev": c["sev"], "kind": "site-change",
            "msg": f"{c['field']} changed on {c['url'].rsplit('/', 1)[-1] or c['url']}: "
                   f"{c['before']} → {c['after']}"}
           for c in d["changes"] if c["sev"] in ("high", "med")]
    if d["removed"]:
        out.append({"sev": "med", "kind": "site-change",
                    "msg": f"{len(d['removed'])} pages disappeared from the crawl "
                           f"(first: {d['removed'][0]})"})
    return out[:12]


def render_md(cfg, d=None):
    d = d or diff(cfg)
    if d.get("error"):
        return f"# Site changes\n\n- ℹ {d['error']}"
    L = [f"# Site changes since the previous crawl — {cfg.get('site', 'site')}",
         f"{d['pages_before']} → {d['pages_now']} pages · **+{len(d['added'])} added · "
         f"−{len(d['removed'])} removed** · {d['counts']['high']} high / {d['counts']['med']} med / "
         f"{d['counts']['low']} low changes", ""]
    if d["counts"]["high"]:
        L.append("## 🔴 Indexability regressions — check these NOW")
        for c in d["changes"]:
            if c["sev"] == "high":
                L.append(f"- **{c['url']}** — {c['field']}: {c['before']} → **{c['after']}**")
        L.append("")
    if d["changes"]:
        L += ["## All changes", "| sev | page | field | before | after |", "|---|---|---|---|---|"]
        for c in d["changes"][:40]:
            L.append(f"| {c['sev']} | {c['url'].rsplit('/', 1)[-1][:30]} | {c['field']} | "
                     f"{c['before'][:40]} | {c['after'][:40]} |")
    else:
        L.append("_No on-page changes between the two crawls._")
    if d["added"]:
        L += ["", "**New pages:** " + ", ".join(u.rsplit("/", 1)[-1] for u in d["added"][:10])]
    if d["removed"]:
        L += ["", "**Removed pages:** " + ", ".join(u.rsplit("/", 1)[-1] for u in d["removed"][:10])]
    L += ["", "_Runs from the crawl history (`ingest` keeps the previous corpus). Daily cron + "
          "`anomaly --alert` = 24/7 site monitoring, locally. Run after every deploy._"]
    return "\n".join(L)
