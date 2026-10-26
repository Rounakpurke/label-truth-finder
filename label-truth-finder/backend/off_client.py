"""Open Food Facts / Open Beauty Facts lookups (ODbL data - keep attribution)."""
import datetime as dt
import logging
import re

import requests

from errors import ApiError

log = logging.getLogger(__name__)

SITES = {
    "food": ("Open Food Facts", "https://world.openfoodfacts.org"),
    "beauty": ("Open Beauty Facts", "https://world.openbeautyfacts.org"),
}
FIELDS = ("code,product_name,brands,image_front_url,ingredients_text,nutriments,"
          "allergens_tags,traces_tags,last_modified_t")
# frontend key -> (OFF key, unit)
NUTRI_MAP = {
    "energy": ("energy-kcal_100g", "kcal"), "protein": ("proteins_100g", "g"),
    "carbohydrates": ("carbohydrates_100g", "g"), "sugars": ("sugars_100g", "g"),
    "added_sugars": ("added-sugars_100g", "g"), "fat": ("fat_100g", "g"),
    "saturated_fat": ("saturated-fat_100g", "g"), "trans_fat": ("trans-fat_100g", "g"),
    "fibre": ("fiber_100g", "g"),
}


class OffError(Exception):
    pass


def _headers(cfg):
    return {"User-Agent": f"LabelTruthFinder/0.1 (local prototype; {cfg['OFF_CONTACT']})"}


def _get(cfg, url, params):
    try:
        r = requests.get(url, params=params, headers=_headers(cfg), timeout=cfg["OFF_TIMEOUT"])
    except requests.exceptions.Timeout:
        raise OffError("The online product database (Open Food Facts) timed out.")
    except requests.exceptions.RequestException:
        raise OffError("The online product database could not be reached. Check your internet connection.")
    if r.status_code == 404:
        return None
    if r.status_code >= 400:
        raise OffError(f"The online product database returned an error (HTTP {r.status_code}).")
    try:
        return r.json()
    except ValueError:
        raise OffError("The online product database returned an unreadable response.")


def _fmt(v, unit):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f"{f:g} {unit}"


def _tag_name(tag):
    return tag.split(":", 1)[-1].replace("-", " ").strip().capitalize()


def _normalize(p, site_key):
    site_name, base = SITES[site_key]
    nm = p.get("nutriments") or {}
    nutrition = {"basis": "per 100 g / 100 ml (as stored in the online database)"}
    for k, (off_key, unit) in NUTRI_MAP.items():
        nutrition[k] = _fmt(nm[off_key], unit) if off_key in nm else None
    nutrition["sodium"] = None
    sodium, salt = nm.get("sodium_100g"), nm.get("salt_100g")
    if isinstance(sodium, (int, float)):
        nutrition["sodium"] = _fmt(sodium * 1000, "mg")  # OFF stores sodium in grams
    elif isinstance(salt, (int, float)):
        nutrition["sodium"] = f"{_fmt(salt, 'g')} (salt)"
    has_nutrition = any(v for k, v in nutrition.items() if k != "basis")
    code = str(p.get("code") or "")
    modified = p.get("last_modified_t")
    return {
        "code": code,
        "product_name": (p.get("product_name") or "").strip() or None,
        "brand": (p.get("brands") or "").strip() or None,
        "image_url": p.get("image_front_url") or None,
        "ingredients_text": (p.get("ingredients_text") or "").strip() or None,
        "nutrition": nutrition if has_nutrition else None,
        "allergens": [_tag_name(t) for t in (p.get("allergens_tags") or [])],
        "traces": [_tag_name(t) for t in (p.get("traces_tags") or [])],
        "url": f"{base}/product/{code}" if code else None,
        "source_name": site_name,
        "retrieved": dt.date.today().isoformat(),
        "last_modified": dt.datetime.fromtimestamp(modified, dt.timezone.utc).date().isoformat() if isinstance(modified, (int, float)) else None,
    }


def _site_order(category):
    return ["beauty", "food"] if category in ("Skincare", "Cosmetics") else ["food", "beauty"]


def lookup_barcode(cfg, barcode, category=""):
    """Return a normalized record, or None if no database has this barcode. Raises OffError if all lookups failed."""
    errors = 0
    sites = _site_order(category)
    for key in sites:
        base = SITES[key][1]
        try:
            data = _get(cfg, f"{base}/api/v2/product/{barcode}.json", {"fields": FIELDS})
        except OffError as e:
            errors += 1
            last = e
            continue
        if data and data.get("status") == 1 and isinstance(data.get("product"), dict):
            prod = data["product"]
            prod.setdefault("code", barcode)
            return _normalize(prod, key)
    if errors == len(sites):
        raise last
    return None


def search(cfg, query, category="", limit=10):
    """Search by name. Returns a list of normalized records (possibly empty). Raises OffError on failure."""
    key = _site_order(category)[0]
    base = SITES[key][1]
    data = _get(cfg, f"{base}/cgi/search.pl", {
        "search_terms": query, "search_simple": 1, "action": "process", "json": 1,
        "page_size": limit, "fields": FIELDS})
    products = (data or {}).get("products") or []
    return [_normalize(p, key) for p in products if isinstance(p, dict) and p.get("code")]


def _tokens(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def name_similarity(query, candidate):
    q, c = _tokens(query), _tokens(candidate)
    return len(q & c) / len(q) if q else 0.0


def match_by_name(cfg, name, category="", threshold=0.6):
    """Return the best record only if its name clearly matches; otherwise None (never a silent substitute)."""
    best, best_score = None, 0.0
    for rec in search(cfg, name, category):
        label = f"{rec.get('brand') or ''} {rec.get('product_name') or ''}"
        score = max(name_similarity(name, rec.get("product_name")), name_similarity(name, label))
        if score > best_score:
            best, best_score = rec, score
    return best if best_score >= threshold else None
