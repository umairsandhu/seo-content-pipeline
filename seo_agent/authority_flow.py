"""Internal authority flow — compute PageRank over the site's OWN internal link
graph (numpy power iteration) to see where link equity actually concentrates, and
sculpt it toward money pages. Complements `audit`'s orphan/click-depth checks with a
quantitative flow model.

Surfaces: pages hoarding authority (high PR, few outlinks), money/pillar pages
starved of internal PR, and dangling sinks. Deterministic, offline (corpus.json +
numpy). Site-agnostic."""
import numpy as np

from .index import load_corpus


def _norm(u):
    return (u or "").split("#")[0].split("?")[0].rstrip("/")


def pagerank(corpus, damping=0.85, iters=60):
    urls = [_norm(c["url"]) for c in corpus]
    idx = {u: i for i, u in enumerate(urls)}
    n = len(urls)
    M = np.zeros((n, n))
    for c in corpus:
        src = idx[_norm(c["url"])]
        outs = {idx[_norm(l)] for l in (c.get("links") or []) if _norm(l) in idx and idx[_norm(l)] != src}
        if outs:
            for d in outs:
                M[d, src] = 1.0 / len(outs)
        else:
            M[:, src] = 1.0 / n  # dangling → teleport
    r = np.full(n, 1.0 / n)
    tele = np.full(n, 1.0 / n)
    for _ in range(iters):
        r = damping * M.dot(r) + (1 - damping) * tele
    return urls, idx, r


def report(cfg, corpus_path="corpus.json"):
    corpus = load_corpus(corpus_path)
    urls, idx, pr = pagerank(corpus)
    inbound = np.zeros(len(urls))
    outbound = [0] * len(urls)
    for c in corpus:
        s = idx[_norm(c["url"])]
        outs = {idx[_norm(l)] for l in (c.get("links") or []) if _norm(l) in idx}
        outbound[s] = len(outs)
        for d in outs:
            inbound[d] += 1
    pillars = {("/" + p.strip("/")) for p in (cfg.get("pillars") or {})}
    rows = []
    for i, u in enumerate(urls):
        rows.append({"url": corpus[i]["url"], "pr": float(pr[i]), "inbound": int(inbound[i]),
                     "outbound": outbound[i],
                     "is_pillar": any(pl in u for pl in pillars) if pillars else False})
    rows.sort(key=lambda r: -r["pr"])
    top = rows[:15]
    # money pages (pillars) starved of PR = below median PR
    med = float(np.median(pr))
    starved_pillars = [r for r in rows if r["is_pillar"] and r["pr"] < med]
    # hoarders: high PR, few outbound (equity dead-ends)
    hoarders = sorted([r for r in rows if r["pr"] >= med and r["outbound"] <= 2],
                      key=lambda r: -r["pr"])[:10]
    sinks = [r for r in rows if r["outbound"] == 0]
    # sculpt plan: route authority from hoarders/top pages INTO starved money pages
    donors = (hoarders or top)[:8]
    sculpt = []
    for pillar in starved_pillars[:8]:
        donor = next((d for d in donors if d["url"] != pillar["url"]), None)
        if donor:
            sculpt.append({"from": donor["url"], "to": pillar["url"],
                           "reason": f"donor PR {donor['pr']*1000:.2f}‰ → starved pillar ({pillar['inbound']} inbound)"})
    return {"pages": len(rows), "top": top, "starved_pillars": starved_pillars,
            "hoarders": hoarders, "sinks": len(sinks), "sculpt": sculpt}


def render_md(cfg, r):
    L = [f"# Internal authority flow (PageRank) — {cfg.get('site','site')}",
         f"{r['pages']} pages · {r['sinks']} dead-end pages (no internal outlinks)", "",
         "## Top authority pages", "| PR | in | out | page |", "|--:|--:|--:|---|"]
    for p in r["top"][:10]:
        L.append(f"| {p['pr']*1000:.2f}‰ | {p['inbound']} | {p['outbound']} | {p['url'].rsplit('/',1)[-1]} |")
    if r["starved_pillars"]:
        L += ["", "## 🔴 Money/pillar pages starved of internal authority (link to these more)"]
        for p in r["starved_pillars"][:10]:
            L.append(f"- {p['url']} — only {p['inbound']} inbound internal links")
    if r["hoarders"]:
        L += ["", "## 🟡 Authority hoarders (high PR, ≤2 outlinks — add links from here to money pages)"]
        for p in r["hoarders"][:8]:
            L.append(f"- {p['url'].rsplit('/',1)[-1]} (PR {p['pr']*1000:.2f}‰, {p['outbound']} outlinks)")
    if r.get("sculpt"):
        L += ["", "## ✅ Sculpting plan — add these internal links (route authority to money pages)"]
        for s in r["sculpt"]:
            L.append(f"- link **{s['from'].rsplit('/',1)[-1]}** → **{s['to'].rsplit('/',1)[-1]}** ({s['reason']})")
    return "\n".join(L)
