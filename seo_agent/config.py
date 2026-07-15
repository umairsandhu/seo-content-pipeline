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
    "competitors": [],            # competitor domains — backlink gap + content gap
    "history_dir": "history",     # time-series snapshot store (Layer 1)
    # Layer 3 drafting. provider "agent" = the agent running the skill writes it
    # (no API key). Set to "anthropic"/"openai" only for headless/cron runs.
    "llm": {"provider": "agent", "model": "claude-opus-4-8", "max_tokens": 8000},
    "cms": {"type": "file", "dir": "content"},                 # publish target (Layer 4)
    "audit": {"title_min": 30, "title_max": 60, "meta_min": 70, "meta_max": 160,
              "thin_words": 300, "min_inbound": 3, "max_depth": 4},   # Site Doctor
    "speed": {"strategy": "mobile", "max_urls": 10},            # PageSpeed/CrUX
    "logs": {"path": None},                                     # server access-log file (#2)
    "aio": {"target_pos": 3, "max_detect": 20},                # AI-Overview CTR model (#1)
    "render": {"enabled": False, "wait": "networkidle", "timeout": 15},   # JS rendering (#4)
    "rank": {"keywords": [], "max": 50},                       # rank + SERP-feature tracking (#5)
}


def _load_dotenv(path=".env"):
    """Minimal, dependency-free .env loader (does not override existing env)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        if v:
            os.environ.setdefault(k.strip(), v)


def load(path="config.json"):
    _load_dotenv()
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
