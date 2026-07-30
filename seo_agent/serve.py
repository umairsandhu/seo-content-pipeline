"""Local dashboard — a single glass pane over the shared state the autopilot agents
write. Serves a live web page (stdlib `http.server`, zero deps) with the Situation,
Plan (dated), Execution, Review queue, and Ledger panels. Humans approve or request
changes inline (posts to the same autonomy/review queue the CLI uses), and can trigger a
cycle. Local by default (127.0.0.1). Site-agnostic."""
import html
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import autonomy, autopilot, ledger, review, state

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


def _make_handler(cfg):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body, ctype="text/html", code=200):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body.encode())

        def do_GET(self):
            if self.path.startswith("/api/state"):
                self._send(json.dumps(state.summary(cfg), indent=1), "application/json")
            else:
                self._send(_page(cfg))

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            form = urllib.parse.parse_qs(self.rfile.read(n).decode())
            g = lambda k: (form.get(k) or [""])[0]
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


def serve(cfg, port=8787):
    httpd = HTTPServer(("127.0.0.1", port), _make_handler(cfg))
    print(f"SEO autopilot dashboard → http://127.0.0.1:{port}   (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
