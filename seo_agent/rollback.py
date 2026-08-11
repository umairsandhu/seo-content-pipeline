"""Auto-rollback + post-apply verification — the undo reflex an autonomous agent needs
before it runs unattended on a live site (W3 / gate G3).

Three moving parts:
  · CAPTURE — before shipping a meta/content change, snapshot the page's current
    title/meta/H1 from the live HTML so we can restore it (`before_state` on the ledger).
  · VERIFY — after `apply`, re-fetch the page and confirm the change actually landed
    (the new title/meta is present); the ledger row is marked verified 1/0. A change that
    didn't land is not a real change — don't let it pollute attribution.
  · ROLLBACK — `rollback <change_id>` reissues the INVERSE site_control op from the stored
    before_state (autonomy-gated, logged as `rollback:<type>`). `proposals(cfg)` finds
    changes that MEASURED NEGATIVE (holdout-adjusted lift < 0 with the CI excluding zero at
    +28d) and returns rollback proposals; autopilot queues them (approve mode) and feeds the
    losing change-type into the brain as an avoid-lesson.

Reuses the crawler (`ingest.extract`), the ledger, `site_control`, and `learn`. Stdlib +
existing deps only. Site-agnostic."""


def capture(cfg, url):
    """Snapshot a live page's revertable fields before we change them. Degrades to {} if
    the page can't be fetched (then rollback for that change is unavailable, and we say so)."""
    try:
        from . import ingest
        status, final, doc = ingest._fetch(url)
        if not doc:
            return {}
        rec = ingest.extract(final or url, doc)
        return {"title": rec.get("title", ""), "description": rec.get("description", ""),
                "h1": (rec.get("h1") or [""])[0] if rec.get("h1") else "",
                "captured_from": final or url}
    except Exception:
        return {}


def verify(cfg, url, change):
    """Re-fetch the page and confirm the change landed. For meta/content ops we check the
    new title/description is present in the live HTML. Returns True/False/None(unknown)."""
    op = change.get("op") or change.get("type", "")
    want = change.get("title") or change.get("description") or change.get("detail") or ""
    if op not in ("update_meta", "update_content", "retitle") or not want:
        return None
    try:
        from . import ingest
        _s, final, doc = ingest._fetch(url)
        if not doc:
            return None
        rec = ingest.extract(final or url, doc)
        hay = " ".join([rec.get("title", ""), rec.get("description", ""),
                        (rec.get("text", "") or "")[:4000]]).lower()
        return want.strip().lower()[:60] in hay
    except Exception:
        return None


def rollback(cfg, change_id):
    """Reissue the inverse op from the stored before_state — autonomy-gated + logged."""
    from . import ledger, site_control
    ch = ledger.get_change(cfg, change_id)
    if not ch:
        return {"ok": False, "error": f"no change #{change_id}"}
    before = ch.get("before_state")
    if not before:
        return {"ok": False, "error": f"change #{change_id} has no before-state — can't auto-revert "
                                      "(it predates W3, or capture failed). Revert by hand."}
    typ = ch["type"]
    if typ in ("retitle", "update_meta", "fix:meta", "fix:freshness"):
        res = site_control.change(cfg, "update_meta", url=ch["url"],
                                  title=before.get("title", ""), description=before.get("description", ""))
    elif typ in ("update_content", "refresh"):
        res = site_control.change(cfg, "update_content", url=ch["url"],
                                  content=before.get("body") or before.get("title", ""))
    else:
        return {"ok": False, "error": f"change type '{typ}' has no automatic inverse — revert by hand"}
    try:
        ledger.record(cfg, ch["url"], f"rollback:{typ}", f"revert change #{change_id}")
    except Exception:
        pass
    return {"ok": True, "rolled_back": change_id, "result": res}


def proposals(cfg, horizon=28):
    """Changes that MEASURED NEGATIVE at +horizon (holdout-adjusted, CI excludes 0) and are
    still auto-revertable → rollback proposals. This is what autopilot queues/acts on."""
    from . import ledger
    try:
        fus = ledger.followups(cfg)
    except Exception:
        return []
    # per change type, is the horizon's lift confidently negative?
    from . import learn
    loc = learn.local_lessons(cfg)
    losing = {t for t, hs in loc.items()
              if (hs.get(horizon) or {}).get("n", 0) >= 3
              and (hs.get(horizon) or {}).get("mean_lift", 0) < 0
              and ((hs.get(horizon) or {}).get("ci_low", 0) or 0) < 0
              and ((hs.get(horizon) or {}).get("mean_lift", 0) + ((hs.get(horizon) or {}).get("ci95") or 0)) < 0}
    out = []
    for ch in ledger.changes(cfg):
        if (ch["type"] in losing and ch.get("before_state")
                and not ch["type"].startswith("rollback:") and ch["status"] == "applied"):
            v = (loc.get(ch["type"], {}).get(horizon) or {})
            out.append({"change_id": ch["id"], "url": ch["url"], "type": ch["type"],
                        "mean_lift": v.get("mean_lift"), "ci95": v.get("ci95"), "n": v.get("n")})
    # de-dupe by (url,type) — one proposal per page
    seen, uniq = set(), []
    for p in out:
        k = (p["url"], p["type"])
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def render_md(cfg, r=None):
    if r and "rolled_back" in r:
        return f"# Rollback — change #{r['rolled_back']}\n\n- {r['result'].get('status', 'done')}"
    if r and r.get("error"):
        return f"# Rollback\n\n- ⚠ {r['error']}"
    props = proposals(cfg)
    L = [f"# Rollback proposals — {cfg.get('site', 'site')}"]
    if not props:
        L.append("\n_Nothing to revert — no change type is measurably losing at +28d "
                 "(needs n≥3 with the CI below zero). Good._")
    else:
        L += ["", "These change types are **measurably underperforming** (holdout-adjusted, "
              "CI excludes zero). Revert with `rollback <id>`:", "",
              "| id | page | type | +28d lift | n |", "|--:|---|---|--:|--:|"]
        for p in props:
            L.append(f"| {p['change_id']} | {p['url'].rsplit('/', 1)[-1][:28]} | {p['type']} | "
                     f"{p['mean_lift']:+g} ±{p.get('ci95', '?')} | {p['n']} |")
    L.append("\n_Auto-proposed inside every autopilot cycle (queued for your approval in approve "
             "mode). Every revert also teaches the brain to avoid that change type here._")
    return "\n".join(L)
