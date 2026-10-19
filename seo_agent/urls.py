"""URL structure — does the address name the page? (Site Doctor category `url`.)

Added after a real run (superx.pk, 2026-10-19): the audit passed 38 sector pages at
/sectors/0801/ while each one's title said "Automobile Assembler …". Nothing in the tool
looked at the path itself. The operator found it by eye. LEARNINGS #23 says a miss a human
catches is encoded the same day; this module is that encoding (LEARNINGS #29).

What it reports, grouped by URL TEMPLATE so 721 ticker pages are one finding, not 721:
  - opaque segments: a path segment that is a bare number (an ID or an internal code, not a
    year). A reader, a SERP and an answer engine see an address that names nothing. The fix
    is a slug made from the page's name plus a 301 from the old address. med.
  - mixed case: a path with capitals. Not wrong by itself (a ticker is written in capitals),
    but URLs are case-sensitive, so the lowercase form people type must 301 to the page. With
    probing on, one example per template is requested in lower case; a 404 raises it to med.
  - the other slash form: with probing on, one example per template is requested without (or
    with) its trailing slash. Some hosts match redirect rules exactly — on Cloudflare Pages a
    rule written for `/a` does not fire for `/a/` — so a 404 there is a med finding.
  - a year in the slug that the title does not carry: the address dates a page the title
    keeps current. low.
  - underscores, slugs over 75 characters or 10 words, query strings on indexable URLs. low.
  - a multi-word slug that shares no word with the title or H1 (the address was written for
    another page, or the page was rewritten and the address kept). low.

Probing is bounded (at most 2 requests per template, 6 templates) and can be switched off with
config `url_audit.probe: false`; tests run it off. Nothing here is fatal to the audit.
"""
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

OPAQUE = re.compile(r"^\d{3,}$")
YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
WORD = re.compile(r"[a-z0-9]+")
MAX_PROBED_TEMPLATES = 6


def _indexable(c):
    return (c.get("status") or 200) == 200 and "noindex" not in (c.get("robots") or "").lower()


def _segs(path):
    return [s for s in path.split("/") if s]


def _template(segs, test, slash):
    t = "/" + "/".join("{id}" if test(s) else s for s in segs)
    return t + ("/" if slash and segs else "")


def slugify(text):
    """'Automobile Assembler stocks on PSX' → 'automobile-assembler-stocks-on-psx'."""
    return "-".join(WORD.findall(text.lower().replace("&", " and ")))


def _status(url, timeout):
    """Status of one request, redirects NOT followed (a 301 is an answer, not a hop)."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "seo-agent url audit"})
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def _name_of(c):
    h1 = c.get("h1")
    h1 = h1[0] if isinstance(h1, list) and h1 else h1
    return (h1 or c.get("title") or "").strip()


def check(cfg, corpus, probe=None, timeout=10):
    opt = cfg.get("url_audit", {}) if isinstance(cfg, dict) else {}
    probe = opt.get("probe", True) if probe is None else probe
    F = []
    opaque, upper = defaultdict(list), defaultdict(list)
    underscore, long_, year_only, params, no_overlap = [], [], [], [], []
    for c in corpus:
        if not _indexable(c):
            continue
        url = c.get("url") or ""
        p = urllib.parse.urlparse(url)
        segs = _segs(p.path)
        slash = p.path.endswith("/")
        if p.query:
            params.append(url)
        if not segs:
            continue
        name = " ".join(filter(None, [c.get("title") or "", _name_of(c)])).lower()
        named = set(WORD.findall(name))

        # A number is opaque only when the page's own name does not carry it: ticker 786
        # (786 Investments) IS the name; sector code 0801 ("Automobile Assembler") is not.
        def is_opaque(s):
            return bool(OPAQUE.match(s)) and not YEAR.fullmatch(s) and s not in named
        if any(is_opaque(s) for s in segs):
            opaque[_template(segs, is_opaque, slash)].append(c)
            continue  # the slug is the defect; the other checks would only restate it
        if re.search(r"[A-Z]", p.path):
            upper[_template(segs, lambda s: bool(re.search(r"[A-Z]", s)), slash)].append(c)
        last = segs[-1]
        words = WORD.findall(last.lower())
        if "_" in last:
            underscore.append(url)
        if len(last) > 75 or len(words) > 10:
            long_.append(url)
        years = set(YEAR.findall(last))
        if years and not any(y in name for y in years):
            year_only.append(url)
        stem = lambda w: w[:-1] if len(w) > 3 and w.endswith("s") else w  # ipo ~ ipos
        if len(words) >= 2 and name and not {stem(w) for w in words} & {stem(w) for w in named}:
            no_overlap.append(url)

    probed = 0
    for tmpl, cs in sorted(opaque.items(), key=lambda kv: -len(kv[1])):
        ex = cs[0]
        suggest = slugify(_name_of(ex))[:60].rstrip("-")
        F.append({"cat": "url", "sev": "med", "url": ex["url"],
                  "msg": f"{len(cs)} page(s) at {tmpl} — the address is a number and names nothing "
                         f"(this one is “{_name_of(ex)[:60]}”); move to a slug from the name"
                         + (f" (e.g. …/{suggest}/)" if suggest else "") + " and 301 the old address"})
    for tmpl, cs in sorted(upper.items(), key=lambda kv: -len(kv[1])):
        ex = cs[0]["url"]
        sev, note = "low", "URLs are case-sensitive: make sure the lowercase form 301s here"
        if probe and probed < MAX_PROBED_TEMPLATES:
            probed += 1
            p = urllib.parse.urlparse(ex)
            st = _status(p._replace(path=p.path.lower()).geturl(), timeout)
            if st == 404:
                sev, note = "med", f"the lowercase form ({p.path.lower()}) returns 404 — 301 it to this page"
            elif st in (301, 308):
                note = "the lowercase form redirects (good)"
        F.append({"cat": "url", "sev": sev, "url": ex,
                  "msg": f"{len(cs)} page(s) at {tmpl} use capitals in the path — {note}"})
    if probe:
        seen = 0
        for cs in sorted(list(opaque.values()) + list(upper.values()), key=len, reverse=True):
            if seen >= MAX_PROBED_TEMPLATES:
                break
            seen += 1
            p = urllib.parse.urlparse(cs[0]["url"])
            other = p.path[:-1] if p.path.endswith("/") else p.path + "/"
            st = _status(p._replace(path=other).geturl(), timeout)
            if st == 404:
                F.append({"cat": "url", "sev": "med", "url": cs[0]["url"],
                          "msg": f"the other slash form ({other}) returns 404 — this host matches "
                                 "paths exactly, so write each redirect rule in both forms"})
    for lst, sev, msg in (
        (year_only, "low", "slug carries a year the title does not — the address dates the page"),
        (underscore, "low", "underscore in the slug — use hyphens (Google reads _ as a joiner)"),
        (long_, "low", "slug over 75 characters or 10 words — trim it to the query"),
        (params, "low", "indexable URL with a query string — canonicalise to the clean path"),
        (no_overlap, "low", "slug shares no word with the title or H1 — the address names another page"),
    ):
        if lst:
            F.append({"cat": "url", "sev": sev, "url": lst[0],
                      "msg": f"{len(lst)} page(s): {msg}" + (f" (also {lst[1]})" if len(lst) > 1 else "")})
    return F
