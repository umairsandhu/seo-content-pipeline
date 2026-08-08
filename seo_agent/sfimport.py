"""Screaming Frog import — meet agencies where they already live. Takes SF's
'Internal:All' export (internal_all.csv / internal_html.csv, a dir, or a .zip) and:

  BOOTSTRAP — no corpus yet? Build a metadata-level corpus from the SF crawl
    (titles, metas, H1s, canonicals, robots, status, word counts, crawl depth) so
    the audit/freshness/indexability/sitediff layers light up without our crawler.
    (Content-level checks — citability, term-gap — still want `ingest`'s full text.)
  ENRICH — corpus exists? Merge SF fields (crawl depth, unique inlinks) into it AND
    cross-check the two crawlers: status/robots/canonical disagreements between
    Screaming Frog and our crawl are findings, not noise (they usually mean UA-based
    cloaking, redirects mid-flight, or a stale export).

AUTOMATING THE PULL — three tiers, pick one:
  1. SF Scheduler (GUI, simplest): File → Scheduling → weekly crawl, export
     'Internal:All' to <workspace>/sf-exports/ → the `agent` daemon (or bare `sf`)
     auto-imports anything new it finds there.
  2. SF headless CLI (paid license): `sf --crawl` shells out to
     screamingfrogseospider --headless and imports the result — cron- and
     agent-friendly.
  3. Manual: export from the GUI, run `sf --csv <file.zip>`.

Corpus rotation applies (corpus → corpus.prev.json), so two SF imports diff with
`sitediff` exactly like two of our own crawls. Stdlib only."""
import csv
import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from . import state

# SF column headers (stable across recent versions) → our corpus fields; matched
# case-insensitively, first-present wins.
_COLS = {
    "url": ("Address",),
    "status": ("Status Code",),
    "title": ("Title 1",),
    "description": ("Meta Description 1",),
    "h1": ("H1-1",),
    "robots": ("Meta Robots 1",),
    "canonical": ("Canonical Link Element 1",),
    "words": ("Word Count",),
    "crawl_depth": ("Crawl Depth",),
    "inlinks": ("Unique Inlinks", "Inlinks"),
    "indexability": ("Indexability Status", "Indexability"),
    "content_type": ("Content Type",),
}


def _rows_from_csv(text):
    rdr = csv.reader(io.StringIO(text))
    rows = list(rdr)
    if not rows:
        return []
    # SF sometimes writes a one-cell banner row ("Internal - All") above the header
    head_i = 0 if len(rows[0]) > 3 else 1
    head = [h.strip().lower() for h in rows[head_i]]
    idx = {}
    for field, names in _COLS.items():
        for n in names:
            if n.lower() in head:
                idx[field] = head.index(n.lower())
                break
    if "url" not in idx:
        return []
    out = []
    for r in rows[head_i + 1:]:
        if len(r) <= idx["url"] or not r[idx["url"]].startswith("http"):
            continue
        g = lambda f: (r[idx[f]].strip() if f in idx and idx[f] < len(r) else "")
        ct = g("content_type")
        if ct and "html" not in ct:
            continue  # images/css/js rows in Internal:All
        rec = {"url": g("url"), "source": "screamingfrog",
               "status": int(g("status") or 200) if (g("status") or "").isdigit() else 200,
               "title": g("title"), "description": g("description"),
               "h1": [g("h1")] if g("h1") else [], "headings": [g("h1")] if g("h1") else [],
               "robots": g("robots").lower(), "canonical": g("canonical"),
               "words": int(g("words") or 0) if (g("words") or "").isdigit() else 0,
               "sf_crawl_depth": int(g("crawl_depth") or 0) if (g("crawl_depth") or "").isdigit() else None,
               "sf_inlinks": int(g("inlinks") or 0) if (g("inlinks") or "").isdigit() else None,
               "sf_indexability": g("indexability"), "text": "", "links": []}
        out.append(rec)
    return out


def parse(paths):
    """SF export file(s) / dir / zip → normalized rows."""
    rows = []
    for p in ([paths] if isinstance(paths, (str, Path)) else list(paths)):
        p = Path(p)
        if p.is_dir():
            for f in sorted(p.glob("*.csv")):
                rows += _rows_from_csv(f.read_text(errors="ignore"))
        elif p.suffix == ".zip":
            with zipfile.ZipFile(p) as z:
                for name in z.namelist():
                    if name.endswith(".csv") and "internal" in name.lower():
                        rows += _rows_from_csv(z.read(name).decode("utf-8", "ignore"))
        elif p.exists():
            rows += _rows_from_csv(p.read_text(errors="ignore"))
    seen, out = set(), []
    for r in rows:
        u = r["url"].rstrip("/")
        if u not in seen:
            seen.add(u)
            out.append(r)
    return out


def import_csv(cfg, paths, corpus_path="corpus.json"):
    """Bootstrap or enrich the corpus from SF export(s); returns a summary with any
    crawler-disagreement findings."""
    rows = parse(paths)
    if not rows:
        return {"error": "no Screaming Frog rows found — export the 'Internal:All' tab "
                         "(CSV or the export .zip) and pass that file/folder"}
    cp = Path(corpus_path)
    existing = []
    if cp.exists():
        try:
            existing = json.loads(cp.read_text())
        except Exception:
            existing = []
    sf_corpus = bool(existing) and all(c.get("source") == "screamingfrog" for c in existing[:5])
    if not existing or sf_corpus:  # BOOTSTRAP / SF-refresh — rotate so sitediff compares crawls
        if existing:
            Path(str(cp).replace(".json", ".prev.json")).write_text(cp.read_text())
        cp.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
        return {"mode": "refresh" if existing else "bootstrap", "pages": len(rows), "discrepancies": [],
                "note": "metadata-level corpus from Screaming Frog — audit/freshness/"
                        "indexability/sitediff are live; run `ingest` for full-text depth "
                        "(citability, term-gap, voice)"
                        + (" · run `sitediff` to see what changed between SF crawls" if existing else "")}
    # ENRICH + cross-check
    by_url = {c["url"].rstrip("/"): c for c in existing}
    matched, discrepancies = 0, []
    for r in rows:
        c = by_url.get(r["url"].rstrip("/"))
        if not c:
            continue
        matched += 1
        c["sf_crawl_depth"], c["sf_inlinks"] = r["sf_crawl_depth"], r["sf_inlinks"]
        if r["status"] != c.get("status", 200):
            discrepancies.append(f"{r['url']}: status {c.get('status')} (our crawl) vs "
                                 f"{r['status']} (SF) — UA-dependent response or a change between crawls")
        if ("noindex" in r["robots"]) != ("noindex" in (c.get("robots") or "")):
            discrepancies.append(f"{r['url']}: robots disagree — ours '{c.get('robots')}' vs "
                                 f"SF '{r['robots']}' (cloaking or stale export?)")
        cc, sc = (c.get("canonical") or "").rstrip("/"), (r["canonical"] or "").rstrip("/")
        if cc and sc and cc != sc:
            discrepancies.append(f"{r['url']}: canonical disagrees — ours {cc} vs SF {sc}")
    cp.write_text(json.dumps(existing, ensure_ascii=False, indent=1))
    return {"mode": "enrich", "pages": len(rows), "matched": matched,
            "sf_only": len(rows) - matched, "discrepancies": discrepancies[:20]}


# ── automation ───────────────────────────────────────────────────────────────
def auto_import(cfg, export_dir="sf-exports"):
    """Watch-folder: import any SF export file not seen before (the `agent` daemon
    calls this every tick — pair it with SF's built-in Scheduler writing here)."""
    d = Path(export_dir)
    if not d.is_dir():
        return None
    st = state.read(cfg, "sf", None) or {"imported": []}
    new = [p for p in sorted(d.iterdir()) if p.suffix in (".csv", ".zip")
           and p.name not in st["imported"]]
    if not new:
        return None
    res = import_csv(cfg, new)
    st["imported"] = (st["imported"] + [p.name for p in new])[-100:]
    state.write(cfg, "sf", st)
    return {**res, "files": [p.name for p in new]}


_SF_BINS = ("screamingfrogseospider",
            "/Applications/Screaming Frog SEO Spider.app/Contents/MacOS/ScreamingFrogSEOSpiderLauncher")


def crawl(cfg, export_dir="sf-exports", timeout=3600):
    """Headless Screaming Frog crawl → export → import (needs SF installed + a paid
    license for CLI mode). The cron/agent-friendly pull."""
    binp = next((b for b in _SF_BINS if shutil.which(b) or Path(b).exists()), None)
    if not binp:
        return {"error": "Screaming Frog not found — install it, or use its GUI Scheduler "
                         f"to export into ./{export_dir}/ (auto-imported), or `sf --csv <export>`"}
    site = cfg.get("site")
    out = Path(export_dir)
    out.mkdir(exist_ok=True)
    try:
        subprocess.run([binp, "--crawl", site, "--headless", "--overwrite",
                        "--output-folder", str(out.resolve()),
                        "--export-tabs", "Internal:All"],
                       check=True, capture_output=True, timeout=timeout)
    except Exception as e:
        return {"error": f"SF headless crawl failed: {e} (CLI mode needs a paid SF license)"}
    return auto_import(cfg, export_dir) or {"error": f"crawl ran but no export appeared in {out}/"}


def render_md(cfg, r):
    if not r:
        return "# Screaming Frog\n\n_Nothing new to import (drop exports in `sf-exports/` or `sf --csv <file>`)._"
    if r.get("error"):
        return f"# Screaming Frog import\n\n- ⚠ {r['error']}"
    L = [f"# Screaming Frog import — {r['mode']}",
         f"- {r['pages']} HTML pages" + (f" · matched {r['matched']} to our crawl · {r['sf_only']} SF-only"
                                         if r["mode"] == "enrich" else ""),
         f"- files: {', '.join(r['files'])}" if r.get("files") else ""]
    if r.get("note"):
        L.append(f"- {r['note']}")
    if r.get("discrepancies"):
        L += ["", "## ⚠ Crawler disagreements (worth a look — cloaking, redirects, or stale export)"]
        L += [f"- {d}" for d in r["discrepancies"]]
    L += ["", "_Now run `audit` / `sitediff` / `plan` — SF data flows through the whole pipeline. "
          "Automate the pull: SF Scheduler → `sf-exports/` (the `agent` daemon auto-imports) or "
          "`sf --crawl` (headless CLI)._"]
    return "\n".join(filter(None, L))
