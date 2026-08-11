# ARCHITECTURE-V2 — the rebuild retrospective

*Written 2026-08-11, before launch, while the lessons were fresh. The question this answers:
"rebuild from scratch knowing everything we now know — what's the FIRST architectural
decision you'd change, and why didn't we make it the first time? Separate 'we couldn't have
known' from 'we didn't want to know.'" Grounded by a full drift inventory of the codebase
(87 modules, 13,348 LOC) and an adversarial comparison of the two candidate answers.
No code changes ship with this document — it is the blueprint for post-launch execution.*

---

## §1 · The verdict

**The first decision I'd change: every capability self-describes in ONE registry, and every
surface — CLI, MCP, docs, config slots, wizard, preflight, dashboard, scheduler — is
GENERATED from it.**

The daily act of this project was adding a capability: roughly one every four hours for
three weeks, 93 CLI commands by launch-candidate. Each addition had to be hand-echoed into
up to eight surfaces: an argparse parser + a branch in a 92-arm `elif` chain
(`__main__.py`, 539 lines), an entry in `mcp_server.TOOLS` (66 tuples), rows in README /
SKILL.md / docs/Capabilities.md / docs/Commands.md, config template + hints, the wizard,
the readiness journey, the dashboard, and the scheduler/tips maps. Every shipped failure in
this codebase is a manifestation of that one missing contract.

**The repo contains its own natural experiment.** One seam was built registry-first:
`integrations.INTEGRATIONS` + `cms_extra.REQUIREMENTS`, whose docstring literally promises
*"add a CMS here and every surface updates"* — generating `.env.example`, the wizard's CMS
step, and preflight's Stage D. That seam absorbed **13 CMS connectors and the entire
OSS-provider wave with zero drift**. Every hand-synced surface, maintained by the same
author in the same weeks at the same velocity, drifted within days. The controlled variable
was the registry.

**The smoking guns, live at the time of writing:**
- `README.md` carries **three contradictory MCP tool counts in one file right now** — the
  badge says 66 (line 15), the install section says 57 (line 72), the pricing table says 59
  (line 240). The true count is 66. No single commit was careless; the surfaces simply
  outnumber the discipline.
- **The CATS bug** (git-archaeology confirmed): `audit.CATS` was born with 10 categories,
  froze, and then the `freshness` (commit 676ece7), `indexability` (55d75c5), and `mobile`
  checks were added. Their findings entered the counts in the report header but
  `render_md` iterates `for cat in CATS:` (audit.py:463) — so they were **counted but
  invisible** until 76b1dbb backfilled the list. We fixed it by extending the hardcoded
  list instead of killing the pattern; the same class of bug remains constructible today.

**Why registry-first beats the other candidate.** The serious alternative was
**spine-first**: one append-only event store (Signal / Finding / Change / Outcome / Lesson)
with everything else as derived views — attacking the ~10-store fragmentation and the
holdout-contamination risk (a change that bypasses the ledger silently poisons the holdout,
which biases every lift number, which `learn` aggregates and `brain` converts into
confident "do more of this" playbooks injected into every prompt). That risk is real and
existential. But the scorecard is lopsided: registry-first prevents the **four failure
classes that actually shipped** (vocabulary drift like CATS, doc drift, five parallel
registries, and — via machine-readable `requires` — the `_safe` epidemic's root cause);
spine-first prevents one shipped class (re-derivation) and one latent risk. And the
tiebreaker is the **dependency arrow**: a capability contract that declares
`emits=("Change",)` *is* the spine's schema, written incrementally as capabilities are
added — and the registry is the enforcement point ("any side-effecting capability must emit
Change" is a one-line CI test, which is precisely what makes holdouts trustworthy). The
reverse is not true: an event schema knows nothing about argparse, MCP inputSchemas, wizard
seams, or docs rows. **The spine is the correct decision #2**, adopted the week the tool
first writes to a live site.

---

## §2 · The evidence

From the inventory (all verifiable in-tree):

**Registries.** ~52 registry-like structures: 16 primary (`INTEGRATIONS` 34 entries ·
`cms_extra.REQUIREMENTS` 16 · `wizard.CHOICES` 5 seams · `config.DEFAULTS/TEMPLATE/HINTS`
21/20/20 · `mcp_server.TOOLS` 66 · `tips.TIPS` 24 + `_CONTEXT` 24 · `audit.CATS` 14 +
`HINTS` 13 · `autopilot._SCHED` 19 + `_TASK` 12 · `journey` stages · `identity.INTERVIEW`),
18 secondary (`schema.REQUIRED/GENERATORS`, `personas.ROLES`, `safety.GITIGNORE/PATTERNS`,
`profile._FP`, `geo.WEIGHTS`, `logs.BOTS`, `sfimport._COLS`, `edition.PRICING`,
`remediate._PLAYBOOK`…), **six independent CTR-curve tables** (`aio.py:19`,
`consult.py:55`, `ctr_curves.py:12`…), and **six icon maps** for the same three severity
levels.

**Surfaces.** 93 CLI commands; help text maintained in 4–5 places; measured coverage drift:
MCP 66/93, SKILL.md 87/93, docs/Commands.md 73/93, docs/Capabilities.md 92/93.

**Stores.** ~10 persistence families (corpus.json + corpus.prev.json · nine `state/` keys ·
three SQLite tables across two DBs · ten `history/<kind>` families · `~/.seo-agent/` ·
approvals/review drop-files · six identity markdown files · site-changes/ · sf-exports/);
**24 modules write files directly**; `state.KEYS` declares only 4 of the 9 keys actually
written, so `state.summary()` is blind to brain/agent/deliveries/profile/sf.

**Duplication.** `_safe()` defined **six times with two incompatible signatures**
(autopilot, orchestrate, report vs consult, daemon, diagnose); **162 bare
`except Exception`** clauses; **56 hand-written `render_md()`** implementations; **62 loose
finding-dict construction sites** (`{"cat","sev","url","msg"}`) across 7 modules with no
shared constructor; 54% of sibling imports are lazy in-function (97 of 180).

**Tests.** One 1,227-line `test_core.py`: 49 classes, 100 methods, for 87 modules.

**Drift discovered BY this retrospective** (the audit audited itself):
- (a) `audit.CATS` ↔ `audit.HINTS`: category `"index"` renders with no hint (audit.py:480
  silently emits nothing for it).
- (b) `autopilot._SCHED` ↔ `_TASK`: **8 scheduled action kinds have no task renderer**
  (`eeat`, `geo`, `decide`, `repeat-win`, `ai-visibility`, `fix:a11y`, `fix:duplicate`,
  `fix:headings`) and `fix:freshness` renders but is never scheduled.
- (c) `config.DEFAULTS` ↔ `TEMPLATE`: **9 settings (`llm`, `render`, `max_pages`, `audit`,
  `speed`, `ingest`, `aio`, `pillars`, `history_dir`) never receive scaffolded slots** —
  quietly breaking the "every setting has a visible slot" promise we shipped as a feature.
- (d) `safety.GITIGNORE` ↔ `serve._DOC_FILES`: **9 dashboard-served artifacts are not
  gitignored — including CLIENT.md**, which holds business-sensitive interview answers.
- Plus: `INTEGRATIONS` is **mutated at import time** (`integrations.py:158`, import-order
  dependent) and the `followups` DDL is declared twice in ledger.py (:81, :120).

---

## §3 · What we couldn't have known

Honest epistemics — decisions that were reasonable with day-one information:

- **Day 1, this was a content pipeline** — crawl → audit → brief → publish, ~6 commands.
  A capability registry pays for itself around capability #3 and compounds for the next 90,
  but nobody rationally designs a capability *platform* for a content script. The scale
  (93 commands, 66 tools, an autonomous employee) was an emergent product discovery, not a
  spec we ignored.
- **The spine's value did not exist yet.** An event store for a tool that only *reads*
  sites would have been speculative architecture. The ledger was correctly *discovered* as
  the moat in week 2, when the tool started making changes and measuring them — that is
  when Change-as-primary-write-path became meaningful.
- **External audits as a forcing function.** That two independent GLM audits would judge us
  by *capability-surface truth* — turning doc drift from private toil into public
  credibility damage — was not foreseeable when the README was six lines.
- **Identity-as-files arrived late by necessity.** The OpenClaw/Hermes patterns
  (SOUL/AGENTS/CLIENT/MEMORY, interview-built user models) were learned by studying those
  projects mid-build. That MEMORY.md should be a *generated view* of a Lesson stream is
  obvious only after both the brain and the identity layer existed.

---

## §4 · What we didn't want to know

The motivated part. Not carelessness — a mechanism, named plainly:

- **We had the principle in the codebase and scoped it away from ourselves.**
  `integrations.py` was explicitly built so ".env.example never drifts from the code" —
  *for external APIs*. We then built `cms_extra.REQUIREMENTS`, `wizard.CHOICES`, and
  `config.TEMPLATE/HINTS` as three more partial registries, each at a moment of felt pain,
  and never unified them. **By the third partial registry, we knew.** The evidence wasn't
  hidden; it was load-bearing in our own commit messages.
- **We paid known toil instead of automating it.** Badge counts were hand-bumped in nearly
  every commit ("52 → 57 → 59 → 66 tools") — recurring manual labor is a system telling you
  a number should be computed. The CATS bug got fixed by backfilling the hardcoded list
  rather than deleting the pattern that produced it.
- **`_safe` was copied six times.** Each copy was a moment of "this already exists
  elsewhere," and each was rational locally: graceful degradation is a correct principle
  for *missing credentials*, but with requirements existing only as prose, callers couldn't
  distinguish "GSC isn't connected" from "my new code has an IndexError" — so they wrapped
  everything, and 162 bare `except Exception` clauses made our own bugs indistinguishable
  from missing access. The degradation principle was over-applied into an anesthetic.
- **The incentive mechanism: demo-driven development under critique pressure.** Every
  session rewarded a visible new capability; both external audits *counted capabilities*;
  a registry refactor ships zero features and, mid-sprint, reads as stalling. Velocity was
  the point — and drift was the loan we took out to fund it.

To be fair to the loan: it was arguably the **correct trade** for a three-week 0→launch
sprint — v1 exists, works, and out-features category leaders precisely because we didn't
stop to re-architect. The sin would not have been taking the loan. The sin would be
pretending it isn't on the books. This document is the books.

---

## §5 · The v2 blueprint

### Decision #1 — the capability contract

One module = one registered capability in `seo_agent/registry.py`; every surface is a
generator over the registry:

```python
Capability(
  name="audit",                     # ONE identifier: CLI command, MCP tool, docs anchor
  title="Site Doctor", group="doctor",
  summary="Sitemap/robots/meta/links/structured-data audit",   # → MCP desc, README row, dashboard card
  args={...JSON schema...},         # ONE schema → generated argparse subparser AND MCP inputSchema
  run=fn(cfg, **args) -> data,      # pure: returns typed data, never prints
  render=fn(cfg, data) -> str,      # agent-native markdown (keeper); default renderer if absent
  emits=("Finding",),               # spine record kinds  ← decision-#2 hook
  vocab={"finding.cat": {"freshness": {"why": ..., "fix": ...}, ...}},
                                    # closed vocabulary + teach-forward hints (absorbs audit.HINTS;
                                    # CI: "every emitted cat is registered" → CATS-class bugs unshippable)
  requires=("gsc?",),               # provider slots; "?" = soft → dispatcher degrades; bare = hard gate
  trust={"mutates": False,          # ← Round-2 addition: does invoking this change state?
         "untrusted_inputs": ("page_text",),   #   which args carry hostile content (taint)
         "touches_live": False},    #   crosses to the live site? → force the human gate
  config={"audit.title_max": {"default": 60, "hint": "..."}},  # absorbs TEMPLATE/HINTS/DEFAULTS
  providers=[...],                  # per-seam options, recommended-first (absorbs CHOICES/INTEGRATIONS/REQUIREMENTS)
  schedule=("weekly", 0),           # absorbs autopilot._SCHED/_TASK
  journey=fn(cfg) -> status,        # absorbs preflight/journey items
  tips=("technical",),              # absorbs tips._CONTEXT
)
```

Generated: CLI parser + dispatch (deletes the 92-elif) · MCP `tools/list` (deletes `TOOLS`)
· README command map, SKILL.md, Capabilities.md, badge counts (computed) · `.env.example` ·
wizard + provider picker · `config --fix` · preflight · dashboard cards · scheduler · tips.
Two CI tests hold the line: *every module registers exactly one capability* and
*committed docs == generated docs*.

### The error-policy split (enabled by the contract)

One exception class — `MissingAccess(provider, how_to)` — raised only by the provider
layer. The **dispatcher** pre-checks `requires`, degrades with the teach-forward message,
and records a typed Degraded marker. **Everything else propagates loudly** to a visible
`state/errors` view + a red dashboard banner. Zero `_safe`. Lint rule: `except Exception`
requires a comment naming the expected failure. Graceful degradation stays a feature —
scoped to missing *access*, never to our own defects.

### Decision #2 — the spine underneath

Five record kinds in one append-only, versioned store (envelope
`{id, ts, v, kind, site, actor, data}`): **Signal** (GSC/rank/CWV/crawl/GA4 pulls) ·
**Finding** (audit/anomaly/decay) · **Change** (*the* primary write path —
registry-enforced) · **Outcome** (per-change lift vs holdout at +7/28/90d) · **Lesson**
(learn/brain distillations). Holdout = "URLs with zero Change events in the window" —
**true by construction**, which is what makes the learning loop's confidence honest.
`corpus.json`, `state/*.json`, `brain.json`, `MEMORY.md`, `history/` become derived views
or import buffers.

### Keepers — what v1 got right

Local-first plain files, one folder per site · human gates between the agent and the live
site · holdout measurement at +7/28/90d · identity-as-markdown (SOUL/AGENTS/CLIENT
editable; MEMORY.md becomes a generated view) · per-capability markdown rendering for
agent consumption · fork-safety + leak-scan · stdlib-first with optional depth ·
teach-while-it-works tips · graceful degradation, properly scoped.

---

## §6 · The strangler migration (post-launch; no rewrite)

**Phase 1 — contract shim.** Add `registry.py`; `__main__` tries registry dispatch first,
falls back to the elif chain; MCP serves generated entries for migrated capabilities.
Migrate the ten worst drifters first (audit, plan, learn, brain, ledger, gsc, autopilot,
publish, wizard, integrations); *absorb* the four existing data registries (they're already
data — they move, not rewrite). Land the generated-vs-committed docs CI test immediately.
*Exit: elif chain and TOOLS shrink monotonically; badge counts computed; CATS replaced by
registered vocab.*

**Phase 2 — error-policy cutover.** `MissingAccess` in the provider layer; dispatcher-level
degradation from `requires`; delete all six `_safe` definitions; daemon/autopilot route
internal errors to `state/errors` + dashboard banner. *Exit: an injected bug in
`audit.metadata` crashes `audit` visibly instead of yielding a quietly empty report;
`except Exception` count drops from 162 to named-only.*

**Phase 3 — spine underneath.** (a) Funnel: `ledger.record` becomes `events.append(Change)`
dual-writing the old table; route site_control/repo/publish/review-apply through it; add
the "side-effecting ⇒ emits Change" registry test. (b) Signals: `history.snapshot`
dual-writes Signal events; ledger/learn/algo switch reads; verify attribution matches the
legacy path on a fixture site before cutover. (c) Views: regenerate brain/state/MEMORY.md
from events; retire direct writes. *Exit: delete `state/`, rebuild it byte-identical from
events; diagnose/learn/practices/zeroclick read one store.*

Each phase ships alone, is reversible (dual-write throughout), and the ordering follows the
same dependency arrow that decided the verdict: the registry provides the hooks the other
two phases enforce with.

---

## §7 · Appendix — found while writing this (same-day-fixable punch list)

Not in this document's scope, but discovered by its audit and cheap to fix:

1. **`CLIENT.md` (and 8 other dashboard-served artifacts) are not in `safety.GITIGNORE`** —
   CLIENT.md holds business-sensitive interview answers; in a workspace under git backup
   this borders on a security fix. **Do first.**
2. `audit.HINTS` lacks an entry for category `"index"` (renders hintless).
3. `autopilot._TASK` lacks renderers for 8 scheduled kinds; `fix:freshness` is unschedulable.
4. `config.TEMPLATE` misses 9 DEFAULTS keys — `config --fix` can't scaffold them.
5. `integrations.INTEGRATIONS` mutated at import time (order-dependent); make it a function.
6. Duplicate `followups` DDL in ledger.py (:81, :120).
7. README's three contradictory MCP counts (66/57/59) — fix now, compute post-Phase-1.

---

*The one-sentence version: we built five registries because we kept feeling the pain of not
having one — the rebuild starts by believing our own docstring: "register once → everything
else knows."*

---

# Round 2 — re-asked against the complete audit (2026-08-11)

*Round 1 audited the architecture through one static-structure lens. We then ran the three
lenses it skipped — a **security attack-surface map**, a **coverage measurement**, and an
**exact doc-content diff** (all in [AUDIT-COMPLEMENT](AUDIT-COMPLEMENT.md)) — and re-asked the
rebuild question. Does the registry-first verdict survive?*

## The verdict survives — and round 2 confirms round 1's prediction

The security lens surfaces a failure *class* the static lens could not see: the tool **crossed
a trust boundary**. It became a thing that runs a *mutating* localhost server the browser
auto-opens, an always-on daemon that acts autonomously, subprocess execution, and — most of
all — a loop that **ingests untrusted web content and then acts on it** — with no taint model
and no mutation/trust boundary anywhere in the architecture. The two findings that scored HIGH
(CSRF-to-autopilot-publish on the dashboard; email/feedback → persistent prompt injection) are
both expressions of that missing boundary.

So is the trust boundary the *new* #1 that displaces registry-first? No — and the reason is the
same dependency arrow that decided round 1:

- **Most of the security findings are localized, not structural.** A CSRF token, an Origin
  check, a scheme allowlist, a slug sanitizer are a few lines each — a hardening pass, not a
  rebuild. That is categorically unlike drift, which cannot be fixed without the contract.
- **The one architectural finding — untrusted-content → prompt-injection — is enforced by the
  registry, exactly like the other cross-cutting policies.** A capability contract with a
  `trust` dimension (`mutates` / `untrusted_inputs` / `touches_live` — added to the §5 spec
  above) lets the *dispatcher* CSRF-protect every `mutates:true` capability, taint-track every
  `untrusted_inputs` argument, and force the human gate on every `touches_live` call. This is
  the **third** cross-cutting policy the registry is the substrate for — after the error policy
  (degrade-vs-fail) and the event spine ("side-effecting ⇒ emits Change"). One contract; three
  policies enforced at one point instead of re-implemented per route.

**Registry-first stays #1. The event spine stays #2. Round 2's concrete change is to the
contract spec, not the ranking:** round 1's contract had `requires` and `emits` but no trust
flags. Add them. The trust boundary is decision #2b — adopted the same week as the spine (the
week the tool first mutates and acts), and enforced through the same registry.

## The sharper "we didn't want to know"

Round 1's drift at least *nagged* us — badge counts we hand-bumped every commit, the CATS bug
that eventually surfaced. The security surface was **silent**. We shipped a mutating localhost
dashboard that auto-launches in the browser, an always-on daemon, subprocess execution, and
autonomous action on crawled content — and **never ran a single security pass until asked**.
Coverage is the identical shape: 39% of modules untested, because a test produces no visible
artifact. Both blind spots share one cause, and it is exactly the mechanism round 1 named:
**demo-driven development under critique pressure.** Security, tests, and doc-accuracy are
precisely the three things that *have no demo* — so they are precisely the three things that
rotted. Round 2 does not overturn round 1's thesis; it is the controlled prediction that
thesis makes, confirmed. If the incentive was "ship a visible capability every session," then
the invisible work was always going to be the debt — and it was.

## The "we couldn't have known" that legitimately holds

Local-first / loopback / single-user / bring-your-own-keys was itself a **correct security
decision** — it shrank the threat model so far that several findings are LOW *by design*: no
remote attacker, no multi-tenant data, no hosted secrets, stdio-only MCP, no `eval`/`pickle`.
That is a keeper. The two things that architecture does *not* cover — a browser reaching
localhost, and acting on untrusted content you fetched — are exactly the two that scored HIGH.
And both became knowable only at the same inflection as the ledger and the spine: **week 2–3,
when the content script became an autonomous agent.** On day 1, a crawl-and-report script that
touches nothing and opens no port has neither problem. The honest line is the same as round
1's: we couldn't have known the tool would cross the trust boundary; once it did, the boundary
was a knowable gap we didn't look at — because looking produced no demo.

## What this means for launch (not for the rebuild)

The rebuild verdict is unchanged, but the *launch* gate moved: **AUDIT-COMPLEMENT H1 (dashboard
CSRF) and H2 (email-approval spoofing) must be closed before this ships to strangers** — those
are exploitable, not merely untidy. The fix is a dedicated hardening pass under test
(`/security-review`), not a document. This addendum's job was only to answer whether the
complete picture changes the *architecture* verdict. It doesn't. It sharpens it, and it turns
round 1's self-diagnosis from an assertion into a confirmed prediction.
