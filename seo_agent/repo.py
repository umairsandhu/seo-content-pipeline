"""Repo-based execution — the thing no SaaS dashboard can do: edit meta tags, schema,
canonicals and redirects *directly in the site's codebase* and open a PR. Autonomy-
gated (manual→diff only, approve→queue, auto→branch+commit+PR), and every applied edit
is logged to the causal ledger with its commit ref.

Degrades cleanly: not a git repo → writes `.patch` files; git but no `gh` CLI → commits
a branch and prints the PR command; full setup → opens the PR. Stdlib + git/gh.
Site-agnostic — point `repo.path` at the checkout (defaults to cwd)."""
import difflib
import re
import subprocess
from pathlib import Path

from . import autonomy, ledger


def _root(cfg):
    return Path((cfg.get("repo", {}) or {}).get("path", "."))


def _git(root, *args, check=False):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60,
                          check=check).stdout.strip()


def _is_git(root):
    try:
        return _git(root, "rev-parse", "--is-inside-work-tree") == "true"
    except Exception:
        return False


def diff_edit(path, edits):
    """Apply regex `edits` (list of {find, replace}) to a file's text; return (new_text, unified_diff)."""
    p = Path(path)
    if not p.exists():
        return None, f"missing file: {path}"
    before = p.read_text(encoding="utf-8", errors="ignore")
    after = before
    for e in edits:
        after = re.sub(e["find"], e["replace"], after, flags=re.I | re.S)
    diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        fromfile=f"a/{p.name}", tofile=f"b/{p.name}"))
    return after, diff


def _contained(root, rel):
    """SEC-M4: the edited file must resolve INSIDE the repo root — no absolute or ../ paths."""
    root = Path(root).resolve()
    p = (root / rel).resolve()
    return root == p or root in p.parents


def open_pr(cfg, title, file_edits, branch=None, url=""):
    """file_edits: [{file, edits:[{find,replace}], desc, url?}]. Returns a result dict."""
    root = _root(cfg)
    bad = [fe["file"] for fe in file_edits if not _contained(root, fe["file"])]
    if bad:
        return {"status": "blocked", "reason": f"path escapes the repo root: {bad[0]}"}
    dec = autonomy.authorize(cfg, f"PR: {title}", kind="update", target=url or title)
    # compute diffs regardless (so manual mode shows the change)
    planned = []
    for fe in file_edits:
        new, diff = diff_edit(Path(root, fe["file"]), fe["edits"])
        planned.append({**fe, "diff": diff, "new": new})
    if not dec["execute"]:
        for pl in planned:  # write .patch previews
            if pl.get("diff"):
                Path(root, pl["file"] + ".patch").write_text(pl["diff"])
        return {"status": "queued" if dec.get("queued") else "planned", "reason": dec["reason"],
                "edits": [{"file": p["file"], "diff": p["diff"]} for p in planned]}
    # execute: write files
    for pl in planned:
        if pl.get("new") is not None:
            Path(root, pl["file"]).write_text(pl["new"], encoding="utf-8")
    if not _is_git(root):
        return {"status": "written", "note": "not a git repo — files edited in place; commit manually",
                "files": [p["file"] for p in planned]}
    br = branch or "seo/" + re.sub(r"[^a-z0-9]+", "-", title.lower())[:40]
    _git(root, "checkout", "-b", br)
    _git(root, "add", *[p["file"] for p in planned])
    _git(root, "commit", "-m", title + "\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>")
    commit = _git(root, "rev-parse", "--short", "HEAD")
    for pl in planned:  # log each edit to the ledger with the commit ref
        ledger.record(cfg, pl.get("url") or url or pl["file"], "repo-edit", pl.get("desc", title), commit_ref=commit)
    pr = _gh_pr(root, br, title)
    return {"status": "pr" if pr else "committed", "branch": br, "commit": commit, "pr": pr,
            "files": [p["file"] for p in planned]}


def _gh_pr(root, branch, title):
    try:
        _git(root, "push", "-u", "origin", branch)
        out = subprocess.run(["gh", "pr", "create", "--title", title, "--body",
                              "Automated SEO fix. Review before merge.", "--head", branch],
                             cwd=str(root), capture_output=True, text=True, timeout=60)
        return out.stdout.strip() or None
    except Exception:
        return None


def render_md(cfg, r):
    st = r["status"]
    if st == "pr":
        return f"# Repo PR opened ✅\n\n- {r['pr']}\n- branch `{r['branch']}` @ {r['commit']}"
    if st == "committed":
        return (f"# Committed to `{r['branch']}` ({r['commit']}) ✅\n\n"
                f"- files: {', '.join(r['files'])}\n- open the PR: `gh pr create --head {r['branch']}`")
    if st == "written":
        return f"# Files edited in place\n\n- {r['note']}\n- {', '.join(r['files'])}"
    # queued / planned
    L = [f"# Repo change — {st}", f"_{r['reason']}_", ""]
    for e in r["edits"]:
        L += [f"## {e['file']}", "```diff", (e["diff"] or "(no change)")[:1500], "```"]
    return "\n".join(L)
