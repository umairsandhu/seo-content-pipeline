# AUDIT-COMPLEMENT — the lenses ARCHITECTURE-V2 didn't cover

*Written 2026-08-11. [ARCHITECTURE-V2](ARCHITECTURE-V2.md) audited the architecture
whole-product, but through a single static-structure lens. This document adds the three
lenses it skipped — **security attack surface, test coverage, and doc-content accuracy** —
each measured against the real code with file:line cites. Document-only: findings are
**tracked, not applied**; the HIGH security items are flagged as public-launch gates and
should be closed by a dedicated hardening pass (the `/security-review` skill) before this
ships to strangers.*

*Still NOT covered even now, stated honestly: a runtime/performance profile, a real
line-coverage percentage (no `coverage` tool installed — the number below is a structural
proxy), and line-by-line prose accuracy of the older prose docs (ONBOARDING/PLAYBOOK/
Architecture).*

---

## The threat model (state it before ranking anything)

This is a **local, single-user, loopback-bound, bring-your-own-keys** tool. That is itself a
correct security *decision* that shrinks the threat model enormously — there is no remote
network attacker, no multi-tenant data, no hosted secrets. Several findings below are LOW
*because* of that architecture, and that's a keeper, not luck.

The realistic attackers are three:
- **(A) A malicious web page the user visits while the dashboard is running.** The dashboard
  auto-opens in the browser (`serve.py:350`) and stays up under `serve`/`agent`. A page in
  another tab can reach `http://127.0.0.1:8787` via CSRF and DNS-rebinding. **This is the
  attacker that matters** — it needs zero workspace access, just the normal operating mode.
- **(B) Malicious crawled content / imported files / inbound email.** The tool's entire job is
  to crawl arbitrary sites and act on what it finds — so hostile input is the *expected* input,
  not an edge case.
- **(C) A local process or a planted workspace file.** A local process already has the user's
  file access, so most "local" escapes are ≈ already-authenticated; marginal severity is low.

---

## Security findings (severity-ranked; top items verified by direct read)

### 🔴 HIGH — gate any public launch

**H1 · CSRF + DNS-rebinding on the dashboard's mutating endpoints.** `serve.py:328-341`
(`do_POST`) performs **no Origin / Host / Referer / token check**. All three POST routes are
reachable by a cross-site auto-submitting `<form>` (form-urlencoded ⇒ no CORS preflight):
- `/cycle` → `autopilot.cycle(cfg, deliver=False)` — a full crawl→plan→dispatch→publish/PR run
  under the configured autonomy mode.
- `/approve` → `review.respond(cfg, int(id), "approve")` — approves a **queued live-site
  change**, which `apply --approved` / the next cycle then executes against the CMS.
- `/changes` → attacker-chosen `notes` → `autonomy.set_status(feedback=…)` →
  `brain.distill` → injected into **every persona prompt** (`personas.py:82-84`): CSRF becomes
  *persistent prompt injection*.
There is also no `Host` allowlist, so DNS-rebinding gives a remote page the same access; and
`/api/state` (`serve.py:308-309`) is an unauthenticated dump of the full situation/plan/report
state. *Verified by direct read (`serve.py:328-341`).* → **Fix direction:** require a
same-origin check (Host ∈ {127.0.0.1, localhost} + Origin match) and a per-session CSRF token
on all POSTs; consider a random dashboard token in the URL the browser is opened with.

**H2 · Email-approval spoofing.** `review.py:76-101` (`_poll_email`) reads UNSEEN messages
from INBOX with **no sender allowlist, no DKIM/SPF, no thread verification**. The body regexes
(`review.py:17-19`, matched with `finditer` over the whole message incl. quoted/forwarded
text) mean **anyone who can send email to the polled inbox can approve arbitrary queue IDs**
(`review.py:91-92` → `autonomy.set_status(…,"approved")` → live CMS via
`site_control.apply_approved`) and inject up to 800 chars into the brain via a `FEEDBACK` line
(`review.py:95-97`). The daemon polls every heartbeat and distills the same tick
(`daemon.py:142` → `review.poll` → `brain.cycle`). → **Fix direction:** require approvals from
an allowlisted sender address; treat the inbox as untrusted by default and document that IMAP
polling trusts whoever can email it.

### 🟠 MEDIUM — before pilots on client sites, or document loudly

**M3 · SSRF + `file://` scheme in the crawler.** `ingest.py:31-44` (`_get`/`_fetch`) call bare
`urllib.request.urlopen` with **no scheme allowlist** (stdlib `urllib` honors `file://`,
`ftp://`, `data:`), and with the default empty `include`, `_match` (`ingest.py:234-240`)
applies **no host filter**. A malicious sitemap/sitemap-index `<loc>` can therefore make the
tool read local files (`file:///…/.env`) or fetch internal/localhost services — including the
dashboard's own `/cycle`. Sitemaps recurse with no host/scheme check (`ingest.py:47-89`) and
are auto-discovered from `robots.txt` (`ingest.py:223-240,311-316`). *Verified (`ingest.py:31-44`).*
→ **Fix direction:** allowlist `http/https`, resolve and block private/loopback/link-local IP
ranges, keep crawls host-scoped.

**M4 · Write-path traversal.** `publish.py:60` (`_slug`) collapses only whitespace — `/` and
`..` survive — and `_file` writes `Path("content") / f"{slug}.md"` (`publish.py:72-82`), so a
title/slug like `../../evil` escapes the content dir. `repo.py:59,65` similarly writes
`Path(root, fe["file"])` with no containment check (absolute/`../` paths write anywhere).
Slugs derive from agent/LLM drafts seeded by crawled SERP/competitor titles. *Verified
(`publish.py:60`).* → **Fix direction:** sanitize slugs (strip separators + `..`), and
containment-check every `repo` file path.

**M5 · Untrusted content → prompt injection (architectural — not a one-liner).**
`produce.py:216` embeds raw crawled `page["text"][:4000]` under *"write from THIS"*; emailed
`FEEDBACK`/`CHANGES` notes and review notes flow through `brain.add` into **every**
writer/strategist/editor system prompt (`brain.py:106-136`, `personas.py:82-84`); and the
daemon distills them **without human review**. This is the taint problem — the tool ingests
hostile content and then treats it as instructions. → **Fix direction:** delimit/label
untrusted spans in prompts, and gate auto-distillation of inbound feedback behind human review.

**M6 · Env credentials persisted to `config.json` in cleartext.** `config.load` injects
`_dfs_login`/`_dfs_password` from the environment into the cfg dict (`config.py:187-188`), and
`wizard.interactive` writes the whole dict to disk (`wizard.py:200`) — so DataForSEO creds
that lived only in `.env` get written into `config.json` in cleartext. Worse, the leak-scanner
regex (`safety.py:42`) doesn't match JSON (`"_dfs_password": "…"`), so `safety` won't flag it.
`config.json` *is* gitignored, so it won't be committed — but plaintext creds on disk plus a
scanner blind spot is a real finding. → **Fix direction:** never persist `_`-prefixed
env-sourced keys; extend the secret regex to JSON.

### 🟡 LOW / by-design (local-first legitimately shrinks these)

- **`/doc` symlink escape** (`serve.py:290`) — `.resolve()` follows symlinks then only checks
  cwd-containment, never re-checking the whitelist, so `content/x.json → ../.env` is served.
  *Verified* — but it needs attacker **write access to the workspace**, i.e. ≈ already a local
  user. → tighten by re-checking the resolved path against the whitelist.
- **Subprocess argv injection** — a leading-`-` value in `cfg.site`/crawl URL/`rclone_remote`
  becomes a CLI flag (`sfimport.py:193`, `speed.py:126`, `deliver.py:66`). Bounded: **no
  `shell=True`, no `os.system`, no `eval`/`exec`/`pickle`/`yaml.load` anywhere in the package**
  (a real keeper) — so this is flag-confusion, not RCE.
- **Unescaped XML in the launchd plist** (`daemon.py:93-111`) — `<`/`&` in a site netloc or cwd
  corrupts the plist; unusual inputs only.
- **Parser DoS** — no size caps on `urlopen`/zip/CSV reads (`ingest.py:34`, `sfimport.py:98`,
  `gsc_csv.py:110`); ReDoS surface in the HTML regexes. Availability only, self-inflicted on a
  local tool.
- **Unauthenticated local state** — `/api/state`, `approvals.json`, `state/` are plain files a
  local process can already read/write; same origin as H1.

### Keepers the security sweep confirmed
Parameterized SQL throughout (`ledger.py`, `store.py`); list-argv on every subprocess (no
shell); MCP is **stdio-only** (no socket — the parent process is the trust boundary); no
`eval`/`exec`/`pickle`/`yaml.load` in the package; the fork-safety leak-scan and gitignore
hardening (recently extended to `CLIENT.md`/`state/`/`*.db`). The local-first choice is doing
real security work.

---

## Coverage findings

No `coverage` tool is installed, so this is a **structural proxy** (which modules are named by
the test suite at all), not a line-coverage percentage — a real run belongs in CI.

**33 of 85 modules are never named** in the single 1,308-line, 104-method, 49-class
`tests/test_core.py`. The revealing part is *which* 33: the under-tested set is the **original
pipeline core** — `plan`, `analyze`, `onboard`, `report`, `publish`, `safety`, `safetygate`,
`remediate`, `eeat`, `decay`, `backlinks`, `rank`, `render`, `notify`, `index`, `authority`,
`internal`, `intl`, `local`, `logs`, `aivis`, `competitors`, `prospect`, `trends`, `radar`,
`jobs`, `store`, `opportunities`, `refresh`, `webagent`, `gsc_csv` — while the newest,
adversarially-built subsystems (ledger/learn/brain/attribution, identity, sitediff, zeroclick,
provider choices, native crawler) are well covered. The tool got safer to change exactly where
it was youngest, and least where it was oldest. → **Recommend:** per-module smoke tests for the
load-bearing untested set (`plan`/`publish`/`safety`/`report` first), and a real coverage run
gated in CI. This ties directly to [ARCHITECTURE-V2 §6](ARCHITECTURE-V2.md): the per-capability
contract is the natural home for a per-capability test contract.

---

## Doc-content findings (exact, measured)

Command **presence** across the doc surfaces, against the 93 registered CLI commands:

| Surface | Coverage | Missing |
|---|--:|---|
| docs/Capabilities.md | 92/93 | `edition` |
| SKILL.md | 89/93 | `anomaly`, `edition`, `ga4`, `pr` |
| README.md | 83/93 | `analyze`, `autolink`, `discover`, `inlinks`, `interview`, `intl`, `prospect`, `remediate`, `research`, `toxicity` |
| **docs/Commands.md** | **76/93** | `autopilot`, `cms`, `deliver`, `demo`, `edition`, `feedback`, `interview`, `learn`, `practices`, `repurpose`, `serve`, `sf`, `sitediff`, `start`, `tip`, `voice`, `zeroclick` |

`docs/Commands.md` is the worst — it predates the entire autonomy/learning/identity era.
Caveat: this measures *presence*, not accuracy; the prose in older docs
(ONBOARDING/PLAYBOOK/Architecture) was not line-verified against current behavior. This is the
doc-drift ARCHITECTURE-V2 §1 predicted, quantified — and the reason the v2 fix is doc
*generation*, not another hand-patch (patching by hand here would repeat the exact sin the
retrospective names).

---

## Punch list (tracked, not applied)

| # | Finding | Sev | Fixes at |
|---|---|---|---|
| H1 | Dashboard CSRF / DNS-rebinding | 🔴 | serve.py do_POST/do_GET |
| H2 | Email-approval spoofing | 🔴 | review._poll_email |
| M3 | Crawler SSRF + file:// | 🟠 | ingest._get/_fetch/_match |
| M4 | Write-path traversal | 🟠 | publish._slug, repo file paths |
| M5 | Untrusted content → prompt injection | 🟠 | produce/brain/personas (taint model) |
| M6 | Env creds → config.json cleartext + scanner blind spot | 🟠 | config.load, wizard, safety regex |
| L7 | /doc symlink escape | 🟡 | serve._doc_path |
| L8 | Subprocess argv flag-injection | 🟡 | sfimport/speed/deliver argv |
| L9 | Coverage: 33 untested core modules | 🟡 | tests/ + CI coverage |
| L10 | Doc drift (Commands.md 76/93) | 🟡 | doc generation (v2 §6) |

**H1 and H2 gate any public/agency launch.** The right way to clear them is a dedicated
hardening pass — run `/security-review` on a branch and fix under test — not another
document. This file is the map for that pass.

---

## ✅ Status update (2026-08-11): H1, H2, and M3–M6 fixed

The hardening pass landed with the CHANGE-PLAN Tier-1 work — verified by 7 new security tests
and a live curl smoke of the dashboard (no-token → 403, spoofed Host → 403, `/` → 303
bootstrap):

- **H1** — per-session token on every mutating POST + `/api/state`/`/doc`, Host-loopback
  (rebinding) guard, CSP + `nosniff`, raw-`.html` passthrough removed. `serve.py`.
- **H2** — email approvals require an allowlisted sender; empty allowlist disables them. `review.py`.
- **M3** — `ingest._url_ok`: http(s)-only, blocks loopback/private/link-local + `file://`, size cap, redirect re-check.
- **M4** — `publish._slug` sanitized; `repo._contained` blocks `../`/absolute file writes.
- **M5** — untrusted crawled content fenced as data; brain memory relabeled non-instruction.
- **M6** — `config.persistable` strips env creds before any config write; leak-scanner regex now matches JSON.
- **L7** — `/doc` re-checks the *resolved* path against the whitelist (symlink escape closed).

Still open (by-design LOW): L8 subprocess argv flag-confusion (no RCE — no `shell=True`),
plus the coverage + doc-drift items, which are tracked in
[CHANGE-PLAN](CHANGE-PLAN.md) Tier 2/3.
