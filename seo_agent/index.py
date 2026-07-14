"""Dedup + internal-link index over an ingested corpus (corpus.json). File-based,
no DB — TF-IDF cosine. Body space for linking / content-dup; title space for
query-cannibalization. build_vectorizer() is the swap-point for real embeddings.

Reusable across sites: it reads the generic {url, title, description, headings,
text} shape produced by ingest.py."""
import json
import re
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_corpus(path="corpus.json"):
    return json.load(open(path))


def build_vectorizer(texts):
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                          sublinear_tf=True, min_df=1, max_df=0.6, max_features=40000)
    return vec, vec.fit_transform(texts)


class Index:
    def __init__(self, corpus):
        self.corpus = corpus
        bodies = [" ".join([c.get("title", ""), c.get("title", ""),
                            c.get("description", ""), " ".join(c.get("headings", [])),
                            c.get("text", "")]) for c in corpus]
        self.vec, self.X = build_vectorizer(bodies)
        titles = [(c.get("title", "") + " " +
                   re.sub(r"[-/]", " ", c.get("url", "").rsplit("/", 1)[-1])) for c in corpus]
        self.tvec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                    sublinear_tf=True, min_df=1)
        self.tX = self.tvec.fit_transform(titles)

    def _label(self, i):
        return self.corpus[i].get("url") or self.corpus[i].get("title", f"#{i}")

    def check_topic(self, title, extend_at=0.50, related_at=0.30, exclude=None):
        sims = cosine_similarity(self.tvec.transform([title]), self.tX)[0]
        top = []
        for i in sims.argsort()[::-1]:
            lab = self._label(i)
            if lab == exclude:
                continue
            top.append((lab, float(sims[i])))
            if len(top) >= 3:
                break
        best = top[0][1] if top else 0.0
        verdict = "EXTEND" if best >= extend_at else "RELATED" if best >= related_at else "NOVEL"
        return verdict, top

    def link_targets(self, text, k=4, floor=0.12):
        sims = cosine_similarity(self.vec.transform([text]), self.X)[0]
        return [(self._label(i), float(sims[i])) for i in sims.argsort()[::-1][:k]
                if sims[i] >= floor]

    def duplicate_pairs(self, threshold=0.55, space="title"):
        M = self.tX if space == "title" else self.X
        S = cosine_similarity(M)
        pairs = [(S[i, j], self._label(i), self._label(j))
                 for i in range(len(self.corpus)) for j in range(i + 1, len(self.corpus))
                 if S[i, j] >= threshold]
        pairs.sort(reverse=True)
        return pairs

    def clusters(self, threshold=0.55, space="title"):
        pairs = self.duplicate_pairs(threshold, space)
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for _, a, b in pairs:
            parent[find(a)] = find(b)
        groups = {}
        for _, a, b in pairs:
            groups.setdefault(find(a), set()).update([a, b])
        peak = {}
        for sc, a, b in pairs:
            k = find(a)
            peak[k] = max(peak.get(k, 0), sc)
        out = [{"members": sorted(m), "peak": peak.get(r, 0)} for r, m in groups.items()]
        out.sort(key=lambda g: (-len(g["members"]), -g["peak"]))
        return out
