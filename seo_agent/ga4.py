"""GA4 connector — organic *revenue* and conversions, so the executive one-pager reports
business outcomes, not just clicks. Closes the "correlation theater" gap: pair GSC
(clicks/position) with GA4 (sessions → conversions → revenue) for the organic channel.

Needs a service account (reuse the GSC one) added to the GA4 property with Viewer
access, the Analytics Data API enabled, and `ga4_property_id` in config (or
GA4_PROPERTY_ID). Degrades to a clear 'not configured' when absent. Site-agnostic."""
import datetime
import json
import urllib.request

from . import config as cfgmod  # noqa: F401  (kept for symmetry / future config helpers)


def _token(cfg):
    cred = cfg.get("gsc_credentials") or cfg.get("ga4_credentials")
    if not cred:
        return None
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
    except Exception:
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            cred, scopes=["https://www.googleapis.com/auth/analytics.readonly"])
        creds.refresh(Request())
        return creds.token
    except Exception:
        return None


def _property(cfg):
    import os
    return cfg.get("ga4_property_id") or os.environ.get("GA4_PROPERTY_ID")


def organic(cfg, days=90):
    """Organic-search sessions, conversions, and revenue for the last `days`."""
    prop, token = _property(cfg), _token(cfg)
    if not prop:
        return {"error": "set ga4_property_id (and share the GSC service account with the GA4 property)"}
    if not token:
        return {"error": "GA4 auth failed — needs google-auth + a service account with Analytics access"}
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    body = {"dateRanges": [{"startDate": str(start), "endDate": str(end)}],
            "dimensions": [{"name": "sessionDefaultChannelGroup"}],
            "metrics": [{"name": "sessions"}, {"name": "conversions"}, {"name": "totalRevenue"}],
            "dimensionFilter": {"filter": {"fieldName": "sessionDefaultChannelGroup",
                                           "stringFilter": {"value": "Organic Search"}}}}
    req = urllib.request.Request(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.load(r)
    except Exception as e:
        return {"error": f"GA4 request failed: {e}"}
    row = (data.get("rows") or [{}])[0].get("metricValues", []) if data.get("rows") else []
    v = [m.get("value") for m in row] + ["0", "0", "0"]
    return {"days": days, "sessions": int(float(v[0])), "conversions": round(float(v[1]), 1),
            "revenue": round(float(v[2]), 2)}


def render_md(cfg, r):
    if r.get("error"):
        return f"# GA4 organic outcomes\n\n_{r['error']}_"
    return (f"# GA4 — organic outcomes (last {r['days']}d)\n\n"
            f"- sessions: **{r['sessions']:,}**\n- conversions: **{r['conversions']:,}**\n"
            f"- revenue: **${r['revenue']:,.2f}**\n\n"
            "_Pair with GSC clicks/position for change-level revenue attribution in the ledger._")
