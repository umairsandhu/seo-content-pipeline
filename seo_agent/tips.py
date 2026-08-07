"""SEO tidbits — the tool teaches while it works. One sourced, genuinely
interesting fact per day, surfaced after commands, on the dashboard, and in
digests. Context-aware (an audit gets a technical tip, a draft gets a content
tip), never more than one per day per machine, and every tip names its source —
no folklore.

STANDING RULE: when a new talk / study / article teaches the operator something
(like the SparkToro zero-click talk that seeded half this library), distill it
into TIPS here — same day, with the source. The library is part of the learning
loop. Off switch: `"tips": false` in config or SEO_TIPS=0. Stdlib only."""
import datetime
import json
import os
from pathlib import Path

# tags: technical · content · geo · measurement · social · strategy
TIPS = [
    # ── from the SparkToro zero-click talk / studies ─────────────────────────
    {"text": "~58% of US Google searches end without a click, and only ~374 of every 1,000 "
             "send someone to the open web. Being SEEN in the results is now its own channel — "
             "that's why `citability` and `zeroclick` exist.",
     "source": "SparkToro/Datos 2024 Zero-Click Search Study (sparktoro.com/blog)", "tags": ["measurement", "geo"]},
    {"text": "Impressions up while clicks fall — the 'alligator graph' — is a structural web "
             "shift, not a problem with your content. Measure branded demand and AI citations, "
             "not just traffic (`zeroclick` shows your alligator).",
     "source": "SparkToro, State of Search Q4 2025 (sparktoro.com)", "tags": ["measurement"]},
    {"text": "97.3% of the most-viewed Facebook posts contain no outbound link, and no-link posts "
             "reach ~10× further across social platforms. Publish standalone value in the feed; "
             "put the link in the first comment (`repurpose <url>` drafts these).",
     "source": "Meta Widely Viewed Content Reports, 2021–2025 · SparkToro", "tags": ["social", "content"]},
    {"text": "HubSpot's organic traffic dropped ~80% after AI Overviews — and revenue hit an "
             "all-time high the same quarter. Traffic and revenue are not the same thing; judge "
             "content by its job, not its clicks.",
     "source": "HubSpot Q4 2025 earnings, via SparkToro/MicroConf", "tags": ["measurement", "strategy"]},
    {"text": "Dropbox ran month-long ad-channel blackouts: channels reporting 1.5–2.0× attributed "
             "ROAS measured 0.7–0.9× CAUSAL ROAS — platforms overclaim 2–10×. Holdout comparison "
             "(what our ledger does) is the honest measurement.",
     "source": "Dropbox incrementality study, peer-reviewed (ACM EC)", "tags": ["measurement"]},
    {"text": "100% of traffic from TikTok, Slack, Discord, and WhatsApp shows up in analytics as "
             "'direct' — dark social is invisible. If a Slack share converts, Google gets the "
             "credit. Correlate leading indicators over time instead of trusting attribution.",
     "source": "SparkToro dark-social experiment, 1,100 tracked visits", "tags": ["measurement"]},
    {"text": "Reddit outranks every vendor simultaneously on 50–66% of shared B2B SaaS keywords — "
             "and its advantage grows as queries get longer. Buyers form opinions in threads "
             "before they ever see your site (`brief` flags UGC-dominated SERPs).",
     "source": "Ross Simmonds / Foundation Inc. B2B SERP analysis", "tags": ["strategy", "content"]},
    {"text": "One negative review theme appeared 67× in one brand's AI-answer outputs — AI systems "
             "amplify sparse data into 'trends'. Publishing real counter-data displaced it after "
             "~2 citations, but it crept back without regular refreshes.",
     "source": "Wil Reynolds / Seer Interactive", "tags": ["geo", "strategy"]},
    {"text": "Email open rates have been stable for 20 years (30% in 2005, 34% in 2024). It's the "
             "one channel no algorithm can throttle — every rented-land effort should feed a list "
             "you own.",
     "source": "SparkToro / industry email benchmarks", "tags": ["strategy"]},
    {"text": "The zero-click content ratio: about 5 value 'deposits' (no-link, standalone-value "
             "posts) for every 1 'withdrawal' (a CTA). Earn the goodwill, then spend it sparingly.",
     "source": "Amanda Natividad, SparkToro (zero-click marketing)", "tags": ["social", "content"]},
    {"text": "On LinkedIn, plain-text posts routinely out-reach embedded video ~8–10×, posting "
             "twice within 24h throttles the earlier post, and ~3 posts/week beats daily. "
             "Personal profiles out-engage company pages — people engage with people.",
     "source": "Amanda Natividad, SparkToro", "tags": ["social"]},
    # ── search + AI answers ──────────────────────────────────────────────────
    {"text": "AI answer engines quote self-contained passages of roughly 40–170 words that lead "
             "with the answer. A direct 40–80-word answer in your first paragraph is the single "
             "highest-leverage edit for AI visibility (`citability` scores every page on this).",
     "source": "Princeton GEO research + observed AI-answer behavior", "tags": ["geo", "content"]},
    {"text": "Google says AI features ride the same core ranking signals — GEO ≈ SEO plus "
             "extractability. You don't need a separate 'AI strategy'; you need liftable passages, "
             "schema, and unblocked AI crawlers.",
     "source": "Google Search Central on AI features", "tags": ["geo"]},
    {"text": "Roughly one in five searches now happens outside traditional search engines — Amazon "
             "~10%, social ~5%, AI tools ~3% and growing fast. 'Search' is a behavior, not one "
             "results page.",
     "source": "SparkToro/Datos, State of Search Q4 2025", "tags": ["strategy"]},
    {"text": "A stale year in a title ('Best X in 2024') depresses CTR even when the page is "
             "fresh — searchers and AI models both read it as outdated. Bump the year only WITH a "
             "real content refresh (the `freshness` audit sweeps for these).",
     "source": "field-tested; encoded in this tool after a 43-title miss (LEARNINGS #23)", "tags": ["content"]},
    # ── technical ────────────────────────────────────────────────────────────
    {"text": "A page that is noindexed AND robots.txt-disallowed can linger in the index forever: "
             "Google can't crawl it, so it never sees the noindex. Pick one signal "
             "(`audit` catches this conflict).",
     "source": "Google Search Central documentation", "tags": ["technical"]},
    {"text": "Titles and meta descriptions are your SERP ad copy: CTR can move 2–3× on the same "
             "ranking. The cheapest traffic you'll ever win is a rewrite of a high-impression, "
             "low-CTR title (`plan` surfaces them from GSC).",
     "source": "GSC CTR-curve analyses, encoded in `ctr`", "tags": ["technical", "content"]},
    {"text": "Core Web Vitals 2026 bars: LCP < 2.5s, INP < 200ms, CLS < 0.1 — at the 75th "
             "percentile of real users, not your fast laptop. Pages sharing a template share "
             "their CWV, so fix templates, not pages (`speed` samples one per template).",
     "source": "Google Search Central / CrUX", "tags": ["technical"]},
    {"text": "Modern link spam is mostly ignored, not punished — Google's SpamBrain neutralizes it "
             "automatically, and disavow files are rarely necessary. Spend the effort earning one "
             "real mention instead (`prospect`).",
     "source": "Google Search Central on SpamBrain", "tags": ["technical"]},
    {"text": "Striking distance beats net-new: queries already ranking 4–20 with real impressions "
             "are your highest-probability wins — Google already considers you relevant. Upgrade "
             "those pages before writing anything new (`plan` ranks them first).",
     "source": "encoded from live-site results (LEARNINGS #10)", "tags": ["strategy", "content"]},
    {"text": "Google indexes the MOBILE rendering of your page, full stop. A missing viewport "
             "meta means Google sees a desktop page squeezed onto a phone (`audit` checks it; "
             "`speed` adds tap-target depth via PSI).",
     "source": "Google Search Central, mobile-first indexing", "tags": ["technical"]},
    {"text": "Publishing scaled, low-value content now risks sitewide demotion, not just those "
             "pages — Google's scaled-content policies target patterns, not URLs. That's why this "
             "tool hard-blocks thin/duplicate drafts at the publish gate.",
     "source": "Google spam policies (scaled content abuse)", "tags": ["content", "technical"]},
    {"text": "Webflow, Ghost, and many themes emit <meta content=… name=…> — attribute order "
             "reversed. Naive parsers report 'missing meta description' on every page. Always "
             "verify a sitewide 'missing X' finding against live HTML before believing it.",
     "source": "encoded in this tool after a 400-page false positive (LEARNINGS #1)", "tags": ["technical"]},
    {"text": "The realistic buyer journey — LinkedIn post → podcast → newsletter → a Slack "
             "mention → branded Google search → convert. Google captures the demand; the four "
             "invisible touches created it. Watch branded search volume as your demand-creation "
             "proxy (`zeroclick` trends it).",
     "source": "Amanda Natividad, SparkToro (MicroConf talk)", "tags": ["measurement", "strategy"]},
]

# command → preferred tags (context-aware pick)
_CONTEXT = {"audit": ["technical"], "sitemap": ["technical"], "speed": ["technical"],
            "schema": ["technical", "geo"], "sitediff": ["technical"],
            "brief": ["content"], "draft": ["content"], "crew": ["content"], "refresh": ["content"],
            "repurpose": ["social", "content"], "citability": ["geo"], "geo": ["geo"],
            "aivis": ["geo"], "entity": ["geo"],
            "gsc": ["measurement"], "learn": ["measurement"], "ledger": ["measurement"],
            "zeroclick": ["measurement"], "ga4": ["measurement"], "report": ["measurement", "strategy"],
            "plan": ["strategy"], "consult": ["strategy"], "onboard": ["strategy"],
            "autopilot": ["strategy", "measurement"]}

_STATE = Path(os.path.expanduser("~/.seo-agent")) / "tips.json"


def _enabled(cfg):
    if os.environ.get("SEO_TIPS", "").lower() in ("0", "false", "off"):
        return False
    return cfg.get("tips", True) is not False


def _state():
    try:
        return json.loads(_STATE.read_text())
    except Exception:
        return {"last": "", "idx": -1}


def pick(cfg=None, context=None, advance=True):
    """Today's tip: rotates through the library machine-wide; prefers tips matching
    the command's context when it's that tip's day-one showing."""
    st = _state()
    today = datetime.date.today().isoformat()
    if st.get("last") == today:
        return TIPS[st.get("idx", 0) % len(TIPS)]  # same tip all day — no slot-machine
    idx = (st.get("idx", -1) + 1) % len(TIPS)
    want = _CONTEXT.get(context or "", [])
    if want:  # nudge forward to the next context-matching tip (bounded scan)
        for off in range(len(TIPS)):
            if set(TIPS[(idx + off) % len(TIPS)]["tags"]) & set(want):
                idx = (idx + off) % len(TIPS)
                break
    if advance:
        try:
            _STATE.parent.mkdir(parents=True, exist_ok=True)
            _STATE.write_text(json.dumps({"last": today, "idx": idx}))
        except Exception:
            pass
    return TIPS[idx]


def maybe(cfg, context=None):
    """One tip per day per machine, rendered — or None (already shown / disabled)."""
    if not _enabled(cfg or {}):
        return None
    if _state().get("last") == datetime.date.today().isoformat():
        return None
    return render(pick(cfg, context))


def render(t):
    return f"💡 {t['text']}\n   — {t['source']}"


def render_md(cfg):
    t = pick(cfg, advance=False)
    return (f"# 💡 Today's SEO tidbit\n\n{t['text']}\n\n_Source: {t['source']}_\n\n"
            f"_{len(TIPS)} sourced tidbits in the library — one per day after commands, on the "
            "dashboard, and in digests. Disable with `\"tips\": false` in config. New talks and "
            "studies feed the library (LEARNINGS loop)._")
