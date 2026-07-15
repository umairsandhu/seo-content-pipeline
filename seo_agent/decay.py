"""Layer 2 — Decide. Content decay: compare the latest GSC snapshot to a prior
one and surface queries losing rank + pages losing clicks — the auto-refresh
queue (goals #1, #3). Requires ≥2 GSC snapshots in history/gsc_queries and
history/gsc_pages, which the `gsc` command and orchestrate runs write."""
from . import history


def detect(cfg, pos_drop=1.0, click_drop=1.0):
    out = {"queries": None, "pages": None}

    qp, qc = history.previous(cfg, "gsc_queries"), history.latest(cfg, "gsc_queries")
    if qp and qc:
        d = history.diff_rows(qp["data"], qc["data"], "query", "position")
        # position went UP numerically = ranking got WORSE
        out["queries"] = sorted((m for m in d["moved"] if m["delta"] >= pos_drop),
                                key=lambda m: -m["delta"])[:40]

    pp, pc = history.previous(cfg, "gsc_pages"), history.latest(cfg, "gsc_pages")
    if pp and pc:
        d = history.diff_rows(pp["data"], pc["data"], "page", "clicks")
        out["pages"] = sorted((m for m in d["moved"] if m["delta"] <= -click_drop),
                              key=lambda m: m["delta"])[:40]
    return out
