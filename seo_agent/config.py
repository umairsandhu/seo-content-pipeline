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
    "ingest": {"workers": 8},                                   # parallel crawl fetch workers
}


# ── the hand-holding scaffold: every settable key gets a visible slot ────────
# config.json is scaffolded like .env.example: the slot is already there, you just
# fill it. JSON has no comments, so the "_hints" block carries the how-to per key.
TEMPLATE = {
    "site": "https://www.example.com",
    "sitemap": "https://www.example.com/sitemap.xml",
    "include": [],
    "exclude": [],
    "competitors": [],
    "gsc_property": "",
    "gsc_credentials": "",
    "autonomy": "approve",
    "cms": {"type": "file", "dir": "content"},
    "report": {"email_to": [], "from": ""},
    "drive": {"folder_id": "", "credentials": "", "rclone_remote": ""},
    "learning": {"share_cross_site": False},
    "tips": True,
    "agent": {"interval": 600, "hour": 8, "report_weekday": 4, "sf_crawl": False},
    "crawl": {"mode": "auto", "delay": 0.15},
    "llm": {"provider": "agent", "model": ""},
    "render": {"enabled": False},
    "max_pages": 400,
    "ingest": {"workers": 8},
    "speed": {"strategy": "mobile", "max_urls": 10},
    "audit": {"title_max": 60, "thin_words": 300, "max_depth": 4},
    "aio": {"target_pos": 3},
    "pillars": {},
    "history_dir": "history",
    "review": {"channels": []},
    "rank": {"keywords": [], "max": 50},
    "logs": {"path": ""},
    "brand": {"name": "Site"},
    "dataforseo": {"location_name": "United States", "language_name": "English"},
}
HINTS = {
    "site": "your site, with https:// (one workspace folder = one site)",
    "sitemap": "usually <site>/sitemap.xml — check robots.txt if unsure",
    "include": 'content sections to analyze, e.g. ["/blog/"] — empty = crawl everything',
    "competitors": '2-3 competitor domains, e.g. ["rival.com"] — unlocks gap/backlink analysis',
    "gsc_property": 'EXACTLY as it appears in Search Console: "sc-domain:example.com" or "https://www.example.com/"',
    "gsc_credentials": "path to your Google service-account JSON — just save it here as "
                       "gsc-credentials.json (git-ignored) and it is AUTO-DETECTED; then share the "
                       "GSC property with the service account's email (GSC → Settings → Users → Add user). "
                       "No service account? Skip it: `gsc --csv <export.zip>` works too",
    "autonomy": '"manual" (plan only) · "approve" (queue for your OK — recommended) · "auto"',
    "cms": "where changes/posts ship — run `cms` to see all 13 options + their env vars/keys",
    "report": 'email_to: who gets the PDF reports, e.g. ["you@co.com"] (+ SMTP_* or RESEND_API_KEY in .env)',
    "drive": "Google Drive delivery: folder_id of the client folder (share it with your service "
             "account email); credentials falls back to gsc_credentials; or an rclone_remote",
    "learning": "share_cross_site: true = contribute anonymized change-type stats to your own "
                "machine-wide store so every workspace learns from the others (opt-in)",
    "tips": "one sourced SEO tidbit per day after commands / on the dashboard — false to disable",
    "agent": "the always-on daemon (`agent`): heartbeat seconds, daily-cycle hour, weekly report "
             "day (Fri=4), sf_crawl: true = weekly headless Screaming Frog pull. Background: "
             "`agent --background` · boot-persistent: `agent --install`",
    "crawl": 'mode: "auto" (profiler picks sitemap vs link-following spider) | "sitemap" | "spider"; '
             "delay = politeness seconds (robots Crawl-delay always honored). "
             "`profile` auto-detects the platform + rendering needs; `profile --apply` writes these",
    "llm": 'who writes headlessly: "agent" (Claude drives — recommended, no key) | "ollama" '
           '(local OSS) | "anthropic" | "openai" — the wizard asks',
    "render": "enabled: true = JavaScript rendering via Playwright (the profiler auto-enables "
              "when the site is client-rendered and Playwright is installed)",
    "max_pages": "crawl cap per ingest (profiler sizes it from the sitemap)",
    "ingest": "workers: parallel fetchers (profiler sizes; lower on shared hosting)",
    "speed": 'strategy: "mobile"|"desktop"; max_urls: CWV sample size (smart-sampled: homepage + '
             "money pages + one per template)",
    "audit": "Site Doctor thresholds (title_max, thin_words, max_depth …) — defaults are sane",
    "aio": "AI-Overview CTR model: target_pos for forecasting",
    "pillars": 'hub pages to funnel internal links into, e.g. {"/shop": "storefront"}',
    "history_dir": "where dated snapshots live (default history/) — attribution feeds on these",
    "review": 'extra approval channels, e.g. ["slack"] (SLACK_WEBHOOK_URL in .env) — CLI/dashboard always work',
    "rank": "keywords to track daily/weekly, e.g. {\"keywords\": [\"best crm\"], \"max\": 50}",
    "logs": "path to a server access log (crawl-budget + AI-crawler analysis)",
    "brand": "name used in reports; secrets NEVER go here — they live in .env",
    "dataforseo": "market for volumes/SERPs (login/password go in .env, not here)",
    "_more": "any key in seo_agent/config.py DEFAULTS can also be overridden here",
}

_CRED_GUESSES = ("gsc-credentials.json", "service-account.json", "google-credentials.json",
                 "gsc-service-account.json")


def scaffold(site=None):
    """A complete config for a new workspace — every slot visible, hints inline."""
    cfg = json.loads(json.dumps(TEMPLATE))  # deep copy
    if site:
        s = site.rstrip("/")
        cfg["site"], cfg["sitemap"] = s, s + "/sitemap.xml"
    cfg["_hints"] = HINTS
    return cfg


def ensure_keys(path="config.json"):
    """Add any missing template slots to an existing config.json (values preserved).
    Returns the list of keys added — this is `config --fix`."""
    p = Path(path)
    cur = json.load(open(p)) if p.exists() else {}
    added = []
    for k, v in TEMPLATE.items():
        if k not in cur:
            cur[k] = json.loads(json.dumps(v))
            added.append(k)
        elif isinstance(v, dict) and isinstance(cur.get(k), dict):
            for k2, v2 in v.items():
                if k2 not in cur[k]:
                    cur[k][k2] = json.loads(json.dumps(v2))
                    added.append(f"{k}.{k2}")
    cur["_hints"] = HINTS
    p.write_text(json.dumps(cur, indent=2) + "\n")
    return added


_TRANSIENT = ("_dfs_login", "_dfs_password")   # env-sourced secrets injected by load(); never persist


def persistable(cfg):
    """A copy of cfg safe to write to config.json — strips env-sourced secrets that
    load() injects, so wizard/scaffold can't leak them to disk (SEC-M6)."""
    return {k: v for k, v in cfg.items() if k not in _TRANSIENT}


def detect_gsc_credentials():
    """Zero-config: a service-account JSON dropped in the workspace is found by name."""
    for name in _CRED_GUESSES:
        if Path(name).exists():
            return name
    for p in sorted(Path(".").glob("*service*account*.json")) + sorted(Path(".").glob("*credentials*.json")):
        return str(p)
    return None


def service_account_email(path):
    """The email to share the GSC property / Drive folder with (from the key file)."""
    try:
        return json.load(open(path)).get("client_email")
    except Exception:
        return None


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
    if not cfg.get("gsc_credentials"):  # hand-holding: a key file in the folder just works
        found = detect_gsc_credentials()
        if found:
            cfg["gsc_credentials"] = found
    return cfg
