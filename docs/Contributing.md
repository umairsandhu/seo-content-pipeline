# Contributing / Extending

The codebase is intentionally small, terse, and consistent. Match the surrounding style: pure
functions, docstring-first, `numpy`/`scikit-learn` + stdlib only, and **graceful degradation**
(a missing credential disables a capability, never crashes a run). Fixes are proposed, not
applied. New capabilities should be deterministic where possible; leave editorial writing and
judgment to the agent.

## Ground rules
- **Site-agnostic** — no hardcoded site; read everything from `cfg`.
- **Degrade gracefully** — wrap external calls; return empty/None instead of raising.
- **File-based** — persist to the workspace (JSON), not a DB.
- **Fork-safe** — never write real secrets; new env vars go in the registry (auto-added to
  `.env.example`).

## Add a Site-Doctor check
In `seo_agent/audit.py`, write a function that appends findings, then call it in `report()`:

```python
def my_check(corpus, F):
    bad = [c for c in corpus if _indexable(c) and <condition>]
    if bad:
        F.append({"cat": "content", "sev": "med", "url": bad[0]["url"],
                  "msg": f"{len(bad)} pages have <problem>"})
# in report(): my_check(corpus, F)
```
Findings are `{cat, sev(high|med|low), url, msg}`. Add a new `cat` to `CATS` if needed. Prefer
**one aggregated finding** (count + samples) over one-per-page. If the check needs new page
data, capture it in `ingest.extract()` (add a field to the returned dict).

## Add an API integration
1. Append an entry to `INTEGRATIONS` in `seo_agent/integrations.py` (`tier`, `env`, `config`,
   `unlocks`, `options`, `docs`). This auto-updates `.env.example`, onboarding, and the matrix.
2. Add a provider function in `seo_agent/providers.py` using `http_json` (the generic
   authenticated HTTP primitive). Degrade to `None`/`[]` on missing auth.
3. Wire it into a command/finding.

## Add a CMS connector
In `seo_agent/publish.py`, add a `_yourcms(cfg, cms, post)` function returning
`{ok, connector, id/url}`, register it in the `publish()` dispatch dict, and add an
integration entry with its env var. Follow the existing WordPress/Ghost connectors.

## Add a CLI command + MCP tool
- CLI: add a subparser + a dispatch branch in `seo_agent/__main__.py`, and a line to the header.
- MCP: add a `_yourtool(a)` function and an entry to `TOOLS` in `seo_agent/mcp_server.py`.

## Add a capability to the action plan
Have `seo_agent/plan.py` pull your signal and `add(_a(impact, effort, kind, target, why, cmd))`
so it appears in the ranked plan. Keep sources best-effort (wrap in `try/except`).

## The build loop (research before building)
Per [BUILDLOOP.md](../BUILDLOOP.md): monitor the canonical sources → when Google/AI search
shifts, ground the change in a research pass → encode it as a check/metric → validate on a
golden test site → ship. Don't build capabilities on unverified claims — the roadmap flags
which items still need an evidence pass (e.g. a rigorous topical-authority/E-E-A-T *scoring*
model) vs. which are blocked (the GSC Generative-AI API).

## Testing
Smoke-test offline: create a small `corpus.json` + `config.json`, run the command, and confirm
it degrades cleanly with no credentials. Run `python -m py_compile seo_agent/*.py` and
`seo-content-pipeline safety --precommit` before committing.

## Style
Terse, readable, self-documenting. Prefer clarity over cleverness. One capability = one module.
Update the relevant doc (`docs/…`, `SKILL.md`, `BUILDLOOP.md`) with the change.
