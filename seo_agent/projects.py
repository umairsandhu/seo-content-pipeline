"""Multi-project registry — run the agency motion: many client sites from one place.
A `projects.json` at the registry root maps name → workspace dir. `status` rolls up
each project's onboarding readiness so you can see, at a glance, which clients are
wired up and which need attention. Each project stays a self-contained, fork-safe
workspace (one dir = one site) — this only indexes them. Site-agnostic; stdlib only."""
import json
from pathlib import Path

from . import config as cfgmod
from . import journey

REGISTRY = "projects.json"


def _load(root="."):
    p = Path(root) / REGISTRY
    if p.exists():
        return json.loads(p.read_text())
    return {"projects": []}


def add(name, directory, root="."):
    reg = _load(root)
    reg["projects"] = [p for p in reg["projects"] if p["name"] != name]
    reg["projects"].append({"name": name, "dir": str(directory)})
    (Path(root) / REGISTRY).write_text(json.dumps(reg, indent=2) + "\n")
    return reg


def status(root="."):
    out = []
    for p in _load(root)["projects"]:
        d = Path(p["dir"])
        try:
            cfg = cfgmod.load(str(d / "config.json"))
            r = journey.readiness(cfg, root=str(d))
            out.append({"name": p["name"], "dir": p["dir"], "site": cfg.get("site"),
                        "score": r["score"], "ready": r["ready"],
                        "missing": r["required_missing"]})
        except Exception as e:
            out.append({"name": p["name"], "dir": p["dir"], "error": str(e)[:80]})
    return out


def render_md(root="."):
    rows = status(root)
    if not rows:
        return ("# Projects\n\n_No projects registered. Add one:_\n"
                "`projects add <name> <workspace-dir>` (or edit projects.json).")
    L = ["# Projects — client portfolio", "", "| project | site | ready | missing |", "|---|---|--:|---|"]
    for r in rows:
        if r.get("error"):
            L.append(f"| {r['name']} | ⚠ {r['error']} | — | — |")
        else:
            flag = "🟢" if r["ready"] else "🔴"
            L.append(f"| {r['name']} | {r['site']} | {flag} {r['score']}/100 | "
                     f"{', '.join(r['missing']) or '—'} |")
    return "\n".join(L)
