"""Demo mode — the 5-minute, zero-key first run. `python -m seo_agent demo` builds a
complete synthetic workspace (a fictional outdoor-gear blog): a crawled corpus with
realistic flaws, three months of GSC history, a change ledger with measured wins AND
one loss, and a seeded brain — so `start`, `plan`, `practices`, `learn`, and the
dashboard are instantly meaningful with no credentials and no network.

Everything is generated deterministically from today's date; the demo's lesson store
stays inside the demo folder (never touches ~/.seo-agent). When it clicks, point the
real thing at your site: `init --site https://your-site.com` in a fresh folder."""
import datetime
import json
from pathlib import Path

SITE = "https://demo-outdoors.example"
_MARKER = ".seo-demo"

_GOOD = [
    ("best-4-season-tents", "Best 4-Season Tents of {Y} — Tested on 11 Peaks",
     "We pitched 14 tents in 60-mph gusts; 5 survived. Full test data inside."),
    ("hiking-boot-guide", "How Should Hiking Boots Fit? A Boot-Fitter Explains",
     "A certified fitter on sizing, break-in, and the 3 fit checks that prevent blisters."),
    ("layering-system", "What Is the 3-Layer System? (With Gram Weights)",
     "Base, mid, shell — with measured weights and temperature ranges for each combo."),
    ("down-vs-synthetic", "Down vs Synthetic Insulation: Which Is Warmer Wet?",
     "Lab loft-retention numbers after soaking, drying times, and price per warmth unit."),
]
_STALE = ["best-tents-2024", "sleeping-bags-2024", "camp-stoves-2023", "headlamps-2024",
          "rain-jackets-2024", "trekking-poles-2023"]
_THIN = ["gaiters", "tent-stakes", "carabiners"]
_NOMETA = ["water-filters", "first-aid-kits", "bear-canisters", "trail-snacks"]


def _text_good(topic):
    return (f"{topic.replace('-', ' ').title()} — the short answer: after 6 weeks of field testing "
            f"across 11 trips, three models clearly beat the rest, and the best value costs $189. "
            f"Below are the measurements, the failures, and exactly who each pick is for.\n\n"
            f"How did we test?\nWe logged 47 nights, 212 miles, and temperatures from -12°C to 31°C. "
            f"Each item was weighed (to the gram), stress-tested, and scored by 3 testers.\n\n"
            f"Which one should you buy?\n1. The all-rounder — 1,240 g, $189\n2. The ultralight — 890 g, $259\n"
            f"3. The budget pick — 1,610 g, $99\n\nWhat matters most?\n" + "Durability beats weight for most people. " * 40)


def _text_thin(topic):
    return f"{topic.replace('-', ' ').title()} are useful. Here are some thoughts. " * 12


def _corpus():
    today = datetime.date.today()
    C = []
    for slug, title, desc in _GOOD:
        C.append({"url": f"{SITE}/blog/{slug}", "status": 200, "title": title.replace("{Y}", str(today.year)),
                  "description": desc, "h1": [title.replace("{Y}", str(today.year))],
                  "headings": ["How did we test?", "Which one should you buy?", "What matters most?"],
                  "text": _text_good(slug), "lists": 2, "tables": 1, "csr": False})
    for slug in _STALE:
        yr = slug.rsplit("-", 1)[-1]
        name = slug.rsplit("-", 1)[0].replace("-", " ").title()
        C.append({"url": f"{SITE}/blog/{slug}", "status": 200,
                  "title": f"10 Best {name} in {yr} (Buyer's Guide)",
                  "description": f"Our picks for {name.lower()} in {yr}.", "h1": [f"Best {name} in {yr}"],
                  "headings": [f"Top {name} picks"], "text": f"In {yr} we compared 20 {name.lower()}. " * 60,
                  "lists": 1, "tables": 0, "csr": False})
    for slug in _THIN:
        C.append({"url": f"{SITE}/blog/{slug}", "status": 200, "title": f"{slug.replace('-', ' ').title()} Guide",
                  "description": "A quick guide.", "h1": [slug], "headings": [], "text": _text_thin(slug),
                  "lists": 0, "tables": 0, "csr": False})
    for slug in _NOMETA:
        C.append({"url": f"{SITE}/blog/{slug}", "status": 200, "title": f"{slug.replace('-', ' ').title()} — Field Guide",
                  "description": "", "h1": [slug], "headings": ["FAQ"], "text": _text_good(slug),
                  "lists": 1, "tables": 0, "csr": False})
    for c in C:
        c["words"] = len(c["text"].split())
    return C


def build(dirname="seo-demo"):
    from . import brain, history, learn, ledger
    root = Path(dirname).resolve()
    if root.exists() and any(root.iterdir()) and not (root / _MARKER).exists():
        return {"error": f"{root} exists and isn't empty — pick another --dir or delete it"}
    root.mkdir(parents=True, exist_ok=True)
    (root / _MARKER).write_text("generated demo workspace — safe to delete\n")
    today = datetime.date.today()
    D = lambda days_ago: (today - datetime.timedelta(days=days_ago)).isoformat()

    # cfg with absolute paths for seeding; the written config.json uses defaults (relative)
    cfg = {"site": SITE, "history_dir": str(root / "history"), "store_path": str(root / "seo.db"),
           "state_dir": str(root / "state"), "global_lessons_path": str(root / "lessons-local.json")}
    (root / "config.json").write_text(json.dumps({
        "site": SITE, "sitemap": SITE + "/sitemap.xml", "include": ["/blog/"],
        "competitors": ["rivalgear.example"], "autonomy": "approve",
        "brand": {"name": "Demo Outdoors"},
        "learning": {"share_cross_site": False},
        "global_lessons_path": "lessons-local.json",
        "_demo": "synthetic workspace — every number below is generated, not real"}, indent=2) + "\n")
    (root / "corpus.json").write_text(json.dumps(_corpus(), indent=1))

    # 3 months of GSC page history: 2 retitles win, 1 meta win, 1 refresh LOSS, 10-page holdout
    changed = {"best-tents-2024": (40, 40, 55, 85), "hiking-boot-guide": (35, 35, 44, 66),
               "rain-jackets-2024": (25, 25, 34, 49),
               "sleeping-bags-2024": (30, 30, 36, 44), "camp-stoves-2023": (60, 60, 52, 44)}
    def snap(days_ago, idx):
        rows = [{"page": f"{SITE}/blog/{slug}", "clicks": v[idx], "position": 9.0 - idx}
                for slug, v in changed.items()]
        rows += [{"page": f"{SITE}/blog/holdout-{i}", "clicks": 50 + idx, "position": 12.0} for i in range(10)]
        history.snapshot(cfg, "gsc_pages", rows, date=D(days_ago))
    for i, days in enumerate((63, 35, 28, 7)):
        snap(days, i)
    history.snapshot(cfg, "gsc_queries", [
        {"query": "best 4 season tent", "clicks": 130, "impressions": 6200, "ctr": 0.021, "position": 8.9},
        {"query": "down vs synthetic", "clicks": 70, "impressions": 3600, "ctr": 0.019, "position": 11.6},
        {"query": "how should hiking boots fit", "clicks": 50, "impressions": 2700, "ctr": 0.019, "position": 10.1},
        {"query": "demo outdoors", "clicks": 210, "impressions": 1400, "ctr": 0.15, "position": 1.2}],
        date=D(35))
    history.snapshot(cfg, "gsc_queries", [  # impressions surge, clicks lag → the alligator opens
        {"query": "best 4 season tent", "clicks": 120, "impressions": 9800, "ctr": 0.012, "position": 8.4},
        {"query": "down vs synthetic", "clicks": 60, "impressions": 5200, "ctr": 0.011, "position": 11.2},
        {"query": "how should hiking boots fit", "clicks": 45, "impressions": 3900, "ctr": 0.011, "position": 9.8},
        {"query": "demo outdoors", "clicks": 300, "impressions": 2100, "ctr": 0.14, "position": 1.2}],
        date=D(7))

    ledger.record(cfg, f"{SITE}/blog/best-tents-2024", "retitle", "2024 → current year", date=D(35))
    ledger.record(cfg, f"{SITE}/blog/hiking-boot-guide", "retitle", "benefit-led title", date=D(35))
    ledger.record(cfg, f"{SITE}/blog/rain-jackets-2024", "retitle", "2024 → current year", date=D(35))
    ledger.record(cfg, f"{SITE}/blog/sleeping-bags-2024", "update_meta", "meta rewrite", date=D(35))
    ledger.record(cfg, f"{SITE}/blog/camp-stoves-2023", "refresh", "content refresh", date=D(35),
                  before={"title": "Best Camp Stoves in 2023 (Buyer's Guide)",
                          "description": "Our 2023 camp-stove picks."})  # a measured loser → W3 rollback demo

    from . import identity
    identity.scaffold({"site": SITE, "brand": {"name": "Demo Outdoors"}}, root=str(root))
    identity.write_client({**cfg, "site": SITE},
                          {"sells": "premium outdoor gear reviews + affiliate picks",
                           "buyer": "weekend backpackers researching their next purchase",
                           "conversion": "affiliate click-through on a gear pick",
                           "moat": "we actually field-test everything (47 nights logged)",
                           "nogo": "never trash competitors; no medical/survival claims",
                           "capacity": "5"}, root=str(root))
    learn.cycle(cfg)                      # measures +7/+28 follow-ups (holdout-adjusted)
    brain.add(cfg, "preference", "Client feedback on monthly report: love the comparison tables — "
              "keep intros under 3 sentences and always lead with the price-per-warmth numbers",
              source="client-feedback")
    brain.cycle(cfg)                      # distills the retitle playbook from the measured wins
    return {"ok": True, "dir": str(root), "pages": len(_corpus()),
            "measured_changes": 5, "next": f"cd {dirname} && python -m seo_agent start"}


def render_md(r):
    if r.get("error"):
        return f"# Demo\n\n- ⚠ {r['error']}"
    return "\n".join([
        "# Demo workspace ready 🎒  (synthetic data — zero keys, zero network)", "",
        f"- **{r['pages']} pages** crawled corpus (good, stale-year, thin, missing-meta — like a real site)",
        f"- **3 months of search history** + **{r['measured_changes']} measured changes** "
        "(3 statistically qualified wins, 1 modest, 1 honest loss — holdout-adjusted, CI-checked)",
        "- **A learned playbook + client taste** already in the brain", "",
        "## Do this now",
        f"```\n{r['next']}\n```",
        "The dashboard opens: the guide shows what a real setup needs, **Best practices** shows "
        "found→fixed→measured with numbers, **Learning** shows day/week impact, and `plan` ranks "
        "what to do next. Poke `practices`, `learn`, `brain`, `plan`, `audit` — then point it at "
        "your real site: `init --site https://your-site.com` in a fresh folder."])
