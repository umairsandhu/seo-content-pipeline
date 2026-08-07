"""Proactive brand-voice analysis — learn how this site already writes BEFORE the
first draft, instead of only reacting to review notes. Measures the existing corpus
(sentence rhythm, person, contractions, heading style, list/number density, title
patterns) and distills a voice profile the Writer persona receives on every draft
(stored in the brain as a preference → auto-injected via personas.system).

This answers the 'competent-but-generic content' critique: the writer starts from
the site's actual voice on day one. Deterministic, offline, stdlib. Site-agnostic."""
import re

from .index import load_corpus

_WORD = re.compile(r"[A-Za-z']+")
_CONTR = re.compile(r"\b\w+(?:n't|'re|'ll|'ve|'d|'s)\b", re.I)
_YOU = re.compile(r"\byou(?:r|rs)?\b", re.I)
_WE = re.compile(r"\b(?:we|our|ours|us)\b", re.I)
_Q = re.compile(r"^(how|what|why|when|where|which|who|can|is|do|does|should)\b", re.I)


def analyze(cfg, corpus_path="corpus.json", sample=30):
    """Voice metrics from the meatiest pages (words > 300, top `sample` by length)."""
    try:
        corpus = [c for c in load_corpus(corpus_path) if (c.get("words") or 0) > 300]
    except Exception:
        return None
    corpus = sorted(corpus, key=lambda c: -(c.get("words") or 0))[:sample]
    if not corpus:
        return None
    sent_lens, paras, per100 = [], [], {"contr": 0, "you": 0, "we": 0, "nums": 0}
    total_words = 0
    q_heads = heads = lists = 0
    for c in corpus:
        text = c.get("text", "") or ""
        words = len(_WORD.findall(text))
        total_words += words
        sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 2]
        sent_lens += [len(_WORD.findall(s)) for s in sents]
        paras += [len(p.split()) for p in text.split("\n\n") if len(p.split()) > 10]
        per100["contr"] += len(_CONTR.findall(text))
        per100["you"] += len(_YOU.findall(text))
        per100["we"] += len(_WE.findall(text))
        per100["nums"] += len(re.findall(r"\b\d[\d,.%$]*\b", text))
        hs = c.get("headings", []) or []
        heads += len(hs)
        q_heads += sum(1 for h in hs if _Q.match(h.strip()) or h.strip().endswith("?"))
        lists += c.get("lists", 0) or 0
    titles = [c.get("title", "") for c in corpus if c.get("title")]
    r100 = {k: round(v / max(total_words, 1) * 100, 2) for k, v in per100.items()}
    avg_sent = round(sum(sent_lens) / max(len(sent_lens), 1), 1)
    profile = {
        "pages_analyzed": len(corpus),
        "avg_sentence_words": avg_sent,
        "avg_paragraph_words": round(sum(paras) / max(len(paras), 1), 1),
        "contractions_per_100w": r100["contr"],
        "you_per_100w": r100["you"], "we_per_100w": r100["we"],
        "numbers_per_100w": r100["nums"],
        "question_heading_share": round(q_heads / max(heads, 1), 2),
        "lists_per_page": round(lists / len(corpus), 1),
        "titles_with_numbers": round(sum(1 for t in titles if re.search(r"\d", t)) / max(len(titles), 1), 2),
        "avg_title_chars": round(sum(len(t) for t in titles) / max(len(titles), 1)),
    }
    profile["tone"] = ("conversational, reader-directed" if r100["contr"] >= 0.5 and r100["you"] >= 1.0
                       else "first-person-plural, brand-led" if r100["we"] > r100["you"]
                       else "neutral-professional")
    profile["summary"] = (
        f"Voice profile (measured from {len(corpus)} existing pages): {profile['tone']}; "
        f"sentences average ~{avg_sent} words; "
        f"{'contraction-friendly' if r100['contr'] >= 0.5 else 'few contractions (more formal)'}; "
        f"addresses the reader as 'you' {r100['you']:g}×/100w; "
        f"{int(profile['question_heading_share']*100)}% of headings are questions; "
        f"~{profile['lists_per_page']:g} lists per page; "
        f"{int(profile['titles_with_numbers']*100)}% of titles carry a number "
        f"(avg {profile['avg_title_chars']} chars). Match this voice unless briefed otherwise.")
    return profile


def apply(cfg):
    """Store the profile in the brain as a preference — the Writer persona then
    receives it on every draft automatically (personas.system → context_block)."""
    p = analyze(cfg)
    if not p:
        return {"ok": False, "error": "no corpus (run `ingest`) or no pages >300 words"}
    from . import brain
    r = brain.add(cfg, "preference", p["summary"], source="voice-analysis", tag="voice-profile",
                  evidence={k: v for k, v in p.items() if k != "summary"})
    return {"ok": True, "profile": p, "brain": r}


def render_md(cfg, r=None):
    r = r or apply(cfg)
    if not r.get("ok"):
        return f"# Brand voice\n\n- ⚠ {r.get('error')}"
    p = r["profile"]
    L = [f"# Brand voice — measured from {p['pages_analyzed']} pages", "",
         f"**{p['summary']}**", "",
         "| metric | value |", "|---|--:|"]
    for k in ("avg_sentence_words", "avg_paragraph_words", "contractions_per_100w", "you_per_100w",
              "we_per_100w", "numbers_per_100w", "question_heading_share", "lists_per_page",
              "titles_with_numbers", "avg_title_chars"):
        L.append(f"| {k.replace('_', ' ')} | {p[k]} |")
    L += ["", "_Stored in the brain as a preference — every future draft is written in this "
          "voice (and refined further by your review notes)._"]
    return "\n".join(L)
