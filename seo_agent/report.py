"""HTML dashboard — one self-contained, shareable report fusing the Site Doctor,
the action plan, GEO/AEO readiness, E-E-A-T, and (when wired) GSC opportunities.
Writes `report.html`: open in a browser or host it. No external assets; light +
dark aware. Everything degrades — sections whose data is unavailable are omitted."""
import datetime
import html as _h
import os
import shutil
import subprocess

from . import analyze, audit, authority_flow, citability, eeat, entity, geo, plan

# Headless-browser binaries we can drive to print HTML → PDF, in preference order.
_BROWSERS = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Program Files/Google/Chrome/Application/chrome.exe",
]


def _find_browser():
    for b in _BROWSERS:
        return_path = shutil.which(b) if os.sep not in b else (b if os.path.exists(b) else None)
        if return_path:
            return return_path
    return None


def to_pdf(html_path, pdf_out=None):
    """Render an existing HTML report to PDF via a headless Chromium/Chrome/Edge.
    Returns the PDF path, or None (with the reason) if no browser is available —
    the HTML is always still there, so this degrades gracefully."""
    browser = _find_browser()
    if not browser:
        return None, "no Chrome/Chromium/Edge found — open report.html and Print → Save as PDF"
    pdf_out = pdf_out or os.path.splitext(html_path)[0] + ".pdf"
    url = "file://" + os.path.abspath(html_path)
    try:
        subprocess.run([browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_out}", url],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    except Exception as e:  # noqa: BLE001 — any launch failure degrades to HTML-only
        return None, f"browser render failed ({type(e).__name__})"
    return (pdf_out, None) if os.path.exists(pdf_out) else (None, "browser produced no file")

_CSS = """
:root{--bg:#fff;--fg:#111;--mut:#666;--card:#f6f7f9;--bd:#e3e6ea;--hi:#e5484d;--me:#f5a524;--lo:#e8c020;--ok:#12b886;--ac:#3b82f6}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mut:#9aa4af;--card:#161b22;--bd:#2a313a;--hi:#ff6b6b}}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
.wrap{max-width:960px;margin:0 auto;padding:32px 20px}
h1{font-size:26px;margin:0 0 2px}h2{font-size:18px;margin:32px 0 10px;border-bottom:1px solid var(--bd);padding-bottom:6px}
.sub{color:var(--mut);margin:0 0 24px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.tile{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:16px}
.tile .n{font-size:28px;font-weight:700}.tile .l{color:var(--mut);font-size:13px}
table{width:100%;border-collapse:collapse;font-size:14px;overflow-x:auto;display:block}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--bd);vertical-align:top}
th{color:var(--mut);font-weight:600}tr:last-child td{border:0}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600;color:#fff}
.hi{background:var(--hi)}.me{background:var(--me)}.lo{background:var(--lo);color:#000}
.pill{background:var(--card);border:1px solid var(--bd);border-radius:999px;padding:2px 10px;font-size:12px;color:var(--mut);margin:0 6px 6px 0;display:inline-block}
code{background:var(--card);padding:1px 6px;border-radius:6px;font-size:12px}
.foot{color:var(--mut);font-size:12px;margin-top:40px;border-top:1px solid var(--bd);padding-top:12px}
"""


def _tile(n, label):
    return f'<div class="tile"><div class="n">{n}</div><div class="l">{_h.escape(str(label))}</div></div>'


def build(cfg, out="report.html"):
    site = cfg.get("site", "site")
    A = _safe(lambda: audit.report(cfg))
    G = _safe(lambda: geo.report(cfg))
    E = _safe(lambda: eeat.report(cfg))
    CI = _safe(lambda: citability.report(cfg))
    EN = _safe(lambda: entity.report(cfg))
    acts = _safe(lambda: plan.build(cfg)) or []
    gsc = _safe(lambda: analyze.gsc_opportunities(cfg))

    tiles = []
    if A:
        tiles.append(_tile(f"{A['counts']['high']} / {A['counts']['med']} / {A['counts']['low']}", "audit high / med / low"))
        tiles.append(_tile(A["links"].get("orphans", "—"), "orphan pages"))
    if G:
        tiles.append(_tile(f"{G['avg_score']}/100", "GEO readiness"))
    if CI:
        tiles.append(_tile(f"{CI['avg']}/100", "AI citability"))
    if E:
        tiles.append(_tile(f"{E['avg_signals']}/4", "E-E-A-T signals"))
    if gsc:
        tiles.append(_tile(len(gsc["striking"]), "striking-distance"))

    body = [f"<h1>SEO report — {_h.escape(site)}</h1>",
            f'<p class="sub">{datetime.date.today().isoformat()} · generated by seo-content-pipeline</p>',
            f'<div class="tiles">{"".join(tiles)}</div>']

    if acts:
        body.append("<h2>Action plan — do next</h2><table><tr><th>#</th><th>do</th><th>target</th><th>why</th><th>effort</th><th>cmd</th></tr>")
        for i, x in enumerate(acts[:12], 1):
            tgt = x["target"].rsplit("/", 1)[-1] or x["target"]
            body.append(f"<tr><td>{i}</td><td><b>{_h.escape(x['kind'])}</b></td><td>{_h.escape(tgt[:40])}</td>"
                        f"<td>{_h.escape(x['why'][:70])}</td><td>{x['effort']}</td><td><code>{_h.escape(x['cmd'])}</code></td></tr>")
        body.append("</table>")

    if A and A["findings"]:
        order = {"high": 0, "med": 1, "low": 2}
        body.append("<h2>Site Doctor — top findings</h2><table><tr><th>sev</th><th>area</th><th>finding</th></tr>")
        for f in sorted(A["findings"], key=lambda f: order[f["sev"]])[:15]:
            cls = {"high": "hi", "med": "me", "low": "lo"}[f["sev"]]
            body.append(f'<tr><td><span class="badge {cls}">{f["sev"]}</span></td><td>{f["cat"]}</td>'
                        f'<td>{_h.escape(f["msg"])}</td></tr>')
        body.append("</table>")

    if G:
        body.append(f"<h2>GEO / AEO readiness — {G['avg_score']}/100</h2>")
        if G["ai_blocked"]:
            body.append('<p><span class="badge hi">AI crawlers blocked</span> — the site is opted out of AI answers.</p>')
        body.append("<p>Most-missing signals: " + "".join(
            f'<span class="pill">{_h.escape(k)} · {n}</span>' for k, n in list(G["missing"].items())[:8] if n) + "</p>")

    if EN or CI:
        body.append("<h2>AI search — entity & citability</h2>")
        if EN:
            wd = (f'<span class="badge ok">Wikidata {EN["wikidata"]["qid"]}</span>' if EN["wikidata"]
                  else '<span class="badge hi">no Wikidata entity</span>')
            body.append(f"<p>{wd} · sameAs profiles: {len(EN['sameAs_present'])} · "
                        f"brand salience {EN['salience']}</p>")
        if CI:
            body.append("<p>Passage-citability <b>" + f"{CI['avg']}/100</b>. Fix site-wide: " + "".join(
                f'<span class="pill">{_h.escape(k)} · {n}</span>'
                for k, n in sorted(CI["missing"].items(), key=lambda kv: -kv[1])[:5] if n) + "</p>")

    if gsc and gsc["striking"]:
        body.append("<h2>Striking distance — one push to page 1</h2><table><tr><th>query</th><th>pos</th><th>impr</th></tr>")
        for r in gsc["striking"][:12]:
            body.append(f"<tr><td>{_h.escape(r['query'])}</td><td>{r['position']:.1f}</td><td>{r['impressions']}</td></tr>")
        body.append("</table>")

    body.append('<p class="foot">Fixes are proposed, not applied — review and apply as PRs. '
                'Run <code>plan</code> for the live action list.</p>')
    from . import edition
    if not edition.has(cfg, "white_label_reports"):  # open edition keeps a small attribution
        body.append('<p class="foot" style="opacity:.6">Generated with the SEO Content Pipeline · '
                    'white-label reports available on Pro+</p>')
    doc = f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>" \
          f"<title>SEO report — {_h.escape(site)}</title><style>{_CSS}</style></head>" \
          f"<body><div class=wrap>{''.join(body)}</div></body></html>"
    open(out, "w").write(doc)
    return out


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None
