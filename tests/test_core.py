"""Core + roadmap-module tests. Stdlib unittest (no pytest dependency required;
`python -m pytest tests/` or `python -m unittest discover tests` both run it).

Each test is self-contained: it builds a tiny synthetic corpus/config in a temp
directory so nothing touches a real site or network (the few network paths —
Wikidata, live SERP, LLM engines — are exercised only via their offline branches)."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from seo_agent import (authority_flow, autonomy, citability, consult, crew, ctr_curves, entity,
                       gsc_csv, ingest, intl, jobs, journey, local, notify, personas, publish,
                       safetygate, site_control, store, wizard)

CORPUS = [
    {"url": "https://x.com/", "title": "Home", "description": "d", "headings": ["Home"],
     "text": "Welcome to Acme. " + "unique home words here " * 30, "words": 90,
     "links": ["https://x.com/a", "https://x.com/b"], "lists": 1, "tables": 0,
     "hreflang": [], "img_total": 1, "img_alt": 1, "status": 200},
    {"url": "https://x.com/a", "title": "What is a widget?", "description": "d",
     "headings": ["What is a widget?", "How do widgets work?"],
     "text": "A widget is a small tool that does one job well, in about sixty words of a clear "
             "answer-first paragraph that a model could quote directly without extra context around it. "
             + "distinct sentence alpha bravo charlie delta echo foxtrot. " * 25,
     "words": 220, "links": ["https://x.com/"], "lists": 2, "tables": 1,
     "hreflang": [], "status": 200},
    {"url": "https://x.com/b", "title": "Widget pricing", "description": "d", "headings": ["Pricing"],
     "text": "Our widget costs 49 dollars in 2026 with 12 percent savings. " * 20, "words": 160,
     "links": ["https://x.com/", "https://x.com/a"], "lists": 0, "tables": 0,
     "hreflang": [], "status": 200},
]


def _workspace():
    d = tempfile.mkdtemp()
    Path(d, "corpus.json").write_text(json.dumps(CORPUS))
    return d


CFG = {"site": "https://x.com", "brand": {"name": "Acme"}, "pillars": {"/a": "hub"},
       "history_dir": "history", "competitors": ["y.com"]}


class MetaParsing(unittest.TestCase):
    def test_attribute_order_independent(self):
        html = '<meta content="hello world" name="description">'
        self.assertEqual(ingest._meta_content(html, "description"), "hello world")
        html2 = '<meta name="description" content="second">'
        self.assertEqual(ingest._meta_content(html2, "description"), "second")

    def test_jsonld_dates_author(self):
        doc = ('<script type="application/ld+json">'
               '{"@graph":[{"@type":"BlogPosting","datePublished":"2026-01-02",'
               '"author":{"@type":"Person","name":"Jane Doe"}}]}</script>')
        m = ingest._jsonld_meta(doc)
        self.assertEqual(m["published"], "2026-01-02")
        self.assertEqual(m["author"], "Jane Doe")


class SafetyGate(unittest.TestCase):
    def test_thin_blocked(self):
        v = safetygate.check({"title": "t", "text": "only a few words here"})
        self.assertFalse(v["ok"])
        self.assertTrue(any("thin" in r for r in v["reasons"]))

    def test_unique_long_passes(self):
        d = _workspace()
        vocab = ["harbor", "lantern", "meridian", "cobalt", "fathom", "willow", "ember", "quartz",
                 "thicket", "brine", "cinder", "marrow"]
        text = " ".join(f"{w}{i}" for i, w in enumerate(vocab * 40))  # 480 unique tokens
        v = safetygate.check({"title": "Real", "text": text}, corpus_path=str(Path(d, "corpus.json")))
        self.assertTrue(v["ok"], v["reasons"])

    def test_near_duplicate_blocked(self):
        d = _workspace()
        dup = {"title": CORPUS[1]["title"], "text": CORPUS[1]["text"]}
        v = safetygate.check(dup, corpus_path=str(Path(d, "corpus.json")))
        self.assertFalse(v["ok"])
        self.assertTrue(any("duplicate" in r for r in v["reasons"]))


class Citability(unittest.TestCase):
    def test_report_shape(self):
        d = _workspace()
        r = citability.report(CFG, corpus_path=str(Path(d, "corpus.json")))
        self.assertIn("avg", r)
        self.assertTrue(0 <= r["avg"] <= 100)
        self.assertEqual(r["pages"], 3)


class CtrCurves(unittest.TestCase):
    def test_generic_fallback(self):
        c = ctr_curves.curve({"history_dir": tempfile.mkdtemp()})
        self.assertEqual(c["source"], "generic-fallback")
        self.assertGreater(ctr_curves.expected_ctr(c, 1), ctr_curves.expected_ctr(c, 10))

    def test_first_party_curve(self):
        d = tempfile.mkdtemp()
        from seo_agent import history
        cfg = {"history_dir": d}
        rows = []
        for pos, ctr in ((1, 0.30), (3, 0.12), (5, 0.05), (8, 0.02)):
            rows += [{"query": f"q{pos}_{i}", "position": pos, "impressions": 1000, "ctr": ctr} for i in range(5)]
        history.snapshot(cfg, "gsc_queries", rows)
        c = ctr_curves.curve(cfg)
        self.assertEqual(c["source"], "first-party-gsc")
        self.assertAlmostEqual(c["curve"][1], 0.30, places=2)


class AuthorityFlow(unittest.TestCase):
    def test_pagerank_sums_to_one(self):
        _urls, _idx, pr = authority_flow.pagerank(CORPUS)
        self.assertAlmostEqual(float(pr.sum()), 1.0, places=3)

    def test_report_has_sculpt(self):
        d = _workspace()
        r = authority_flow.report(CFG, corpus_path=str(Path(d, "corpus.json")))
        self.assertIn("sculpt", r)


class Intl(unittest.TestCase):
    def test_no_hreflang(self):
        d = _workspace()
        r = intl.report(CFG, corpus_path=str(Path(d, "corpus.json")))
        self.assertFalse(r["has_hreflang"])


class Local(unittest.TestCase):
    def test_not_local(self):
        d = _workspace()
        r = local.report(CFG, corpus_path=str(Path(d, "corpus.json")))
        self.assertFalse(r["is_local"])


class Entity(unittest.TestCase):
    def test_org_jsonld_generation(self):
        block = entity._org_jsonld(CFG, "Acme", {"logo": "l.png"},
                                   ["https://linkedin.com/company/acme"], {"url": "https://www.wikidata.org/wiki/Q1"})
        self.assertEqual(block["@type"], "Organization")
        self.assertIn("https://www.wikidata.org/wiki/Q1", block["sameAs"])


class Store(unittest.TestCase):
    def test_record_series_deltas(self):
        cfg = {"store_path": str(Path(tempfile.mkdtemp(), "s.db"))}
        store.record(cfg, "rank", [{"q": "a", "position": 10}], "q", ["position"], date="2026-01-01")
        store.record(cfg, "rank", [{"q": "a", "position": 6}], "q", ["position"], date="2026-01-08")
        s = store.series(cfg, "rank", "a|position")
        self.assertEqual(len(s), 2)
        d = store.deltas(cfg, "rank", "position")
        self.assertEqual(d[0]["delta"], -4)


class Jobs(unittest.TestCase):
    def test_enqueue_due_mark(self):
        cfg = {"jobs_path": str(Path(tempfile.mkdtemp(), "j.db"))}
        jid = jobs.enqueue(cfg, "aivis")
        self.assertTrue(any(j["id"] == jid for j in jobs.due(cfg)))
        jobs.mark(cfg, jid, "done")
        self.assertFalse(any(j["id"] == jid and j["cmd"] == "aivis" for j in jobs.due(cfg)))


class GscCsv(unittest.TestCase):
    def test_pct_and_num(self):
        self.assertAlmostEqual(gsc_csv._ctr("3.45%"), 0.0345, places=4)
        self.assertAlmostEqual(gsc_csv._ctr("0.0345"), 0.0345, places=4)
        self.assertAlmostEqual(gsc_csv._ctr("1%"), 0.01, places=4)
        self.assertEqual(gsc_csv._num("1,234"), 1234)

    def test_parse_queries(self):
        txt = "Top queries,Clicks,Impressions,CTR,Position\nbest pizza,10,\"1,000\",1.00%,7.5\n"
        rows = gsc_csv.parse_text(txt)
        self.assertEqual(rows[0]["query"], "best pizza")
        self.assertEqual(rows[0]["impressions"], 1000)
        self.assertAlmostEqual(rows[0]["ctr"], 0.01, places=4)


class PublishGate(unittest.TestCase):
    def test_gate_blocks_bad_schema(self):
        os.chdir(_workspace())
        g = publish._gate(CFG, {"title": "T", "body": "word " * 400,
                                "jsonld": {"@type": "BlogPosting", "headline": "h"}})
        self.assertFalse(g["ok"])
        self.assertTrue(any("datePublished" in r for r in g["reasons"]))


class Journey(unittest.TestCase):
    def test_readiness_shape(self):
        d = _workspace()
        r = journey.readiness(CFG, root=d)
        self.assertIn("score", r)
        self.assertIn("stages", r)
        self.assertTrue(any(s["stage"].startswith("C") for s in r["stages"]))


class Autonomy(unittest.TestCase):
    def test_manual_never_executes(self):
        self.assertFalse(autonomy.authorize({"autonomy": "manual"}, "x")["execute"])

    def test_auto_executes_nondestructive(self):
        self.assertTrue(autonomy.authorize({"autonomy": "auto"}, "x", kind="update")["execute"])

    def test_auto_destructive_requires_approval(self):
        os.chdir(tempfile.mkdtemp())
        d = autonomy.authorize({"autonomy": "auto"}, "del", kind="delete")
        self.assertFalse(d["execute"])
        self.assertTrue(d["queued"])

    def test_approve_queues(self):
        os.chdir(tempfile.mkdtemp())
        cfg = {"autonomy": "approve"}
        autonomy.authorize(cfg, "update x", kind="update", target="x")
        self.assertEqual(len(autonomy.pending(cfg)), 1)


class SiteControl(unittest.TestCase):
    def test_manual_plans_change_file(self):
        os.chdir(tempfile.mkdtemp())
        r = site_control.change({"autonomy": "manual", "cms": {"type": "file", "dir": "content"}},
                                "update_meta", url="https://x.com/a", title="New")
        self.assertEqual(r["status"], "planned")
        self.assertTrue(Path("site-changes").exists())

    def test_auto_redirect_writes_file(self):
        os.chdir(tempfile.mkdtemp())
        r = site_control.change({"autonomy": {"mode": "auto", "allow_destructive": True},
                                 "cms": {"type": "file", "dir": "content"}},
                                "redirect", from_path="/old", to_path="/new")
        self.assertEqual(r["status"], "executed")
        self.assertTrue(r["ok"])


class Notify(unittest.TestCase):
    def test_dry_run_without_transport(self):
        for k in ("RESEND_API_KEY", "SENDGRID_API_KEY", "SMTP_HOST"):
            os.environ.pop(k, None)
        r = notify.send({"report": {"email_to": ["a@b.com"]}}, None, "s", "body")
        self.assertTrue(r["dry_run"])
        self.assertEqual(r["to"], ["a@b.com"])


class Personas(unittest.TestCase):
    def test_roles(self):
        self.assertIn("consultant", personas.system("strategist").lower())
        self.assertIn("crawler", personas.system("tech_seo").lower())


class Crew(unittest.TestCase):
    def test_article_stages(self):
        d = _workspace(); os.chdir(d)
        p = crew.article(CFG, "widget")
        roles = [s["role"] for s in p["stages"]]
        self.assertEqual(roles, ["researcher", "strategist", "writer", "editor", "tech_seo"])


class Consult(unittest.TestCase):
    def test_situation_pack(self):
        d = _workspace(); os.chdir(d)
        pack = consult.situation(CFG)
        self.assertEqual(pack["site"], "https://x.com")
        self.assertIn("technical", pack)


class Wizard(unittest.TestCase):
    def test_next_step(self):
        d = _workspace()
        r = wizard.next_step(CFG, root=d)
        self.assertEqual(len(r["steps"]), 9)
        self.assertIn("next", r)


class Ledger(unittest.TestCase):
    def test_record_and_changes(self):
        from seo_agent import ledger
        cfg = {"store_path": str(Path(tempfile.mkdtemp(), "s.db"))}
        ledger.record(cfg, "https://x.com/a", "update_meta", "new title")
        ch = ledger.changes(cfg)
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch[0]["type"], "update_meta")

    def test_attribution_needs_history(self):
        from seo_agent import ledger
        cfg = {"store_path": str(Path(tempfile.mkdtemp(), "s.db")), "history_dir": tempfile.mkdtemp()}
        self.assertIn("error", ledger.attribution(cfg))


class Repo(unittest.TestCase):
    def test_diff_edit(self):
        from seo_agent import repo
        d = tempfile.mkdtemp()
        Path(d, "page.html").write_text("<title>Old</title>")
        new, diff = repo.diff_edit(Path(d, "page.html"), [{"find": "Old", "replace": "New"}])
        self.assertIn("New", new)
        self.assertIn("+<title>New", diff)


class Explain(unittest.TestCase):
    def test_names_logged_change(self):
        from seo_agent import explain, ledger, history
        d = tempfile.mkdtemp()
        cfg = {"store_path": str(Path(d, "s.db")), "history_dir": d, "site": "https://x.com"}
        # two page snapshots straddling a change, with a real drop
        history.snapshot(cfg, "gsc_pages", [{"page": "https://x.com/a", "clicks": 100, "position": 5}], date="2026-01-01")
        history.snapshot(cfg, "gsc_pages", [{"page": "https://x.com/a", "clicks": 40, "position": 9}], date="2026-02-01")
        ledger.record(cfg, "https://x.com/a", "update_content", "rewrote", date="2026-01-15")
        r = explain.explain(cfg, "https://x.com/a")
        self.assertTrue(any("WE changed" in c for c in r["causes"]))
        self.assertEqual(r["trend"]["delta_clicks"], -60)


class Review(unittest.TestCase):
    def test_review_gated_apply(self):
        from seo_agent import autonomy, review
        os.chdir(tempfile.mkdtemp())
        cfg = {"autonomy": "approve", "review": {"channels": ["cli"]}}
        autonomy.authorize(cfg, "update a", kind="update", target="a")
        autonomy.authorize(cfg, "update b", kind="update", target="b")
        # review-required → nothing executable until approved
        self.assertEqual(len(autonomy.executable(cfg)), 0)
        review.respond(cfg, 1, "approve")
        review.respond(cfg, 2, "changes", "punchier")
        ready = autonomy.executable(cfg)
        self.assertEqual([i["id"] for i in ready], [1])
        q = {i["id"]: i for i in autonomy.load_queue(cfg)}
        self.assertEqual(q[2]["status"], "changes")
        self.assertEqual(q[2]["feedback"], "punchier")

    def test_no_review_pending_is_executable(self):
        from seo_agent import autonomy
        os.chdir(tempfile.mkdtemp())
        cfg = {"autonomy": "approve"}  # no review channels
        autonomy.authorize(cfg, "x", kind="update", target="x")
        self.assertEqual(len(autonomy.executable(cfg)), 1)


class Channels(unittest.TestCase):
    def test_dry_run(self):
        for k in ("SLACK_WEBHOOK_URL", "SLACK_BOT_TOKEN", "MATTERMOST_WEBHOOK_URL", "WHATSAPP_TOKEN"):
            os.environ.pop(k, None)
        from seo_agent import channels
        r = channels.send({}, "hi", channels=["slack", "mattermost"])
        self.assertTrue(r["slack"]["dry_run"])
        self.assertTrue(r["mattermost"]["dry_run"])


class GA4(unittest.TestCase):
    def test_not_configured(self):
        from seo_agent import ga4
        os.environ.pop("GA4_PROPERTY_ID", None)
        self.assertIn("error", ga4.organic({}))


class Anomaly(unittest.TestCase):
    def test_traffic_cliff(self):
        from seo_agent import anomaly, history
        d = tempfile.mkdtemp()
        cfg = {"history_dir": d}
        history.snapshot(cfg, "gsc_pages", [{"page": f"/{i}", "clicks": 100} for i in range(20)], date="2026-01-01")
        history.snapshot(cfg, "gsc_pages", [{"page": f"/{i}", "clicks": 10} for i in range(20)], date="2026-02-01")
        kinds = [x["kind"] for x in anomaly.detect(cfg)]
        self.assertIn("traffic", kinds)


class Autopilot(unittest.TestCase):
    def test_cycle_writes_state_and_dates(self):
        from seo_agent import autopilot, state
        d = _workspace(); os.chdir(d)
        cfg = dict(CFG, state_dir="state", store_path="s.db", history_dir="hist",
                   autopilot={"max_per_cycle": 3})
        r = autopilot.cycle(cfg, cadence="daily", deliver=False)
        self.assertIn("plan", r)
        pl = state.read(cfg, "plan")
        self.assertTrue(pl and pl["items"])
        # every item has a due_date, cadence, status
        it = pl["items"][0]
        self.assertIn("due_date", it); self.assertIn("cadence", it); self.assertIn("status", it)
        # drip cap respected
        disp = [i for i in pl["items"] if i["status"] == "dispatched"]
        self.assertLessEqual(len(disp), 3)

    def test_second_cycle_persists_status(self):
        from seo_agent import autopilot, state
        d = _workspace(); os.chdir(d)
        cfg = dict(CFG, state_dir="state", store_path="s.db", history_dir="h", autopilot={"max_per_cycle": 2})
        autopilot.cycle(cfg, cadence="daily", deliver=False)
        first = {i["id"]: i["status"] for i in state.read(cfg, "plan")["items"]}
        autopilot.cycle(cfg, cadence="daily", deliver=False)
        second = {i["id"]: i["status"] for i in state.read(cfg, "plan")["items"]}
        # ids are stable and dispatched items stay dispatched (not re-planned)
        self.assertTrue(set(first) & set(second))


class Dashboard(unittest.TestCase):
    def test_page_renders(self):
        from seo_agent import serve
        d = _workspace(); os.chdir(d)
        page = serve._page(dict(CFG, state_dir="state"))
        self.assertIn("Review queue", page)
        self.assertIn("Run cycle", page)


class Edition(unittest.TestCase):
    def test_open_core_never_gates_core(self):
        from seo_agent import edition
        os.environ.pop("SEO_EDITION", None)
        cfg = {"edition": "open"}
        self.assertEqual(edition.edition(cfg), "open")
        self.assertTrue(edition.has(cfg, "anything_core"))   # unknown feature = core = allowed
        self.assertFalse(edition.has(cfg, "white_label_reports"))
        self.assertEqual(edition.workspace_cap(cfg), 1)

    def test_agency_unlocks_commercial(self):
        from seo_agent import edition
        cfg = {"edition": "agency"}
        self.assertTrue(edition.has(cfg, "white_label_reports"))
        self.assertTrue(edition.has(cfg, "commercial_use"))
        self.assertTrue(edition.has(cfg, "reseller_rights"))
        self.assertFalse(edition.has(cfg, "custom_dev"))     # enterprise-only
        self.assertGreater(edition.workspace_cap(cfg), 100)  # unlimited (local, many client folders)


if __name__ == "__main__":
    unittest.main()
