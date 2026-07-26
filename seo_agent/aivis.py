"""aivis — AI-visibility / LLM-citation tracker. The category-defining 2026 signal:
are you *mentioned and cited* inside AI answers (ChatGPT, Perplexity, Gemini, Google
AI Overviews), and how do you compare to competitors? Readiness (`geo`) is necessary
but not sufficient — you can't optimize what you can't measure.

For each prompt × engine it records: brand mentioned, brand cited (domain in the
answer's sources), first-mention rank, sentiment, and competitor share-of-voice.
Snapshots to `history/` + the SQLite store so week-over-week deltas are queryable.

Engines light up per available key (OPENAI/PERPLEXITY/ANTHROPIC/GEMINI + DataForSEO
for AI Overviews). With NO keys it returns an **agent-mode packet** — the agent runs
the prompts and fills the grid — so it works inside Claude with zero credentials.
Site-agnostic."""
import json
import os
import re
import urllib.request
from urllib.parse import urlparse

from . import history, providers, store

_POS = ("best", "top", "leading", "recommended", "popular", "trusted", "great", "excellent",
        "powerful", "reliable", "favorite", "standout", "strong")
_NEG = ("worst", "avoid", "expensive", "limited", "lacks", "poor", "outdated", "weak",
        "complicated", "buggy", "clunky", "overpriced")


def _domain(url):
    return urlparse(url if "//" in url else "//" + url).netloc.replace("www.", "").lower()


def _brand(cfg):
    b = (cfg.get("brand", {}) or {}).get("name") or _domain(cfg.get("site", "")).split(".")[0]
    return b, _domain(cfg.get("site", ""))


def prompts(cfg, n=12):
    """Use configured prompts, else synthesize buyer-intent prompts from brand + seeds."""
    ap = (cfg.get("aivis", {}) or {}).get("prompts")
    if ap:
        return ap[:40]
    brand, dom = _brand(cfg)
    cat = (cfg.get("aivis", {}) or {}).get("category") or f"{brand} category"
    seeds = (cfg.get("seeds") or []) + [s for ss in (cfg.get("seed_sets") or {}).values() for s in ss]
    base = [f"What is the best {cat} software?", f"Top {cat} tools compared",
            f"Best alternatives to {cfg.get('competitors',['a competitor'])[0]}" if cfg.get("competitors") else f"Best {cat} for teams",
            f"What is {brand} and who is it for?", f"Is {brand} any good?",
            f"{brand} vs competitors", f"Recommend a tool for {cat}"]
    base += [f"best tool for {s}" for s in seeds[:5]]
    return base[:n]


# ── engine callers (each returns (text, [citation_urls]) or None) ────────────
def _openai(prompt):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    body = {"model": os.environ.get("AIVIS_OPENAI_MODEL", "gpt-4o"),
            "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    txt = _post("https://api.openai.com/v1/chat/completions", body,
                {"Authorization": f"Bearer {key}"})
    try:
        return txt["choices"][0]["message"]["content"], _urls(txt["choices"][0]["message"]["content"])
    except Exception:
        return None


def _perplexity(prompt):
    key = os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        return None
    body = {"model": "sonar", "messages": [{"role": "user", "content": prompt}]}
    r = _post("https://api.perplexity.ai/chat/completions", body, {"Authorization": f"Bearer {key}"})
    try:
        text = r["choices"][0]["message"]["content"]
        return text, (r.get("citations") or _urls(text))
    except Exception:
        return None


def _anthropic(prompt):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = {"model": os.environ.get("AIVIS_ANTHROPIC_MODEL", "claude-sonnet-5"), "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]}
    r = _post("https://api.anthropic.com/v1/messages", body,
              {"x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        text = "".join(b.get("text", "") for b in r.get("content", []))
        return text, _urls(text)
    except Exception:
        return None


def _gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-2.0-flash:generateContent?key=" + key)
    r = _post(url, {"contents": [{"parts": [{"text": prompt}]}]}, {})
    try:
        text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
        return text, _urls(text)
    except Exception:
        return None


def _google_aio(cfg, prompt):
    """Google AI Overview presence + whether the brand domain appears (DataForSEO SERP)."""
    dfs = cfg.get("dataforseo", {})
    s = providers.serp(prompt, dfs.get("location_name"), dfs.get("language_name"))
    if s.get("error"):
        return None
    urls = [o.get("url", "") for o in s.get("organic", [])]
    text = " ".join(o.get("title", "") for o in s.get("organic", []))
    return ("[AI Overview present]" if s.get("ai_overview") else "") + " " + text, urls


def _post(url, body, headers):
    h = {"content-type": "application/json", **headers}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def _urls(text):
    return re.findall(r"https?://[^\s)\]}>\"']+", text or "")


def _sentiment(text, brand):
    t = (text or "").lower()
    i = t.find(brand.lower())
    if i < 0:
        return "n/a"
    window = t[max(0, i - 160): i + 160]
    pos = sum(w in window for w in _POS)
    neg = sum(w in window for w in _NEG)
    return "positive" if pos > neg else "negative" if neg > pos else "neutral"


def _analyze(text, citations, cfg):
    brand, dom = _brand(cfg)
    t = (text or "").lower()
    mentioned = brand.lower() in t
    cited = any(dom and dom in _domain(c) for c in citations) or (dom and dom in t)
    rank = None
    if mentioned:  # crude first-mention rank vs competitor brands named earlier
        names = [brand] + [c.split(".")[0] for c in cfg.get("competitors", [])]
        order = sorted([(t.find(nm.lower()), nm) for nm in names if t.find(nm.lower()) >= 0])
        rank = [nm for _, nm in order].index(brand) + 1 if any(nm == brand for _, nm in order) else None
    sov = {c.split(".")[0]: (c.split(".")[0].lower() in t) for c in cfg.get("competitors", [])}
    return {"mentioned": mentioned, "cited": bool(cited), "rank": rank,
            "sentiment": _sentiment(text, brand), "competitor_sov": sov}


def active_engines(cfg):
    e = []
    if os.environ.get("OPENAI_API_KEY"): e.append(("chatgpt", _openai))
    if os.environ.get("PERPLEXITY_API_KEY"): e.append(("perplexity", _perplexity))
    if os.environ.get("ANTHROPIC_API_KEY"): e.append(("claude", _anthropic))
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"): e.append(("gemini", _gemini))
    if providers._dfs_auth(): e.append(("google_aio", lambda p: _google_aio(cfg, p)))
    return e


def run(cfg):
    ps = prompts(cfg)
    engines = active_engines(cfg)
    if not engines:
        return {"mode": "agent", "prompts": ps, "packet": _agent_packet(cfg, ps)}
    rows = []
    for p in ps:
        for name, fn in engines:
            try:
                out = fn(p)
            except Exception:
                out = None
            if not out:
                continue
            text, cites = out
            a = _analyze(text, cites, cfg)
            rows.append({"prompt": p, "engine": name, **a})
    summary = _summarize(cfg, rows, engines)
    history.snapshot(cfg, "aivis", rows)
    store.record(cfg, "aivis", [{"key": f"{r['engine']}:mention", "v": int(r["mentioned"])} for r in rows],
                 key_field="key", value_fields=["v"])
    return {"mode": "live", "rows": rows, "summary": summary}


def _summarize(cfg, rows, engines):
    brand, _ = _brand(cfg)
    per = {}
    for name, _fn in engines:
        er = [r for r in rows if r["engine"] == name]
        n = len(er) or 1
        per[name] = {"mention_rate": round(sum(r["mentioned"] for r in er) / n, 2),
                     "citation_rate": round(sum(r["cited"] for r in er) / n, 2),
                     "prompts": len(er)}
    comp = {}
    for c in cfg.get("competitors", []):
        nm = c.split(".")[0]
        comp[nm] = round(sum(r["competitor_sov"].get(nm, False) for r in rows) / max(len(rows), 1), 2)
    return {"brand": brand, "per_engine": per,
            "brand_sov": round(sum(r["mentioned"] for r in rows) / max(len(rows), 1), 2),
            "competitor_sov": comp}


def _agent_packet(cfg, ps):
    brand, _ = _brand(cfg)
    engines = "ChatGPT, Perplexity, Google AI Overviews, Gemini, Claude"
    lines = "\n".join(f"{i+1}. {p}" for i, p in enumerate(ps))
    return (f"# AI-visibility check — run these prompts and report the grid\n\n"
            f"Brand: **{brand}** ({cfg.get('site','')}). Competitors: "
            f"{', '.join(cfg.get('competitors', [])) or '(none set)'}.\n\n"
            f"For EACH prompt below, query each engine you have access to ({engines}) and record: "
            f"is **{brand}** mentioned? is its domain **cited** in the sources? first-mention rank vs "
            f"competitors? sentiment (positive/neutral/negative)? which competitors are mentioned?\n\n"
            f"## Prompts\n{lines}\n\n"
            f"## Deliverable\nA table (prompt × engine) of mentioned / cited / rank / sentiment, then a "
            f"summary: per-engine mention + citation rate, brand share-of-voice, and competitor "
            f"share-of-voice. (Set OPENAI/PERPLEXITY/GEMINI/ANTHROPIC keys or DataForSEO to automate this.)")


def render_md(cfg, r):
    if r.get("mode") == "agent":
        return r["packet"]
    s = r["summary"]
    L = [f"# AI visibility — {s['brand']}", f"brand share-of-voice: **{s['brand_sov']*100:.0f}%** "
         f"of {len(r['rows'])} prompt×engine answers", "", "## Per engine",
         "| engine | mention rate | citation rate | prompts |", "|---|--:|--:|--:|"]
    for e, v in s["per_engine"].items():
        L.append(f"| {e} | {v['mention_rate']*100:.0f}% | {v['citation_rate']*100:.0f}% | {v['prompts']} |")
    if s["competitor_sov"]:
        L += ["", "## Competitor share-of-voice",
              "| competitor | mentioned in |", "|---|--:|"]
        for c, v in sorted(s["competitor_sov"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {c} | {v*100:.0f}% |")
    L.append("\n_Snapshotted to history — re-run weekly for citation-share trend._")
    return "\n".join(L)
