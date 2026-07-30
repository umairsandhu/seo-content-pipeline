# Learnings — field notes that make the tool sharper

Hard-won lessons from running the pipeline on real sites. Each entry is a rule the
code now encodes (or that the driving agent should follow). Add to this file every
time a real run surprises you — it is the tool's growing "muscle memory."

---

## Parsing & ingestion gotchas (encoded in `ingest.py`)

**1. Meta attribute order is not guaranteed — match by key, not position.**
Webflow, Ghost, and many Wix/Squarespace themes emit `<meta content="…" name="description">`
(content *before* name). A naive `name=…content=…` regex silently returns empty and the
audit reports a false *"missing meta description"* on every page. On the first real run
(Trellus, Webflow) this produced **400/400 false positives**.
→ `_meta_content()` parses each `<meta>` tag's attributes into a dict and matches by
`name`/`property` regardless of order. Applies to description, robots, author, and OG tags.

**2. Dates & authors often live in JSON-LD, not OG meta.**
Webflow/Ghost/most modern CMSs put `datePublished` / `dateModified` / `author` inside the
`Article`/`BlogPosting` schema, and emit **no** `article:published_time` OG tag. Reading only
OG meta makes `eeat`/`geo` under-count dated + authored pages (Trellus: a false *"no date on
400/400"* while every page was in fact dated in JSON-LD).
→ `_jsonld_meta()` flattens `@graph`, finds the Article-like node, and fills
`published`/`modified`/`author` when OG meta is absent. **JSON-LD is a first-class signal
source — always check it before declaring a signal missing.**

**3. A "broken" signal can still be a real finding.** On Trellus the JSON-LD author node
existed but had `name: ""` and a generic `/author/` URL — a genuine E-E-A-T defect (visible
byline, empty structured data). Distinguish *absent* from *present-but-empty* and report the
latter as a fixable finding, not a parser miss.

## Scope gotchas (encoded in `eeat.py`)

**4. Sitewide signals must scan the sitemap, not just the content corpus.**
The corpus is `include`-prefixed (e.g. `/post/`, `/learning-center/`), so site-root trust
pages (`/about-us`, `/security`, `/privacy-policy`, `/terms`) aren't in it. Checking trust
pages against the corpus alone falsely reports them missing.
→ `eeat.report()` now unions corpus paths with `ingest.sitemap_urls()`. General rule: any
*sitewide* check (trust pages, nav, hreflang, brand entity) should look at the whole sitemap.

## Rendering

**5. Confirm server-rendered vs. client-rendered before trusting emptiness.** SPA shells look
like "empty" pages. The corpus stores a `csr` heuristic; if a site's pages look thin, check
`csr` and enable `render.enabled` (Playwright) before reporting missing content. (Trellus was
server-rendered Webflow — static HTML had real content — so no render was needed.)

---

## Analysis methodology (the playbook that worked)

**6. Validate the tool against live HTML before reporting.** The audit is a first pass, not
gospel. Spot-check the highest-severity findings with a live fetch — this is exactly what
caught the false 400/400 meta and confirmed the 4 genuinely-empty `<title>` tags. **Never
ship a headline number you haven't verified on ≥1 real page.**

**7. Segment GSC traffic before interpreting it — % of clicks lies.** Split queries into
**branded / off-ICP / commercial** buckets. Trellus looked like a 108K-clicks/mo success, but
it was **58% branded + 36% off-ICP** (a "public phone number directory" page = 45% of all
clicks) and only **3% commercial**. The product's actual money content was a rounding error in
the totals. Always ask *"is this traffic our ICP?"* before celebrating volume.

**8. Diagnose content-rich vs. link-poor.** Compare *ranking-keyword count* vs. *referring
domains* vs. competitors. Trellus ranked for 8–11× more keywords than any competitor but had
the fewest referring domains → the ceiling is **authority, not content**. This flips the
recommendation from "write more" to "consolidate + earn links."

**9. Low difficulty + stuck on page 2 = the problem is on-site.** When keyword difficulty is
0–30 yet pages sit at position 10–40, competition isn't the constraint — cannibalization,
orphan pages, thin/split content and multi-H1 are. Fix the site before blaming the SERP.

**10. Striking-distance beats net-new.** The highest-probability wins are terms already at
position 8–20 with real impressions — Google already considers the site relevant. Rank
recommendations: **striking-distance upgrades → consolidation of cannibalized clusters →
genuine gaps → net-new.** Piling thin posts onto a site that already has hundreds deepens the
problem.

**11. Map every target keyword to an existing page before recommending.** Decide *upgrade vs.
rewrite vs. consolidate vs. write-new* per term. On a 740-page site, most "articles to write"
are really "pages to merge and strengthen."

**12. GSC is the demand signal; DataForSEO is the difficulty/market signal.** For "what can we
rank," GSC impressions + current position are stronger than volume estimates. Use DataForSEO
to add absolute volume, **keyword difficulty**, CPC (commercial value), and the competitor
content/backlink gap. Blend, don't pick one.

## Operating with paid APIs

**13. DataForSEO bills per call — dump raw responses to disk *before* parsing.** A parse bug
must never force a re-bill. On the first live run a low balance ($1) meant every call counted;
saving `_raw_*.json` first let us re-parse for free. Report cost + remaining balance after
each batch, and prefer bulk endpoints (one call, many targets/keywords).

**14. Result-schema shapes differ per endpoint.** `search_volume/live` returns a flat `result`
list; `bulk_keyword_difficulty/live` nests items under `result[0].items`. Inspect
`result[0].keys()` on first use rather than assuming.

## No-API fallbacks (make the tool work for everyone)

**15. Not every client can grant GSC service-account access.** Many can export a CSV / Google
Sheet. `gsc --csv <path|dir|zip>` imports the standard Performance export (Queries + Pages,
CTR as `3.4%`, comma-thousands), normalizes to the pipeline schema, snapshots to `history/`,
and a fallback in `analyze.gsc_raw` lights up the whole pipeline (striking-distance, low-CTR,
decay) with no API. A Google-Sheet share link works too (export the workbook → xlsx → tabs).

## Deliverables

**16. Reports ship as HTML *and* PDF.** `report --pdf` renders via headless Chrome/Chromium/
Edge (auto-detected, degrades to "open the HTML and Print" if none found). For a shareable
link, inline every asset (logo as inlined SVG / data-URI) — external assets are blocked in
hardened viewers and break the PDF's portability.

## The learning loop (a standing rule — never skip)

**17. Measure every change's impact at day / week / month, and never forget what worked.**
This is encoded, not optional: `ledger.follow_up` computes each logged change's holdout-adjusted
lift at **+7 / +28 / +90 days** from the GSC page snapshots; `learn` aggregates that by *change
type* into a "what works best" playbook; and **`learn.cycle` runs automatically inside every
`autopilot` and `run` cycle** — so the follow-up + learning happen without anyone remembering to.
`plan` then recommends *doing more of* the change types with the best proven track record.

**18. Learning compounds across every site — anonymously.** `learn.update_global` contributes
this site's per-(change-type × horizon) aggregates to a cross-site store
(`~/.seo-agent/lessons.json`, override with `global_lessons_path` / `SEO_GLOBAL_LESSONS`), keyed
by a **hash of the domain** — only aggregate lift stats, no URLs, content, or domains in the
clear. A brand-new client **cold-starts** from what worked on every prior site
(`learn.ranking` falls back to the global store when local evidence is thin). One tool, many
sites, one growing brain — privacy-safe.

**19. Attribution needs the snapshot cadence.** Follow-ups only fill in as `gsc` snapshots
accumulate across the horizons. Run `gsc` (or `gsc --csv`) on a schedule; the day/week/month
cells populate as time passes after a change is logged. If a horizon is blank, it's "not yet
measurable," not "no effect."

**20. The brain closes the loop Hermes-style (observe → distill → reuse → refine).** Modeled
on Nous Research's Hermes Agent (memory + auto-distilled skills + user modeling — no weight
updates, just context that compounds): `brain.cycle` runs inside every autopilot/run/review
cycle, distilling review notes + client replies into **taste** (preferences), measured
outcomes into **proven playbooks**, and negative outcomes into **avoid lessons** — then
injects the top entries into every Writer/Strategist prompt (`personas.system(role, cfg)`).
Never build a generation path that bypasses `personas.system(...,cfg)` — that's how learned
taste reaches the output.

**21. Deliver → reply → taste is how you learn how a client works.** Every deliverable goes
out via `deliver` (email and/or their Google Drive folder) and is logged; every reply
(`feedback "…"`, or an email starting `FEEDBACK` caught by `review --poll`) attaches to the
delivery and becomes a preference. Two or three cycles in, drafts/reports read like the
client wrote the spec themselves. Ask for feedback explicitly in the delivery note — silence
teaches nothing.

**23. A per-page instrument is not a sitewide check — sweep everything the audit should own.**
`refresh <url>` detected stale year references from day one, but the sitewide `audit` never
ran that scan across the corpus — so **44 "… in 2025" titles sailed through a 400-page audit**
(caught by the operator, 2026-07-30). The report can only recommend what a module measures
sitewide. Encoded: `audit.freshness()` now sweeps every page (past-year title/H1 with no
current year → per-page `retitle` finding; body-only staleness ≥2y → aggregated refresh
finding) and feeds `plan`/`autopilot` automatically. General rule: whenever a per-URL command
grows a diagnostic, ask "should the audit sweep this?" — and when a human catches a miss,
encode the check the same day.

**22. One CMS registry, every surface.** `cms_extra.REQUIREMENTS` is the single source of
truth for every CMS's env vars + config keys; integrations, `.env.example`, `preflight`
Stage D, and the wizard all generate from it. When a client's CMS has no public write API
(Squarespace, Framer, Duda), say so at onboarding and route to the file/git-PR flow — an
honest "paste this in" beats a connector that silently can't ship.

---

_Every new site teaches the tool something. When a run surprises you, encode the fix in code
**and** add the rule here. The learning loop above makes that automatic for outcomes._
