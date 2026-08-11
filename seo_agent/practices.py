"""Best practices — learned, applied, and PROVEN on this site. The dashboard's
show-don't-tell panel: every row pairs a practice the tool enforces with the live
numbers from *this* workspace — how many pages violate it, how many we fixed
(ledger), and the measured lift where follow-ups exist. Three evidence tiers:

  measured  — this site's holdout-adjusted follow-ups say it works (strongest)
  applied   — we found N violations here and shipped M fixes; measuring now
  encoded   — a field-tested rule baked into the tool (docs/LEARNINGS.md)

Pure-local (corpus + ledger + brain + learn); degrades to whatever exists. The
`practices` command / dashboard panel is how a new operator sees, on day one,
what the tool knows and what it has actually done here. Stdlib only."""
import re
from pathlib import Path

from . import audit, citability, ledger, learn


def _corpus(path="corpus.json"):
    try:
        from .index import load_corpus
        return load_corpus(path)
    except Exception:
        return []


def _fixes_by_type(cfg):
    out = {}
    try:
        for c in ledger.changes(cfg):
            out[c["type"]] = out.get(c["type"], 0) + 1
    except Exception:
        pass
    return out


def _lift(cfg, typ, horizon=28):
    """QUALIFIED evidence only (W2): n≥3 with a 95% CI excluding zero. Small positive
    samples read as 'measuring', never as proof."""
    try:
        v = (learn.local_lessons(cfg).get(typ) or {})
        v = v.get(horizon) or next(iter(v.values()), None)
        if v and v.get("qualified") and v["win_rate"] >= 0.5:
            return (f"{v['mean_lift']:+g} avg clicks/page at +{horizon}d "
                    f"(±{v.get('ci95')} CI95, {int(v['win_rate']*100)}% win, n={v['n']})")
    except Exception:
        pass
    return None


def report(cfg, corpus_path="corpus.json"):
    """[{practice, found, fixed, proof, tier}] — live numbers from this workspace."""
    corpus = _corpus(corpus_path)
    fixes = _fixes_by_type(cfg)
    rows = []

    def row(practice, found, fix_types, example=""):
        fixed = sum(fixes.get(t, 0) for t in fix_types)
        proof = next((p for p in (_lift(cfg, t) for t in fix_types) if p), None)
        tier = "measured" if proof else ("applied" if fixed else "encoded")
        rows.append({"practice": practice, "found": found, "fixed": fixed,
                     "proof": proof or example, "tier": tier})

    if corpus:
        # 1. current-year titles (the one a human caught — LEARNINGS #23)
        F = []
        audit.freshness(corpus, F)
        stale = sum(1 for f in F if f["sev"] == "med")
        body = next((int(m.group(1)) for f in F if f["sev"] == "low"
                     for m in [re.match(r"(\d+) pages", f["msg"])] if m), 0)
        row("Keep years in titles/H1s current — stale years depress CTR + freshness",
            stale, ["retitle", "fix:freshness", "update_meta"],
            f"{body} more pages have stale years in the body" if body else "")
        # 2-4. AI-answer extractability (citability signals)
        cit = citability.report(cfg, corpus_path)
        miss = cit.get("missing", {})
        row("Open with a direct 40–170-word answer (AI engines quote these passages)",
            miss.get("answer_first", 0), ["citability", "update_content", "refresh"], "")
        row("Use question-form H2/H3s mapped to People-Also-Ask",
            miss.get("qa_headings", 0), ["citability", "update_content"], "")
        row("Every page: a hard number per section + a list or table",
            max(miss.get("fact_density", 0), miss.get("lists_or_tables", 0)),
            ["update_content", "refresh"], "")
        # 5. meta description present (order-independent parsing — LEARNINGS #1)
        no_meta = sum(1 for c in corpus if c.get("status", 200) == 200 and not c.get("description"))
        row("Every indexable page has a meta description", no_meta, ["fix:meta", "update_meta"], "")

    # 6. what measurement itself has proven — wins AND losses, honestly labeled
    try:
        for r in learn.ranking(cfg):
            ev = (f"{r['mean_lift']:+g} avg lift"
                  + (f" ±{r['ci95']} CI95" if r.get("ci95") else "")
                  + f" ({int(r['win_rate']*100)}% win, n={r['n']}, {r['source']})")
            if r.get("qualified") and r["win_rate"] >= 0.5:
                rows.append({"practice": f"Do more '{r['type']}' changes — proven track record",
                             "found": None, "fixed": r["n"], "proof": ev, "tier": "measured"})
            elif r["mean_lift"] < 0 and r["n"] >= 3:
                rows.append({"practice": f"Rethink '{r['type']}' changes — measurably NOT working here",
                             "found": None, "fixed": r["n"], "proof": ev, "tier": "measured"})
            elif r["mean_lift"] > 0:
                rows.append({"practice": f"'{r['type']}' changes trending positive — collecting evidence",
                             "found": None, "fixed": r["n"],
                             "proof": ev + " — needs n≥3 with CI>0 to graduate", "tier": "applied"})
    except Exception:
        pass
    # 7. brain lessons (negative knowledge is a best practice too)
    try:
        from . import brain
        for e in brain.load(cfg)["entries"]:
            if e["kind"] == "lesson":
                rows.append({"practice": e["text"][:110], "found": None, "fixed": None,
                             "proof": e["source"], "tier": "measured"})
    except Exception:
        pass
    order = {"measured": 0, "applied": 1, "encoded": 2}
    rows.sort(key=lambda r: (order[r["tier"]], -(r["found"] or 0)))
    return {"rows": rows, "encoded_rules": _rules_count()}


def _rules_count():
    """How many field-tested rules ship with the tool (docs/LEARNINGS.md)."""
    p = Path(__file__).resolve().parent.parent / "docs" / "LEARNINGS.md"
    try:
        return len(re.findall(r"^\*\*\d+\.", p.read_text(), re.M))
    except Exception:
        return 0


_ICON = {"measured": "✅ measured", "applied": "🔧 applied", "encoded": "📘 encoded"}


def render_md(cfg, r=None):
    r = r or report(cfg)
    L = [f"# Best practices — learned & applied on {cfg.get('site', 'this site')}",
         f"_{r['encoded_rules']} field-tested rules ship with the tool (docs/LEARNINGS.md); "
         "below: how they play out HERE — found → fixed → measured._", "",
         "| practice | found | fixed | evidence |", "|---|--:|--:|---|"]
    for row in r["rows"][:14]:
        L.append(f"| {_ICON[row['tier']]} · {row['practice']} | "
                 f"{row['found'] if row['found'] is not None else '—'} | "
                 f"{row['fixed'] if row['fixed'] is not None else '—'} | {row['proof'] or '—'} |")
    L += ["", "_✅ measured = holdout-adjusted follow-ups on this site · 🔧 applied = shipped, "
          "measuring · 📘 encoded = enforced by the audit/gates. Fix flow: `plan` → approve → "
          "`apply --approved` → the ledger measures it._"]
    return "\n".join(L)
