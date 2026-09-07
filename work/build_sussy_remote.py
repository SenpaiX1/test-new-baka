"""
Rebuild sussybakabois catalog by scraping the live worker:
  https://bakaboiz.jakefirenze778.workers.dev/games/

Strategy:
  1) GET the remote index.html
  2) Parse every card -> (name, icon href, gameSite href)
  3) Concurrently GET each existing gameSite/*.html wrapper and find its iframe
     src (points to ../gamesf/X.html for local games, or an external URL)
  4) HEAD-check every candidate gamesf URL to see what actually exists
  5) HEAD-check every icon (both ./icons and ./images)
  6) Emit catalog.json with ABSOLUTE worker URLs, so we never have to host copies.
"""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = "https://bakaboiz.jakefirenze778.workers.dev/games/"
OUT = Path("/app/frontend/public/sussybakabois")
OUT.mkdir(parents=True, exist_ok=True)

sess = requests.Session()
sess.headers["User-Agent"] = "Mozilla/5.0 (compatible; sussy-catalog-builder/1.0)"

print(f"Fetching {BASE} ...")
idx_html = sess.get(BASE, timeout=30).text
print(f"  {len(idx_html)} bytes")

# --- 1. Parse all cards. ---
CARD_RE = re.compile(
    r"<h1[^>]*>(?P<name>.*?)</h1>"
    r"(?P<mid>.*?)"
    r"<img[^>]*?src=\"(?P<icon>[^\"]+)\""
    r"(?P<mid2>.*?)"
    r"onclick=\"window\.location\.href='gameSite/(?P<game>[^']+)'\"",
    re.DOTALL | re.IGNORECASE,
)

def clean_name(raw):
    raw = re.sub(r"<span[^>]*(?:update-tag|online-tag|new-tag)[^>]*>.*?</span>",
                 "", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = raw.replace("&amp;", "&").replace("&#39;", "'").replace("&nbsp;", " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    if raw.isupper():
        raw = raw.title().replace("'S", "'s")
    return raw

def title_from_filename(fn):
    stem = Path(fn).stem
    stem = re.sub(r"^(cl|gs)", "", stem)
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", stem) or [stem]
    return " ".join(w.capitalize() for w in parts) or stem

# Collect one entry per unique gameSite target (first card wins).
cards = {}   # gameSite_href -> {"name","icon"}
for m in CARD_RE.finditer(idx_html):
    href = m.group("game")
    if href in cards:
        continue
    cards[href] = {
        "name": clean_name(m.group("name")),
        "icon": m.group("icon"),
    }
print(f"Parsed {len(cards)} unique cards from index")

# --- 2. HEAD-check every gameSite wrapper ---
def head(url):
    try:
        r = sess.head(url, timeout=15, allow_redirects=True)
        if r.status_code == 405:  # some workers reject HEAD
            r = sess.get(url, timeout=15, stream=True)
            r.close()
        return r.status_code
    except Exception:
        return 0

def get_text(url):
    try:
        r = sess.get(url, timeout=25)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None

wrapper_urls = {h: BASE + "gameSite/" + h for h in cards}
print(f"HEADing {len(wrapper_urls)} wrapper URLs...")

wrapper_status = {}
with ThreadPoolExecutor(max_workers=32) as pool:
    futs = {pool.submit(head, u): h for h, u in wrapper_urls.items()}
    for f in as_completed(futs):
        wrapper_status[futs[f]] = f.result()

alive_wrappers = [h for h, s in wrapper_status.items() if s == 200]
print(f"  {len(alive_wrappers)} wrappers exist (HTTP 200)")

# --- 3. Fetch each live wrapper and extract its iframe target ---
IFRAME_RE = re.compile(r'<iframe[^>]*src="([^"]+)"', re.S | re.I)
print(f"Fetching {len(alive_wrappers)} wrappers for iframe targets...")

wrapper_target = {}   # gameSite href -> ("gamesf", "clovooo.html") or ("external", "https://...")
NEEDS_WRAPPER_TOKENS = ("sus.ai1490.com/embed", "ip.nowgg.fun", "window.location.search")

def resolve_wrapper(href):
    url = wrapper_urls[href]
    text = get_text(url)
    if text is None:
        return href, None
    m = IFRAME_RE.search(text)
    if m:
        src = m.group(1).strip()
        m2 = re.search(r"gamesf/([^/'\"]+\.html)", src)
        if m2:
            return href, ("gamesf", m2.group(1))
        if src.startswith("http://") or src.startswith("https://"):
            return href, ("external", src)
        # Some srcs are relative to gameSite/ (e.g. "gamesf/foo.html" without ../)
        if src.startswith("./") or "://" not in src and src.endswith(".html"):
            m3 = re.search(r"([A-Za-z0-9_.-]+\.html)$", src)
            if m3:
                return href, ("gamesf", m3.group(1))
    # No iframe: could be a JS-driven wrapper (nowgg cloud, plague inc, roblox)
    if any(tok in text for tok in NEEDS_WRAPPER_TOKENS):
        return href, ("wrapper", href)  # load the wrapper URL itself
    return href, None

with ThreadPoolExecutor(max_workers=32) as pool:
    for fut in as_completed([pool.submit(resolve_wrapper, h) for h in alive_wrappers]):
        h, info = fut.result()
        if info:
            wrapper_target[h] = info

kinds = {}
for _, t in wrapper_target.items():
    kinds[t[0]] = kinds.get(t[0], 0) + 1
print(f"  Resolved: {kinds}")

# --- 4. Verify gamesf targets exist remotely ---
gamesf_needed = sorted({t[1] for t in wrapper_target.values() if t[0] == "gamesf"})
print(f"HEADing {len(gamesf_needed)} gamesf files...")
gamesf_status = {}
with ThreadPoolExecutor(max_workers=32) as pool:
    futs = {pool.submit(head, BASE + "gamesf/" + g): g for g in gamesf_needed}
    for f in as_completed(futs):
        gamesf_status[futs[f]] = f.result()
alive_gamesf = {g for g, s in gamesf_status.items() if s == 200}
print(f"  {len(alive_gamesf)} gamesf files present remotely")

# --- 5. Verify icons; try both /icons/ and /images/ (index uses both) ---
icon_refs = {c["icon"] for c in cards.values() if c["icon"]}
print(f"HEADing {len(icon_refs)} icon URLs...")
icon_ok = {}
def check_icon(ref):
    # ref may be like "icons/foo.png" or "images/foo.jpg" — try as-is first,
    # then fall back to swapping icons<->images.
    ref = ref.lstrip("./")
    candidates = [ref]
    if ref.startswith("icons/"):
        candidates.append("images/" + ref[len("icons/"):])
    elif ref.startswith("images/"):
        candidates.append("icons/" + ref[len("images/"):])
    for c in candidates:
        if head(BASE + c) == 200:
            return ref, BASE + c
    return ref, None
with ThreadPoolExecutor(max_workers=32) as pool:
    for f in as_completed([pool.submit(check_icon, r) for r in icon_refs]):
        ref, url = f.result()
        if url:
            icon_ok[ref] = url

print(f"  {len(icon_ok)}/{len(icon_refs)} icons resolved")

# --- 6. Build catalog with absolute URLs ---
def final_url(kind, target):
    if kind == "gamesf":
        return BASE + "gamesf/" + target
    if kind == "wrapper":
        return BASE + "gameSite/" + target
    return target  # external absolute URL

games = []
seen = set()
for href, card in cards.items():
    info = wrapper_target.get(href)
    if not info:
        continue
    kind, target = info
    if kind == "gamesf" and target not in alive_gamesf:
        continue
    key = (kind, target)
    if key in seen:
        continue
    seen.add(key)
    games.append({
        "id": Path(target).stem if kind != "external" else re.sub(r"[^a-z0-9]+", "-", card["name"].lower()).strip("-") or href,
        "name": card["name"] or title_from_filename(href),
        "cover": icon_ok.get(card["icon"], ""),
        "url": final_url(kind, target),
        "source": kind,
    })

games.sort(key=lambda g: g["name"].lower())
(OUT / "catalog.json").write_text(json.dumps(games, indent=2), encoding="utf-8")

by_kind = {}
for g in games:
    by_kind[g["source"]] = by_kind.get(g["source"], 0) + 1
print(f"\nCatalog written: {len(games)} games total")
for k, n in sorted(by_kind.items()):
    print(f"  {k:10s}: {n}")
print(f"\nSample entries:")
for g in games[:10]:
    print(f"  [{g['source']:8s}] {g['name']:<28s} {g['url'][:90]}")
