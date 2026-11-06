"""Collect one preview image per linked activity/hotel for planner.html.

Each page publishes an og:image - the preview the site itself chose to represent
that page, which is exactly what we want on a card. We fetch that, not an
arbitrary photo scraped from the page, and every card links back to the source.

Artifact pages cannot load images from other hosts, so the files are downloaded,
cropped to a common 3:2 and published alongside the page.

Writes img/<key>.jpg and build/images.json. Keys that fail are reported, not
guessed at - a card with no image simply renders without one.
"""

import io
import json
import pathlib
import re
import sys

import requests
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent.parent
IMG = HERE / "img"
BUILD = HERE / "build"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
HDRS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,image/*,*/*"}

W, H = 640, 426          # 3:2, enough for a 320px-wide card at 2x

TARGETS = {
    # --- Columbia
    "saluda":      "https://www.icrc.net/event/holiday-lights-river-1",
    "wildlights":  "https://www.riverbanks.org/events/wild-lights",
    "fireflies":   "https://www.milb.com/columbia",
    "rink":        "https://www.richlandcountyrecreation.com/360/Glide-Gather-Ice-Skating-Rink",
    "congaree":    "https://www.nps.gov/cong/planyourvisit/Trail-Information.htm",
    # --- Orangeburg
    "xmaswalk":    "https://www.orangeburg.sc.us/edisto-memorial-gardens/childrens-garden-christmas-walk",
    "edisto":      "https://www.orangeburg.sc.us/edisto-memorial-gardens",
    # --- Savannah
    "boatparade":  "https://savannahswaterfront.com/event/lighted-boat-parade/",
    "plantriver":  "https://www.plantriverside.com/savannah-christmas-market/",
    "coastalbg":   "https://coastalbg.uga.edu/2026/10/december-nights-and-holiday-lights-2026/",
    "ferry":       "https://www.catchacat.org/routes/savannah-belles-ferry/",
    "laurelhill":  "https://www.fws.gov/refuge/savannah",
    "drury":       "https://www.druryhotels.com/locations/savannah-ga/drury-plaza-hotel-savannah-pooler",
    # --- Charleston
    "festlights":  "https://www.ccprc.com/holiday-festival-of-lights/",
    "yorktown":    "https://www.patriotspoint.org/visit/",
    "aglow":       "https://scaquarium.org/aquarium-aglow",
    "harborresort": "https://www.charlestonharborresort.com/",
    # --- Southern Pines
    "gardenlights": "https://www.sandhills.edu/horticultural-gardens/garden-of-lights.html",
    "weymouth":    "https://www.ncparks.gov/state-parks/weymouth-woods-sandhills-nature-preserve",
}

META = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](og:image(?::secure_url)?|twitter:image)["\'][^>]*>',
    re.I)
CONTENT = re.compile(r'content=["\']([^"\']+)["\']', re.I)


JUNK = re.compile(r"(logo|icon|sprite|favicon|placeholder|avatar|badge|seal|"
                  r"header|footer|banner-ad|spacer|blank|pixel)", re.I)
IMGSRC = re.compile(r'<img[^>]+?(?:data-src|srcset|src)=["\']([^"\']+)', re.I)


def largest_photo(url, html, session, limit=14):
    """Fallback when a page publishes no og:image: the biggest real photo on it."""
    seen, best = set(), None
    for raw in IMGSRC.findall(html)[:120]:
        src = raw.split()[0].split(",")[0].strip()
        if not src or src.startswith("data:") or JUNK.search(src):
            continue
        full = requests.compat.urljoin(url, src)
        if full in seen:
            continue
        seen.add(full)
        if len(seen) > limit:
            break
        try:
            r = session.get(full, headers={**HDRS, "Referer": url}, timeout=25)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content))
            w, h = im.size
            if w < 520 or h < 300:
                continue
            ar = w / h
            if not 0.8 <= ar <= 3.2:
                continue
            if best is None or w * h > best[1]:
                best = (full, w * h)
        except Exception:
            continue
    return best[0] if best else None


def og_image(url, session):
    r = session.get(url, headers=HDRS, timeout=45, allow_redirects=True)
    r.raise_for_status()
    html = r.text[:400_000]
    for m in META.finditer(html):
        c = CONTENT.search(m.group(0))
        if c:
            return requests.compat.urljoin(r.url, c.group(1).strip())
    return None


def grab(key, url, session, override=None):
    try:
        src = override
        if not src:
            r = session.get(url, headers=HDRS, timeout=45, allow_redirects=True)
            r.raise_for_status()
            html = r.text[:400_000]
            src = None
            for m in META.finditer(html):
                c = CONTENT.search(m.group(0))
                if c:
                    src = requests.compat.urljoin(r.url, c.group(1).strip())
                    break
            if src and JUNK.search(src):
                src = None          # og:image is just the site logo
            if not src:
                src = largest_photo(r.url, html, session)
        if not src:
            return key, None, "no usable image found"
        ir = session.get(src, headers={**HDRS, "Referer": url}, timeout=60)
        ir.raise_for_status()
        im = Image.open(io.BytesIO(ir.content))
        im = im.convert("RGB")
        # centre-crop to 3:2 then resize
        tw, th = W / H, im.width / im.height
        if th > tw:
            nw = int(im.height * tw)
            im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
        else:
            nh = int(im.width / tw)
            im = im.crop((0, 0, im.width, nh))      # keep the top, not the middle
        im = im.resize((W, H), Image.LANCZOS)
        IMG.mkdir(exist_ok=True)
        out = IMG / f"{key}.jpg"
        im.save(out, "JPEG", quality=78, optimize=True, progressive=True)
        return key, {"file": f"img/{key}.jpg", "src": src, "page": url,
                     "kb": round(out.stat().st_size / 1024, 1)}, None
    except Exception as e:
        return key, None, f"{type(e).__name__}: {str(e)[:90]}"


def main():
    BUILD.mkdir(exist_ok=True)
    overrides = {}
    ov = BUILD / "image_overrides.json"
    if ov.exists():
        overrides = json.loads(ov.read_text())

    s = requests.Session()
    got, failed = {}, {}
    for key, url in TARGETS.items():
        k, rec, err = grab(key, url, s, overrides.get(key))
        if rec:
            got[k] = rec
            print(f"  ok    {k:<13} {rec['kb']:>5.1f} KB  {rec['src'][:72]}")
        else:
            failed[k] = err
            print(f"  FAIL  {k:<13} {err}")

    (BUILD / "images.json").write_text(json.dumps(got, indent=2))
    total = sum(r["kb"] for r in got.values())
    print(f"\n{len(got)}/{len(TARGETS)} images, {total:.0f} KB total")
    if failed:
        print("failed:", ", ".join(failed))
        print("-> add a direct image URL per key in build/image_overrides.json "
              "(grab it with the browser) and re-run")
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main())
