"""Local dashboard — a single glass pane over the shared state the autopilot agents
write, AND the hand-holding layer for a first run. Serves a live web page (stdlib
`http.server`, zero deps) with: a Getting-started guide (wizard steps + the exact
next action), Situation, Plan, Execution, Ledger, Learning, Brain, Best-practices
(learned + applied here, with numbers), Documents-to-review (reports/drafts/change
files, viewable in-browser), and the interactive Review queue. Opens the browser
automatically (`--no-open` to skip). Local by default (127.0.0.1). Site-agnostic."""
import html
import json
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from . import autonomy, autopilot, ledger, review, state

_CACHE = {}


def _cached(key, ttl, fn):
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    val = fn()
    _CACHE[key] = (time.time(), val)
    return val

_CSS = """
:root{--ink:#0d1321;--em:#0e9f6e;--tx:#151b28;--mut:#5a6474;--line:#e3e7ee;--wash:#f6f8fb;--amber:#b45309;--red:#d64545}
*{box-sizing:border-box}body{margin:0;background:#eef1f5;color:var(--tx);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
header{background:var(--ink);color:#fff;padding:16px 26px;display:flex;align-items:center;gap:16px}
header b{font-size:17px}header .g{color:var(--em)}header form{margin-left:auto}
.wrap{max-width:1080px;margin:20px auto;padding:0 20px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.card.wide{grid-column:1/3}
h2{font-size:14px;letter-spacing:.04em;text-transform:uppercase;color:var(--mut);margin:0 0 10px}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:600}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:700}
.s-planned{background:#eef1f5;color:#5a6474}.s-dispatched{background:#e9f2ff;color:#1d4ed8}.s-in_review{background:#fef6e7;color:#b45309}
.s-approved{background:#eafaf3;color:#0b7a54}.s-changes{background:#fdeaea;color:#d64545}.s-done{background:#eafaf3;color:#0b7a54}
.sev-high{color:var(--red);font-weight:700}.sev-med{color:var(--amber);font-weight:700}
button{background:var(--ink);color:#fff;border:0;border-radius:7px;padding:5px 11px;font-size:12px;cursor:pointer}
button.g{background:var(--em)}form.inl{display:inline}input[type=text]{border:1px solid var(--line);border-radius:6px;padding:4px 7px;font-size:12px}
.mut{color:var(--mut)}.empty{color:var(--mut);font-style:italic}
"""


def _page(cfg):
    s = state.summary(cfg)
    sit, pl = s.get("situation") or {}, s.get("plan") or {}
    rep = s.get("report") or {}
    queue = [i for i in autonomy.load_queue(cfg) if i["status"] != "done"]
    site = html.escape(cfg.get("site", "site"))
    P = []
    # Getting started — the hand-holding layer (wizard + readiness, cached 10 min)
    guide = None
    try:
        from . import wizard
        guide = _cached("guide", 600, lambda: wizard.next_step(cfg))
    except Exception:
        pass
    if guide:
        steps, nxt = guide["steps"], guide["next"]
        done = sum(1 for st in steps if st["done"])
        P.append('<div class="card wide"><h2>Getting started — '
                 f'{done}/{len(steps)} steps · readiness {guide["readiness"]["score"]}/100</h2>')
        P.append('<p>' + " ".join(
            f'<span class="pill {"s-done" if st["done"] else ("s-in_review" if nxt and st["n"] == nxt["n"] else "s-planned")}" '
            f'title="{html.escape(st["title"])}">{st["n"]}</span>' for st in steps) + '</p>')
        if nxt:
            P.append(f'<p>▶ <b>Do this next: {html.escape(nxt["title"])}</b><br>'
                     f'<span class="mut">{html.escape(nxt["why"])}</span><br>'
                     f'<code>{html.escape(nxt["do"])}</code></p>')
        else:
            P.append('<p>🎉 <b>Setup complete.</b> <span class="mut">The loop below runs it: '
                     'Run cycle → approve → it ships, measures, and learns.</span></p>')
        P.append('</div>')
    # Situation
    P.append('<div class="card"><h2>Situation</h2>')
    if sit.get("health"):
        h = sit["health"]
        P.append(f'<p><b>{h.get("high",0)}</b> high · {h.get("med",0)} med · {h.get("low",0)} low issues · '
                 f'{len(sit.get("anomalies",[]))} anomalies</p>')
    for a in sit.get("anomalies", [])[:4]:
        P.append(f'<div class="sev-{a["sev"]}">⚠ {html.escape(a["msg"])}</div>')
    P.append('<table><tr><th>sev</th><th>problem</th></tr>' + "".join(
        f'<tr><td class="sev-{p["sev"]}">{p["sev"]}</td><td>{html.escape((p["msg"] or "")[:80])}</td></tr>'
        for p in sit.get("problems", [])[:7]) + '</table>' if sit.get("problems") else '<p class="empty">run a cycle</p>')
    P.append('</div>')
    # Plan (dated)
    P.append('<div class="card"><h2>Plan — dated backlog</h2>')
    items = pl.get("items", [])
    if items:
        P.append('<table><tr><th>due</th><th>action</th><th>target</th><th>cad</th><th>status</th></tr>' + "".join(
            f'<tr><td>{i["due_date"][5:]}</td><td>{html.escape(i["action"])}</td>'
            f'<td class="mut">{html.escape(str(i["target"]).rsplit("/",1)[-1][:22])}</td>'
            f'<td>{i["cadence"]}</td><td><span class="pill s-{i["status"]}">{i["status"]}</span></td></tr>'
            for i in items[:12]) + '</table>')
    else:
        P.append('<p class="empty">no plan yet — Run cycle</p>')
    P.append('</div>')
    # Execution
    ex = s.get("executions") or {}
    P.append('<div class="card"><h2>Execution</h2>')
    P.append(f'<p><b>{len(ex.get("done",[]))}</b> closed · <b>{len(ex.get("dispatched",[]))}</b> dispatched · '
             f'{len(ex.get("scheduled",[]))} scheduled ahead</p>')
    for d in ex.get("dispatched", [])[:6]:
        P.append(f'<div>▸ <b>{html.escape(d["action"])}</b> — <span class="mut">{html.escape(d.get("task",""))}</span></div>')
    P.append('</div>')
    # Ledger / wins
    P.append('<div class="card"><h2>Proven wins (ledger)</h2>')
    wins = rep.get("proven_wins", [])
    if wins:
        P.append('<table><tr><th>page</th><th>lift</th></tr>' + "".join(
            f'<tr><td class="mut">{html.escape(w["url"].rsplit("/",1)[-1][:26])}</td>'
            f'<td class="sev-med">+{w["holdout_adjusted_lift"]}</td></tr>' for w in wins[:7]) + '</table>')
    else:
        P.append('<p class="empty">attribution builds as GSC history accrues</p>')
    P.append('</div>')
    # Learning — impact by day/week/month + what worked best
    P.append('<div class="card wide"><h2>Learning — impact by day / week / month</h2>')
    try:
        from . import learn
        loc = learn.local_lessons(cfg)
        rank = learn.ranking(cfg)
        if loc:
            rows = []
            for t, hs in sorted(loc.items(), key=lambda kv: -(kv[1].get(28, kv[1].get(7, {})).get("mean_lift", 0))):
                c = lambda h: (f"{hs[h]['mean_lift']:+g} (n{hs[h]['n']})" if hs.get(h) else "—")
                wr = hs.get(28, hs.get(7, {})).get("win_rate", 0)
                rows.append(f'<tr><td>{html.escape(t)}</td><td class="n">{c(7)}</td><td class="n">{c(28)}</td>'
                            f'<td class="n">{c(90)}</td><td class="n">{int(wr*100)}%</td></tr>')
            P.append('<table><tr><th>change type</th><th>+7d</th><th>+28d</th><th>+90d</th><th>win</th></tr>'
                     + "".join(rows) + '</table>')
        else:
            P.append('<p class="empty">follow-ups accrue as GSC snapshots build after changes are logged</p>')
        if rank:
            P.append('<p>▶ <b>Do more of:</b> ' + " · ".join(
                f'{html.escape(r["type"])} ({r["mean_lift"]:+g}, {r["source"]})' for r in rank[:4]) + '</p>')
    except Exception:
        P.append('<p class="empty">learning unavailable</p>')
    P.append('</div>')

    # Brain — memory / playbooks / client taste (the Hermes-style loop, visible)
    P.append('<div class="card wide"><h2>Brain — memory · playbooks · client taste</h2>')
    try:
        from . import brain
        bs = brain.load(cfg)["entries"]
        if bs:
            lab = {"preference": "🎨 taste", "playbook": "📗 playbook", "lesson": "⚠ lesson", "fact": "📌 fact"}
            rows = "".join(
                f'<tr><td class="mut">{lab.get(e["kind"], e["kind"])}</td>'
                f'<td>{html.escape(e["text"][:120])}</td><td class="n">{e["updated"]}</td></tr>'
                for e in sorted(bs, key=lambda e: -e["score"])[:8])
            P.append('<table><tr><th></th><th>learned</th><th>updated</th></tr>' + rows + '</table>')
            P.append('<p class="mut">auto-injected into every writer/strategist prompt · '
                     'observe → distill → reuse → refine, every cycle</p>')
        else:
            P.append('<p class="empty">fills itself from review notes, client replies to delivered '
                     'reports (FEEDBACK …), and measured outcomes</p>')
    except Exception:
        P.append('<p class="empty">brain unavailable</p>')
    P.append('</div>')

    # Best practices — learned & applied HERE, with numbers (show, don't tell)
    P.append('<div class="card wide"><h2>Best practices — learned &amp; applied here</h2>')
    try:
        from . import practices
        pr = _cached("practices", 600, lambda: practices.report(cfg))
        if pr["rows"]:
            icon = {"measured": "✅", "applied": "🔧", "encoded": "📘"}
            rows = "".join(
                f'<tr><td>{icon[r["tier"]]}</td><td>{html.escape(r["practice"][:95])}</td>'
                f'<td class="n">{r["found"] if r["found"] is not None else "—"}</td>'
                f'<td class="n">{r["fixed"] if r["fixed"] is not None else "—"}</td>'
                f'<td class="mut">{html.escape((r["proof"] or "—")[:60])}</td></tr>'
                for r in pr["rows"][:10])
            P.append('<table><tr><th></th><th>practice</th><th>found</th><th>fixed</th><th>evidence</th></tr>'
                     + rows + '</table>')
            P.append(f'<p class="mut">✅ measured on this site · 🔧 applied, measuring · 📘 encoded — '
                     f'{pr["encoded_rules"]} field-tested rules ship with the tool. Full detail: <code>practices</code></p>')
        else:
            P.append('<p class="empty">run <code>ingest</code> — practices light up from the corpus + ledger</p>')
    except Exception:
        P.append('<p class="empty">practices unavailable</p>')
    P.append('</div>')

    # Documents & deliverables — everything reviewable, viewable in-browser
    P.append('<div class="card wide"><h2>Documents to review</h2>')
    try:
        docs = _docs_list(cfg)
        if docs:
            rows = "".join(
                f'<tr><td><a href="/doc?f={urllib.parse.quote(d["path"])}">{html.escape(d["path"])}</a></td>'
                f'<td class="mut">{d["kind"]}</td><td class="n">{d["modified"]}</td>'
                f'<td class="mut">{html.escape(d.get("note", ""))[:40]}</td></tr>' for d in docs[:14])
            P.append('<table><tr><th>document</th><th>kind</th><th>updated</th><th></th></tr>' + rows + '</table>')
        else:
            P.append('<p class="empty">reports, drafts and change files appear here as they are produced '
                     '(<code>report --pdf</code>, <code>draft</code>, <code>control</code>)</p>')
        dl = state.read(cfg, "deliveries", []) or []
        if dl:
            last = dl[-1]
            fb = f' · feedback: “{html.escape((last.get("feedback") or "")[:40])}”' if last.get("feedback") else " · awaiting feedback"
            P.append(f'<p class="mut">last delivery #{last["id"]} ({last["date"]}): '
                     f'{html.escape(", ".join(Path(f).name for f in last["files"])[:60])}{fb}</p>')
    except Exception:
        P.append('<p class="empty">documents unavailable</p>')
    P.append('</div>')

    # Review queue (wide, interactive)
    P.append('<div class="card wide"><h2>Review queue — approve or request changes</h2>')
    if queue:
        rows = []
        for i in queue:
            aid = i["id"]
            rows.append(
                f'<tr><td>{aid}</td><td><span class="pill s-{i["status"]}">{i["status"]}</span></td>'
                f'<td>{html.escape(i["action"][:60])}</td>'
                f'<td class="mut">{html.escape((i.get("feedback") or "")[:40])}</td>'
                f'<td><form class="inl" method="post" action="/approve"><input type="hidden" name="id" value="{aid}">'
                f'<button class="g">Approve</button></form> '
                f'<form class="inl" method="post" action="/changes"><input type="hidden" name="id" value="{aid}">'
                f'<input type="text" name="notes" placeholder="changes…" size="16">'
                f'<button>Request</button></form></td></tr>')
        P.append('<table><tr><th>id</th><th>status</th><th>action</th><th>notes</th><th></th></tr>'
                 + "".join(rows) + '</table>'
                 + '<p class="mut">Approved items ship on the next <code>apply --approved</code> / cycle.</p>')
    else:
        P.append('<p class="empty">nothing awaiting review</p>')
    P.append('</div>')
    head = (f'<header><b>SEO <span class="g">autopilot</span></b> · {site} '
            f'<span class="mut" style="color:#8ea0bd">{html.escape(rep.get("date",""))}</span>'
            f'<form method="post" action="/cycle"><button class="g">▶ Run cycle</button></form></header>')
    return (f'<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">'
            f'<meta http-equiv=refresh content=25><title>SEO autopilot — {site}</title><style>{_CSS}</style>'
            f'{head}<div class="wrap">{"".join(P)}</div>')


_DOC_FILES = ("report.html", "report.pdf", "plan.md", "audit.md", "BASELINE.md", "PLAYBOOK.md",
              "recommendations.md", "digest.md", "consult.md", "article-plan.md")
_DOC_DIRS = ("content", "site-changes", "drafts")
_DOC_KIND = {".pdf": "report (PDF)", ".html": "report (web)", ".md": "document", ".json": "change file"}


def _docs_list(cfg):
    out = []
    root = Path.cwd()
    for f in _DOC_FILES:
        p = root / f
        if p.exists():
            out.append({"path": f, "kind": _DOC_KIND.get(p.suffix, "document"),
                        "modified": time.strftime("%m-%d %H:%M", time.localtime(p.stat().st_mtime))})
    for d in _DOC_DIRS:
        dp = root / d
        if dp.is_dir():
            for p in sorted(dp.iterdir(), key=lambda x: -x.stat().st_mtime)[:6]:
                if p.suffix in (".md", ".json", ".html"):
                    out.append({"path": f"{d}/{p.name}", "kind": "draft" if d == "content" else _DOC_KIND.get(p.suffix, "file"),
                                "modified": time.strftime("%m-%d %H:%M", time.localtime(p.stat().st_mtime)),
                                "note": "awaiting review" if d == "site-changes" else ""})
    out.sort(key=lambda d: d["modified"], reverse=True)
    return out


def _doc_path(f):
    """Whitelist + traversal guard for /doc — only known files/dirs under the workspace."""
    if not f or f.startswith(("/", "~")) or ".." in f or "\\" in f:
        return None
    parts = Path(f).parts
    ok = (f in _DOC_FILES) or (len(parts) == 2 and parts[0] in _DOC_DIRS
                               and Path(f).suffix in (".md", ".json", ".html"))
    if not ok:
        return None
    p = (Path.cwd() / f).resolve()
    if Path.cwd().resolve() not in p.parents or not p.exists():
        return None
    return p


def _make_handler(cfg):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body, ctype="text/html", code=200):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body.encode() if isinstance(body, str) else body)

        def do_GET(self):
            if self.path.startswith("/api/state"):
                self._send(json.dumps(state.summary(cfg), indent=1), "application/json")
            elif self.path.startswith("/doc"):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                p = _doc_path((q.get("f") or [""])[0])
                if not p:
                    self._send("<p>not found</p>", code=404)
                elif p.suffix == ".pdf":
                    self._send(p.read_bytes(), "application/pdf")
                elif p.suffix == ".html":
                    self._send(p.read_text(errors="ignore"))
                else:  # md / json — readable, styled, back-linked
                    body = html.escape(p.read_text(errors="ignore"))
                    self._send(f'<!doctype html><meta charset=utf-8><title>{html.escape(p.name)}</title>'
                               f'<style>{_CSS}</style><div class="wrap" style="grid-template-columns:1fr">'
                               f'<div class="card wide"><h2><a href="/">← dashboard</a> · {html.escape(p.name)}</h2>'
                               f'<pre style="white-space:pre-wrap;font-size:13px">{body}</pre></div></div>')
            else:
                self._send(_page(cfg))

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            form = urllib.parse.parse_qs(self.rfile.read(n).decode())
            g = lambda k: (form.get(k) or [""])[0]
            _CACHE.clear()  # any action can change setup/practices state — refresh next render
            if self.path == "/approve":
                review.respond(cfg, int(g("id")), "approve")
            elif self.path == "/changes":
                review.respond(cfg, int(g("id")), "changes", g("notes"))
            elif self.path == "/cycle":
                autopilot.cycle(cfg, deliver=False)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
    return H


def serve(cfg, port=8787, open_browser=True):
    httpd = HTTPServer(("127.0.0.1", port), _make_handler(cfg))
    url = f"http://127.0.0.1:{port}"
    print(f"SEO autopilot dashboard → {url}   (Ctrl-C to stop)")
    if open_browser:  # the hand-holding default: the web page opens and guides you
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
