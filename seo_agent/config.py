"""Config loader for the SEO content pipeline. Site-agnostic: point it at any
domain. Secrets (DataForSEO, GSC) come from env / a key file, never the config."""
import json
import os
from pathlib import Path

DEFAULTS = {
    "site": None,                 # https://www.example.com
    "sitemap": None,              # defaults to <site>/sitemap.xml
    "include": [],                # only ingest URLs whose path starts with one of these ("" = all)
    "exclude": [],                # skip URLs containing any of these
    "max_pages": 400,
    "pillars": {},                # {"/shop": "storefront", ...} — hubs to link into
    "gsc_property": None,         # "sc-domain:example.com" or "https://www.example.com/"
    "gsc_credentials": None,      # path to a Google service-account JSON
    "dataforseo": {"location_name": "United States", "language_name": "English"},
    "brand": {"name": "Site", "navy": "#0B0E33", "green": "#02BC87"},
}


def load(path="config.json"):
    cfg = dict(DEFAULTS)
    p = Path(path)
    if p.exists():
        cfg.update(json.load(open(p)))
    cfg["dataforseo"] = {**DEFAULTS["dataforseo"], **cfg.get("dataforseo", {})}
    cfg["_dfs_login"] = os.environ.get("DATAFORSEO_LOGIN")
    cfg["_dfs_password"] = os.environ.get("DATAFORSEO_PASSWORD")
    if not cfg.get("sitemap") and cfg.get("site"):
        cfg["sitemap"] = cfg["site"].rstrip("/") + "/sitemap.xml"
    return cfg
