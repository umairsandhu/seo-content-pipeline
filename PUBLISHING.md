# Publishing & Installing

Three ways people get this tool. All are one-command once set up.

## A. As a Python package (PyPI) — `pip install`

**Local build test (anyone):**
```bash
pip install build
python -m build          # → dist/*.whl and dist/*.tar.gz
pip install dist/*.whl   # then: seo-content-pipeline --help
```

**Publish to PyPI (maintainer):**
- **Recommended — Trusted Publishing (no tokens):** on [pypi.org](https://pypi.org) →
  the project → *Publishing* → add a trusted publisher for GitHub repo
  `umairsandhu/seo-content-pipeline`, workflow `publish.yml`, environment `pypi`. Then just
  cut a GitHub Release — `.github/workflows/publish.yml` builds and publishes automatically.
- **Or with a token:** `pip install twine && python -m build && twine upload dist/*` (enter
  your PyPI API token when prompted).

**Then anyone installs with:**
```bash
pip install seo-content-pipeline      # or: pipx install seo-content-pipeline
seo-content-pipeline init --site https://theirsite.com
```

Optional extras: `pip install "seo-content-pipeline[gsc,render,embeddings]"`.

## B. As a Claude Code plugin — one-command skill install

The repo is its own Claude marketplace (`.claude-plugin/marketplace.json` + `plugin.json`).
Users install the skill with:
```
/plugin marketplace add umairsandhu/seo-content-pipeline
/plugin install seo-content-pipeline@seo-content-pipeline
```
Claude then auto-invokes it for SEO tasks and **writes the content itself** (no LLM key
needed). To develop locally, drop the repo into `~/.claude/skills/` and it's picked up.

## C. As an MCP server — for any MCP client / CMS

```bash
python -m seo_agent mcp        # stdio MCP server, 33 tools
```
Register it in Claude Desktop / Claude Code / any MCP client as command
`python -m seo_agent mcp`; set `SEO_CONFIG=<path-to-config.json>` to point at a workspace.

## Versioning
Bump `version` in `pyproject.toml`, `.claude-plugin/plugin.json`, and
`.claude-plugin/marketplace.json` together, then tag + release. Keep them in sync.

## Fork-safety
Publishing never ships secrets: `safety`/`init` gitignore `.env`, `config.json`, the
service-account JSON, `history/`, and outputs, and leak-scan the tree. `.env.example` (a
placeholder template) is the only env file committed.
