"""Topical-authority structure analysis. Authority accrues at the CLUSTER level,
not the page: a healthy topic cluster has a pillar page that links to its members
and members that link back and to each other. This groups the corpus into topic
clusters, then scores each on internal-link density + whether a pillar (hub)
exists — surfacing clusters that are content-rich but structurally weak (the
fastest authority win).

Uses its OWN vectorizer (no max_df cap) — unlike the dedup index, topic clustering
must KEEP the shared topical terms that define a cluster."""
from urllib.parse import urljoin, urlparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .index import load_corpus


def _norm(base, href=""):
    try:
        p = urlparse(urljoin(base, href))
    except Exception:
        return None
    return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/") if p.scheme in ("http", "https") else None


def _topic_clusters(corpus, threshold):
    """Union-find topic groups over a shared-term-preserving TF-IDF."""
    texts = [" ".join([c.get("title", ""), " ".join(c.get("h1", [])), c.get("text", "")]) for c in corpus]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    S = cosine_similarity(vec.fit_transform(texts))
    n = len(corpus)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if S[i, j] >= threshold:
                parent[find(i)] = find(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [g for g in groups.values() if len(g) >= 2]


def clusters(cfg, threshold=0.15, corpus_path="corpus.json"):
    corpus = load_corpus(corpus_path)
    ids = {_norm(c.get("final_url") or c["url"]): c for c in corpus}
    adj = {}
    for c in corpus:
        s = _norm(c.get("final_url") or c["url"])
        adj[s] = {t for h in c.get("links", []) if (t := _norm(c["url"], h)) in ids and t != s}
    out = []
    for grp in _topic_clusters(corpus, threshold):
        mem = [_norm(corpus[i].get("final_url") or corpus[i]["url"]) for i in grp]
        mem = [m for m in mem if m in ids]
        if len(mem) < 2:
            continue
        edges = sum(1 for a in mem for b in mem if a != b and b in adj.get(a, ()))
        possible = len(mem) * (len(mem) - 1)
        density = round(edges / possible, 2) if possible else 0
        pillar = max(mem, key=lambda m: sum(1 for a in mem if m in adj.get(a, ())))
        pillar_inb = sum(1 for a in mem if pillar in adj.get(a, ()))
        out.append({"size": len(mem), "members": mem, "link_density": density,
                    "pillar": pillar, "pillar_inbound": pillar_inb,
                    "healthy": density >= 0.3 and pillar_inb >= max(2, len(mem) // 2)})
    out.sort(key=lambda c: -c["size"])
    return out


def render_md(cfg, cl):
    weak = [c for c in cl if not c["healthy"]]
    L = [f"# Topical authority — {cfg.get('site','site')}",
         f"{len(cl)} topic clusters · {len(weak)} need pillar/internal-link work "
         "(authority accrues at the cluster level — a pillar + dense internal links).", ""]
    for c in weak[:12]:
        names = " · ".join(m.rsplit("/", 1)[-1] for m in c["members"][:6])
        L.append(f"- size {c['size']}, link-density {c['link_density']}: {names}")
        L.append(f"    → pillar candidate: **{c['pillar'].rsplit('/', 1)[-1]}** — link the cluster to it and back")
    if not cl:
        L.append("_No multi-page topic clusters found (small corpus or highly distinct pages)._")
    elif not weak:
        L.append("_All clusters have a pillar + healthy internal linking._")
    return "\n".join(L)
