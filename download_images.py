#!/usr/bin/env python3
"""
download_images.py  (v2 – multi-source)
----------------------------------------
Sources tried in order for each location:
  1. Wikimedia Commons Category API
  2. Wikimedia Commons Search API
  3. Flickr public feed (no API key required, CC-licensed photos)

Output:
  images/{key}/img_01.jpg  ...
  images_manifest.js  ->  window.IMG_DATA = { key: [{src, cap}], ... }

Run:   python download_images.py
Re-run is safe: existing files are skipped automatically.
"""

import urllib.request
import urllib.error
import urllib.parse
import json
import os
import time

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
IMG_DIR   = os.path.join(BASE_DIR, "images")
WM_API    = "https://commons.wikimedia.org/w/api.php"
FL_FEED   = "https://www.flickr.com/services/feeds/photos_public.gne"
THUMB_W   = 600
OK_MIME   = {"image/jpeg", "image/png", "image/webp"}

# =====================================================================
#  Place definitions
#  key     = must match HTML plans data
#  cat     = Wikimedia category (without "Category:")
#  q       = Wikimedia search query
#  flickr  = Flickr tag string (comma-separated = AND search)
#  max     = maximum images to download per location
# =====================================================================
PLACES = [
    # -- Plan 1: Zion -------------------------------------------------
    {"key":"narrows",      "max":7,
     "cat":"The_Narrows_(Zion_National_Park)",
     "q":  "The Narrows Zion National Park river canyon Utah",
     "flickr":"narrows,zion"},
    {"key":"emerald",      "max":5,
     "cat":"Emerald_Pools_(Zion_National_Park)",
     "q":  "Emerald Pools Zion National Park waterfall",
     "flickr":"emerald+pools,zion"},
    {"key":"overlook",     "max":5,
     "cat":None,
     "q":  "Canyon Overlook Trail Zion National Park Utah",
     "flickr":"canyon+overlook,zion"},
    {"key":"angels",       "max":5,
     "cat":"Angels_Landing",
     "q":  "Angels Landing Zion National Park Utah summit",
     "flickr":"angels+landing,zion"},
    {"key":"kolob",        "max":6,
     "cat":"Kolob_Canyons",
     "q":  "Kolob Canyons Zion National Park red cliffs",
     "flickr":"kolob,zion"},
    {"key":"checkerboard", "max":4,
     "cat":None,
     "q":  "Checkerboard Mesa East Zion sandstone Utah",
     "flickr":"checkerboard+mesa,zion"},

    # -- Plan 2: Flagstaff - Sedona -----------------------------------
    {"key":"walnut",       "max":5,
     "cat":"Walnut_Canyon_National_Monument",
     "q":  "Walnut Canyon National Monument Arizona cliff dwellings",
     "flickr":"walnut+canyon,arizona"},
    {"key":"sfpeaks",      "max":5,
     "cat":None,
     "q":  "San Francisco Peaks Flagstaff Arizona Coconino forest mountain",
     "flickr":"san+francisco+peaks,flagstaff"},
    {"key":"cathedral",    "max":6,
     "cat":None,
     "q":  "Cathedral Rock Bell Rock Sedona Arizona red butte",
     "flickr":"cathedral+rock,sedona"},
    {"key":"sliderock",    "max":5,
     "cat":"Slide_Rock_State_Park",
     "q":  "Slide Rock State Park Oak Creek Canyon Arizona",
     "flickr":"slide+rock,arizona"},
    {"key":"sunsetcrat",   "max":6,
     "cat":"Sunset_Crater_Volcano_National_Monument",
     "q":  "Sunset Crater Volcano National Monument Arizona",
     "flickr":"sunset+crater,arizona"},
    {"key":"wupatki",      "max":5,
     "cat":"Wupatki_National_Monument",
     "q":  "Wupatki Pueblo ruins Arizona Sinagua ancient",
     "flickr":"wupatki,arizona"},
    {"key":"humphreys",    "max":5,
     "cat":None,
     "q":  "Humphreys Peak San Francisco Peaks Arizona mountain summit",
     "flickr":"humphreys+peak,arizona"},
    {"key":"meteor",       "max":4,
     "cat":None,
     "q":  "Meteor Crater Barringer Crater Arizona impact desert",
     "flickr":"meteor+crater,arizona"},

    # -- Plan 3: Cloudcroft ------------------------------------------
    {"key":"cloudcroft",   "max":5,
     "cat":None,
     "q":  "Cloudcroft New Mexico mountain village pine forest",
     "flickr":"cloudcroft"},
    {"key":"sacramento",   "max":4,
     "cat":None,
     "q":  "Sacramento Mountains New Mexico ponderosa pine forest",
     "flickr":"sacramento+mountains"},
    {"key":"trestle",      "max":4,
     "cat":"Mexican_Canyon_Trestle",
     "q":  "Mexican Canyon Trestle wooden railroad bridge Cloudcroft",
     "flickr":"trestle,cloudcroft"},
    {"key":"rimtrail",     "max":5,
     "cat":None,
     "q":  "Lincoln National Forest Cloudcroft trail trees New Mexico",
     "flickr":"lincoln+national+forest"},
    {"key":"sunspot",      "max":5,
     "cat":"Sunspot_Solar_Observatory",
     "q":  "Sunspot Solar Observatory Sacramento Peak telescope New Mexico",
     "flickr":"sunspot+observatory"},
    {"key":"whitesands",   "max":7,
     "cat":None,
     "q":  "White Sands National Park gypsum dunes desert New Mexico",
     "flickr":"white+sands,national+park"},
    {"key":"cloudmorn",    "max":4,
     "cat":None,
     "q":  "Cloudcroft forest trees New Mexico Otero County",
     "flickr":"cloudcroft,forest"},

    # -- Plan 4: Jemez - Valles - Bandelier --------------------------
    {"key":"jemezfalls",   "max":5,
     "cat":"Jemez_Falls",
     "q":  "Jemez Falls waterfall New Mexico cascade canyon",
     "flickr":"jemez+falls"},
    {"key":"jemezmtn",     "max":4,
     "cat":None,
     "q":  "Jemez Mountains Las Conchas creek canyon New Mexico",
     "flickr":"jemez+mountains"},
    {"key":"valles",       "max":6,
     "cat":"Valles_Caldera_National_Preserve",
     "q":  "Valles Caldera National Preserve New Mexico volcano meadow",
     "flickr":"valles+caldera"},
    {"key":"bandelier",    "max":5,
     "cat":"Bandelier_National_Monument",
     "q":  "Bandelier National Monument cliff dwellings pueblo New Mexico",
     "flickr":"bandelier,new+mexico"},
    {"key":"gilman",       "max":4,
     "cat":"Gilman_Tunnels",
     "q":  "Gilman Tunnels New Mexico Jemez River canyon rock cut",
     "flickr":"gilman+tunnels"},
    {"key":"battleship",   "max":4,
     "cat":None,
     "q":  "Battleship Rock New Mexico Jemez volcanic monolith",
     "flickr":"battleship+rock,new+mexico"},
]

# =====================================================================
#  HTTP
# =====================================================================
HEADERS = {
    "User-Agent":      "AgapeCampingPlan/2.0 (educational, non-commercial)",
    "Accept-Encoding": "identity",
}

def http_get(url: str, extra_headers=None) -> bytes:
    """GET with 429 retry + exponential back-off."""
    headers = dict(HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    delay = 12
    for attempt in range(4):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                print(f"    [429] rate-limited, waiting {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
            else:
                raise
    return b""


def api_get(params: dict) -> dict:
    params = dict(params)
    params["format"] = "json"
    params["origin"] = "*"
    url = WM_API + "?" + urllib.parse.urlencode(params)
    raw = http_get(url)
    return json.loads(raw.decode("utf-8")) if raw else {}


# =====================================================================
#  Wikimedia helpers
# =====================================================================
def fetch_wm_pages(params: dict, max_n: int) -> list:
    try:
        data = api_get(params)
        pages = list(data.get("query", {}).get("pages", {}).values())
        good = []
        for p in pages:
            ii = (p.get("imageinfo") or [{}])[0]
            if ii.get("mime", "") in OK_MIME and ii.get("thumburl"):
                good.append({
                    "title": p["title"],
                    "src":   ii["thumburl"],
                    "mime":  ii["mime"],
                    "from":  "wikimedia"
                })
        return good[:max_n]
    except Exception as exc:
        print(f"    [!] Wikimedia API error: {exc}")
        return []


def wm_from_cat(cat: str, max_n: int) -> list:
    return fetch_wm_pages({
        "action":    "query",
        "generator": "categorymembers",
        "gcmtitle":  "Category:" + cat,
        "gcmtype":   "file",
        "gcmlimit":  str(min(max_n * 3, 50)),
        "prop":      "imageinfo",
        "iiprop":    "url|mime",
        "iiurlwidth": str(THUMB_W),
    }, max_n)


def wm_from_search(q: str, max_n: int) -> list:
    return fetch_wm_pages({
        "action":       "query",
        "generator":    "search",
        "gsrnamespace": "6",
        "gsrsearch":    q,
        "gsrlimit":     str(min(max_n * 6, 50)),
        "prop":         "imageinfo",
        "iiprop":       "url|mime",
        "iiurlwidth":   str(THUMB_W),
    }, max_n)


# =====================================================================
#  Flickr public feed (no API key needed)
# =====================================================================
def flickr_from_tags(tags: str, max_n: int) -> list:
    """
    Uses Flickr public feed – returns most-recent public photos
    tagged with all the provided tags (comma-separated = AND).
    Photos are served at _b (1024px large) size.
    """
    params = {
        "tags":          tags,
        "tagmode":       "all",
        "format":        "json",
        "nojsoncallback": "1",
        "lang":          "en-us",
    }
    url = FL_FEED + "?" + urllib.parse.urlencode(params)
    try:
        raw  = http_get(url, extra_headers={"Referer": "https://www.flickr.com/"})
        data = json.loads(raw.decode("utf-8"))
        items = data.get("items", [])
        good = []
        for item in items:
            m_url = item.get("media", {}).get("m", "")
            if not m_url:
                continue
            # Prefer large (_b = 1024px); _m is fallback (240px)
            b_url = m_url.replace("_m.", "_b.")
            title = item.get("title", "")[:60].strip() or "Flickr photo"
            good.append({"src": b_url, "title": title, "from": "flickr"})
        return good[:max_n]
    except Exception as exc:
        print(f"    [!] Flickr error: {exc}")
        return []


# =====================================================================
#  Download
# =====================================================================
def download_file(url: str, path: str) -> bool:
    """Download url -> path. Retry once if 429."""
    for attempt in range(2):
        try:
            raw = http_get(url)
            if len(raw) < 2000:
                return False
            with open(path, "wb") as f:
                f.write(raw)
            return True
        except urllib.error.HTTPError as e:
            if attempt == 0 and e.code in (404, 403):
                return False   # file does not exist at this size
            if attempt == 0 and e.code == 429:
                print("    [429] download rate-limited, waiting 15s...")
                time.sleep(15)
            else:
                print(f"    [!] HTTP {e.code} for {url[:60]}")
                return False
        except Exception as exc:
            print(f"    [!] Download error: {exc}")
            return False
    return False


def clean_cap(title: str, source: str = "wikimedia") -> str:
    if source == "wikimedia":
        s = title.removeprefix("File:").replace("_", " ")
        for ext in (".jpg",".jpeg",".png",".webp",".tif",".tiff",".JPG",".JPEG",".PNG"):
            if s.endswith(ext):
                s = s[:-len(ext)]
    else:
        s = title
    return s.strip()[:60]


# =====================================================================
#  Manifest  (written incrementally so partial runs aren't lost)
# =====================================================================
MANIFEST_PATH = os.path.join(BASE_DIR, "images_manifest.js")

def load_manifest() -> dict:
    """Load existing manifest or return empty dict."""
    if not os.path.exists(MANIFEST_PATH):
        return {}
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            txt = f.read()
        # strip JS wrapper
        txt = txt.partition("window.IMG_DATA = ")[2].rstrip().rstrip(";")
        return json.loads(txt) if txt else {}
    except Exception:
        return {}

def save_manifest(manifest: dict):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        f.write("/* Auto-generated by download_images.py -- do not edit manually */\n")
        f.write("/* Regenerate: python download_images.py */\n")
        f.write("window.IMG_DATA = ")
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write(";\n")


# =====================================================================
#  Main
# =====================================================================
def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    manifest   = load_manifest()   # preserve existing entries
    total_dl   = 0
    total_skip = 0
    total_fail = 0

    for idx, place in enumerate(PLACES):
        key   = place["key"]
        max_n = place["max"]
        print(f"\n[{idx+1}/{len(PLACES)}] {key}  (need {max_n} imgs)")

        place_dir = os.path.join(IMG_DIR, key)
        os.makedirs(place_dir, exist_ok=True)

        # --- count already-downloaded files
        existing = sorted(
            f for f in os.listdir(place_dir)
            if f.lower().endswith((".jpg",".jpeg",".png"))
        )
        if len(existing) >= max_n:
            print(f"  [=] Already have {len(existing)} images, skipping API calls")
            manifest[key] = [
                {"src": f"images/{key}/{f}", "cap": f.rsplit(".",1)[0].replace("_"," ")}
                for f in existing
            ]
            save_manifest(manifest)
            continue

        # --- Step 1: Wikimedia Category
        cands: list = []
        if place.get("cat"):
            cands = wm_from_cat(place["cat"], max_n)
            print(f"  [WM-cat] '{place['cat']}': {len(cands)} found")
            time.sleep(1.2)

        # --- Step 2: Wikimedia Search
        if len(cands) < max(1, max_n // 2) and place.get("q"):
            q_short = place["q"][:55] + ("..." if len(place["q"])>55 else "")
            extra   = wm_from_search(place["q"], max_n)
            seen    = {c["src"] for c in cands}
            cands  += [c for c in extra if c["src"] not in seen]
            cands   = cands[:max_n]
            print(f"  [WM-search] '{q_short}': total {len(cands)}")
            time.sleep(1.2)

        # --- Step 3: Flickr (if still need more images)
        if len(cands) < max(1, max_n // 2) and place.get("flickr"):
            fl_tags  = place["flickr"]
            fl_imgs  = flickr_from_tags(fl_tags, max_n - len(cands))
            seen     = {c["src"] for c in cands}
            added    = 0
            for fi in fl_imgs:
                if fi["src"] not in seen:
                    cands.append(fi)
                    seen.add(fi["src"])
                    added += 1
            cands = cands[:max_n]
            print(f"  [Flickr] tags='{fl_tags}': +{added} (total {len(cands)})")
            time.sleep(1.0)

        if not cands:
            print(f"  [0] No images found from any source -- skipping")
            manifest.setdefault(key, [])
            save_manifest(manifest)
            continue

        # --- Download images
        local: list = []
        for i, img in enumerate(cands):
            ext    = ".jpg"  # Flickr + Wikimedia both typically JPEG
            fname  = f"img_{i+1:02d}{ext}"
            fpath  = os.path.join(place_dir, fname)
            rel    = f"images/{key}/{fname}"
            source = img.get("from","wikimedia")

            if os.path.exists(fpath) and os.path.getsize(fpath) > 2000:
                print(f"  [=] skip  {fname}")
                local.append({"src": rel, "cap": clean_cap(img.get("title",""), source)})
                total_skip += 1
            else:
                ok = download_file(img["src"], fpath)
                if ok:
                    sz = os.path.getsize(fpath) // 1024
                    src_tag = "flickr" if source=="flickr" else "wiki"
                    print(f"  [+] {fname}  {sz}KB  [{src_tag}]")
                    local.append({"src": rel, "cap": clean_cap(img.get("title",""), source)})
                    total_dl += 1
                else:
                    print(f"  [x] FAIL  {fname}  ({img['src'][:60]})")
                    total_fail += 1
                time.sleep(1.0)   # be polite to servers

        manifest[key] = local
        save_manifest(manifest)   # write after each location
        print(f"  --> {len(local)}/{max_n} images ready")

    # Final summary
    print(f"\n{'='*60}")
    print(f"[OK] New downloads : {total_dl}")
    print(f"[OK] Skipped       : {total_skip}  (already existed)")
    print(f"[!!] Failed        : {total_fail}")
    total = sum(len(v) for v in manifest.values())
    print(f"[OK] Total local   : {total} images across {len(manifest)} locations")
    print(f"[OK] Manifest      : {MANIFEST_PATH}")
    print(f"{'='*60}")
    print("Open ke-hoach-cam-trai-mua-he-hoi-thanh-cap-nhat-v3.html")


if __name__ == "__main__":
    main()
