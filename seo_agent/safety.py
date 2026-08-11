"""Fork-safety — the first onboarding stage, run before anything writes files.
The skill repo is public (MIT); a careless setup could leak the operator's keys
to every fork. This module guarantees it can't:

  - writes a committed `.env.example` (placeholders only) + hardens `.gitignore`
  - LEAK-SCANS tracked files AND the working tree (regex) — .gitignore only
    protects *untracked* files, so scanning is not optional
  - checks no real config.json / service-account / .env is git-tracked
  - can install a stdlib pre-commit hook that re-runs the scan

Everything is stdlib. `check()` returns a verdict; nothing here transmits data."""
import re
import subprocess
from pathlib import Path

from . import integrations

# .env.example is generated from the integrations registry (integrations.env_example)
# so it never drifts from the code — adding an API updates the template automatically.

GITIGNORE = [
    "# Python", "__pycache__/", "*.pyc", "*.egg-info/", "build/", "dist/", ".venv/", "",
    "# Secrets — NEVER commit (public repo)", ".env", ".env.*", "*.env", "!.env.example",
    "config.json", "*service-account*.json", "*-credentials.json", "gsc-service-account.json", "",
    "# Per-site working data + generated outputs", "corpus.json", "corpus.prev.json",
    "history/", "content/", "state/", "memory/", "site-changes/", "sf-exports/",
    "*.db", "agent.log", "approvals.json", "review-responses.json",
    "recommendations.md", "digest.md", "audit.md", "plan.md", "report.html", "report.pdf",
    "consult.md", "article-plan.md", "BASELINE.md", "SETUP.md",
    "content-queue.json", "next-brief.md", "",
    "# Client-sensitive identity/memory — never in a public fork",
    "CLIENT.md", "MEMORY.md", "", "# OS", ".DS_Store",
]

# Real-secret patterns (not placeholders). Ordered high-signal first.
PATTERNS = [
    ("Anthropic key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{20,}")),
    ("Google service-account private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    # allow an optional closing quote before the separator so JSON ("password": "…") is caught too (SEC-M6)
    ("Assigned secret", re.compile(r"(?i)(api[_-]?key|password|secret|token)['\"]?\s*[:=]\s*['\"][^'\"\s]{12,}['\"]")),
]
_SKIP = re.compile(r"(__pycache__|\.git/|node_modules/|\.venv/|\.png$|\.jpg$|\.pdf$|\.ico$)")


def _git(root, *args):
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                              text=True, timeout=30).stdout
    except Exception:
        return ""


def scan_tree(root="."):
    """Regex leak-scan over the working tree. Returns [(file, kind, snippet)]."""
    hits = []
    for p in Path(root).rglob("*"):
        if not p.is_file() or _SKIP.search(str(p)) or p.name in (".env.example",):
            continue
        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        for kind, rx in PATTERNS:
            m = rx.search(text)
            if m:
                hits.append((str(p.relative_to(root)), kind, m.group(0)[:12] + "…"))
                break
    return hits


def tracked_secrets(root="."):
    """git-tracked files that should never be tracked (real config / creds)."""
    tracked = _git(root, "ls-files").splitlines()
    bad = [f for f in tracked if re.search(
        r"(^|/)(config\.json|\.env$|.*service-account.*\.json|.*-credentials\.json)$", f)]
    return bad


def write_env_example(root=".", force=False):
    p = Path(root) / ".env.example"
    if p.exists() and not force:
        return False
    p.write_text(integrations.env_example())
    return True


def harden_gitignore(root="."):
    p = Path(root) / ".gitignore"
    have = set(l.strip() for l in p.read_text().splitlines()) if p.exists() else set()
    added = [l for l in GITIGNORE if l and not l.startswith("#") and l not in have]
    if added or not p.exists():
        body = ("\n".join(GITIGNORE) if not p.exists()
                else p.read_text().rstrip() + "\n\n# seo-content-pipeline hardening\n" + "\n".join(added))
        p.write_text(body.rstrip() + "\n")
    return added


def precommit_hook(root="."):
    """Install a stdlib pre-commit hook that blocks commits with secrets."""
    hooks = Path(root) / ".git" / "hooks"
    if not hooks.exists():
        return False
    (hooks / "pre-commit").write_text(
        "#!/bin/sh\npython -m seo_agent safety --precommit || exit 1\n")
    (hooks / "pre-commit").chmod(0o755)
    return True


def check(cfg=None, root=".", apply=True):
    """Run the full fork-safety pass. apply=True writes .env.example + .gitignore."""
    actions = []
    if apply:
        if write_env_example(root):
            actions.append("wrote .env.example")
        added = harden_gitignore(root)
        if added:
            actions.append(f"hardened .gitignore (+{len(added)} rules)")
    tracked = tracked_secrets(root)
    leaks = scan_tree(root)
    issues = []
    if tracked:
        issues.append(f"{len(tracked)} secret/config files are git-tracked: {', '.join(tracked[:5])} "
                      f"— untrack with `git rm --cached <file>` (they're now in .gitignore)")
    if leaks:
        issues.append(f"{len(leaks)} files contain what look like real secrets: "
                      + ", ".join(f"{f} ({k})" for f, k, _ in leaks[:5]))
    return {"fork_safe": not issues, "issues": issues, "actions": actions,
            "tracked_secrets": tracked, "leaks": leaks}
