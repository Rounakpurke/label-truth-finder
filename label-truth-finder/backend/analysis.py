"""Turns raw model output + online records into the report shape the React frontend expects."""
import datetime as dt
import re

import off_client
import ollama_client
import regulations
from errors import ApiError

NUTRI_LABELS = [("energy", "Calories / energy"), ("protein", "Protein"), ("carbohydrates", "Total carbohydrates"),
                ("sugars", "Total sugars"), ("added_sugars", "Added sugars"), ("fat", "Total fat"),
                ("saturated_fat", "Saturated fat"), ("trans_fat", "Trans fat"), ("fibre", "Dietary fibre"),
                ("sodium", "Sodium / salt")]
NUTRI_KEYS = [k for k, _ in NUTRI_LABELS]
_EMPTY = {"", "null", "none", "n/a", "na", "not available", "not specified", "unknown", "-", "--"}

# ---------------------------------------------------------------- helpers

def clean_str(v, limit=2000):
    if isinstance(v, dict):  # e.g. {"value": 7, "unit": "g"}
        v = " ".join(str(x) for x in (v.get("value"), v.get("unit")) if x not in (None, ""))
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        v = f"{v:g}"
    if not isinstance(v, str):
        return None
    v = re.sub(r"[\x00-\x08\x0b-\x1f]", "", v).strip()
    return None if v.lower() in _EMPTY else v[:limit]


def str_list(v, limit=30):
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        return []
    out = []
    for x in v:
        s = clean_str(x, 300)
        if s and s.lower() not in {o.lower() for o in out}:
            out.append(s)
    return out[:limit]


def valid_gtin(code):
    if not re.fullmatch(r"\d{8}|\d{12,14}", code or ""):
        return False
    digits = [int(c) for c in code]
    check = digits.pop()
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return (10 - total % 10) % 10 == check


def split_ingredients(text, limit=80):
    """Split on commas/semicolons that are not inside brackets."""
    if not text:
        return []
    text = re.sub(r"^\s*ingredients?\s*[:\-]\s*", "", text, flags=re.I).strip().rstrip(".")
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch in ",;" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    out = [re.sub(r"\s+", " ", p).strip(" .") for p in parts]
    return [p for p in out if p][:limit]


def normalize_extraction(raw):
    raw = raw if isinstance(raw, dict) else {}
    nut = raw.get("nutrition") if isinstance(raw.get("nutrition"), dict) else {}
    nutrition = {k: clean_str(nut.get(k), 60) for k in NUTRI_KEYS}
    digits = re.sub(r"\D", "", clean_str(raw.get("barcode"), 30) or "")
    return {
        "product_name": clean_str(raw.get("product_name"), 200),
        "brand": clean_str(raw.get("brand"), 120),
        "barcode": digits or None,
        "ingredients_text": clean_str(raw.get("ingredients_text"), 3000),
        "nutrition": nutrition,
        "nutrition_basis": clean_str(raw.get("nutrition_basis"), 80),
        "declared_allergens": str_list(raw.get("declared_allergens")),
        "may_contain": str_list(raw.get("may_contain")),
        "warnings": str_list(raw.get("warnings")),
        "uncertain_text": str_list(raw.get("uncertain_text")),
    }


# ---------------------------------------------------------------- allergens & sugars

_ALLERGENS = {
    "Cereals containing gluten": ["wheat", "barley", "rye", "oat", "spelt", "kamut", "triticale", "semolina", "maida", "atta", "gluten"],
    "Milk": ["milk", "whey", "casein", "caseinate", "lactose", "butter", "cream", "cheese", "ghee", "curd", "yogurt", "yoghurt", "paneer", "milk solids"],
    "Egg": ["egg", "albumen", "albumin", "lysozyme", "mayonnaise"],
    "Peanut": ["peanut", "groundnut", "arachis"],
    "Tree nuts": ["almond", "cashew", "walnut", "hazelnut", "pistachio", "pecan", "macadamia", "brazil nut"],
    "Soy": ["soy", "soya", "soybean", "tofu", "edamame"],
    "Fish": ["fish", "anchovy", "cod", "salmon", "tuna"],
    "Crustaceans": ["shrimp", "prawn", "crab", "lobster", "crayfish"],
    "Molluscs": ["mollusc", "mollusk", "squid", "oyster", "clam", "mussel"],
    "Sesame": ["sesame", "tahini"],
    "Mustard": ["mustard"],
    "Celery": ["celery"],
    "Lupin": ["lupin"],
    "Sulphites": ["sulphite", "sulfite", "sulphur dioxide", "sulfur dioxide", "metabisulphite", "metabisulfite"],
}
_NON_DAIRY_PREFIX = {"coconut", "soy", "soya", "almond", "oat", "rice", "cashew", "cocoa", "shea", "mango", "kokum",
                     "peanut", "nut", "sesame", "hazelnut", "palm"}


def possible_allergen_matches(text):
    """Naive keyword matches. These are POSSIBLE matches only - never confirmations."""
    if not text:
        return []
    low = text.lower()
    out = []
    for allergen, words in _ALLERGENS.items():
        hits = []
        for w in words:
            for m in re.finditer(rf"(?<![a-z]){re.escape(w)}s?(?![a-z])", low):
                prev = re.findall(r"[a-z]+", low[:m.start()])[-1:] or [""]
                if allergen == "Milk" and w in {"milk", "butter", "cream", "cheese"} and prev[0] in _NON_DAIRY_PREFIX:
                    continue
                if m.group(0).strip() not in hits:
                    hits.append(m.group(0).strip())
        if hits:
            out.append({"allergen": allergen, "matched_text": ", ".join(hits[:4])})
    return out


_SUGARS = ["sugar", "sucrose", "glucose", "fructose", "dextrose", "maltose", "syrup", "honey", "jaggery", "molasses",
           "treacle", "maltodextrin", "invert", "agave", "fruit juice concentrate", "cane juice"]
_SWEETENERS = ["aspartame", "sucralose", "saccharin", "acesulfame", "stevia", "steviol", "sorbitol", "maltitol",
               "xylitol", "erythritol", "mannitol", "isomalt"]


def sugar_sources(names):
    out = []
    for n in names:
        low = n.lower()
        if any(re.search(rf"(?<![a-z]){k}", low) for k in _SUGARS):
            out.append({"name": n, "role": "A sugar or sugar-based sweetener. The ingredient list does not say how much."})
        elif any(k in low for k in _SWEETENERS):
            out.append({"name": n, "role": "A sweetener (not a sugar). The ingredient list does not say how much."})
    return out


# ---------------------------------------------------------------- comparison

def _num_unit(s):
    m = re.search(r"([\d]+(?:[.,]\d+)?)\s*(kcal|kj|mg|g|µg|mcg)?", s or "", re.I)
    if not m:
        return None, None
    return float(m.group(1).replace(",", ".")), (m.group(2) or "").lower()


def compare_sources(pkg, off):
    notes = []
    if pkg["ingredients_text"] and off.get("ingredients_text"):
        a = set(re.findall(r"[a-z0-9]+", pkg["ingredients_text"].lower()))
        b = set(re.findall(r"[a-z0-9]+", off["ingredients_text"].lower()))
        if a and b and len(a & b) / len(a | b) < 0.6:
            notes.append("The ingredient text on the package differs noticeably from the online record. "
                         "The package text is shown; check which version you have.")
    if pkg["product_name"] and off.get("product_name"):
        a, b = off_client._tokens(pkg["product_name"]), off_client._tokens(off["product_name"])
        if a and b and not (a & b):
            notes.append(f"Product name on the package (“{pkg['product_name']}”) differs from the online record (“{off['product_name']}”).")
    off_n = off.get("nutrition") or {}
    if "100" in (pkg.get("nutrition_basis") or ""):
        for k, label in NUTRI_LABELS:
            pv, ov = pkg["nutrition"].get(k), off_n.get(k)
            if not pv or not ov:
                continue
            (pn, pu), (on, ou) = _num_unit(pv), _num_unit(ov)
            if pn is None or on is None or pu != ou:
                continue
            if abs(pn - on) > 1 and abs(pn - on) / max(pn, on) > 0.15:
                notes.append(f"{label}: package shows {pv}, online record shows {ov}.")
    if pkg["declared_allergens"] and off.get("allergens"):
        declared = " ".join(pkg["declared_allergens"]).lower()
        missing = [a for a in off["allergens"] if a.lower().split()[0] not in declared]
        if missing:
            notes.append("The online record lists allergens not named in the package statement: " + ", ".join(missing) + ".")
    return notes


# ---------------------------------------------------------------- main entry

def run_analysis(cfg, image_b64, name, barcode, category, country):
    today = dt.date.today().isoformat()
    pkg = normalize_extraction(ollama_client.extract_label(cfg, image_b64)) if image_b64 else None

    uncertain = list(pkg["uncertain_text"]) if pkg else []
    not_determined, sources = [], []

    # ---- online lookup (barcode only for images; name search only when no image was given)
    code = barcode or None
    if not code and pkg and pkg["barcode"]:
        if valid_gtin(pkg["barcode"]):
            code = pkg["barcode"]
        else:
            uncertain.append("A barcode number was partly read but failed its check digit, so it was not used for lookup.")
    elif barcode and pkg and pkg["barcode"] and pkg["barcode"] != barcode:
        uncertain.append("The barcode you entered differs from the barcode read on the photo.")

    off, off_error, matched_by_name = None, None, False
    try:
        if code:
            off = off_client.lookup_barcode(cfg, code, category)
        elif not image_b64 and name:
            off = off_client.match_by_name(cfg, name, category)
            matched_by_name = off is not None
    except off_client.OffError as e:
        off_error = str(e)

    if not pkg and not off:
        if off_error:
            raise ApiError(off_error + " No label photo was provided, so there is nothing else to analyze.", "off_unavailable", 502)
        what = f"barcode {code}" if code else f"“{name}”"
        raise ApiError(f"No matching product record was found online for {what}. Nothing was substituted. "
                       "Try the barcode, or upload a photo of the label.", "not_found", 404)
    if off_error:
        not_determined.append(f"Online database lookup failed ({off_error}), so only the label photo was used.")
    if pkg and not code and not off_error:
        not_determined.append("No readable barcode was available, so no online database record was looked up.")
    if matched_by_name:
        uncertain.append("This record was matched by product name only. Flavour, size or country variants can differ — "
                         "compare with the package.")

    # ---- ingredients
    pkg_text = pkg["ingredients_text"] if pkg else None
    text = pkg_text or (off or {}).get("ingredients_text")
    origin = "package" if pkg_text else ("database" if text else None)
    names = split_ingredients(text)
    if not names:
        not_determined.append("No ingredient list could be read or found.")

    explained = {}
    if names:
        try:
            for item in ollama_client.explain_ingredients(cfg, names):
                if isinstance(item, dict) and clean_str(item.get("name"), 200):
                    explained[clean_str(item["name"], 200).lower()] = item
        except ApiError as e:
            not_determined.append(f"Ingredient explanations are unavailable right now: {e.message}")
    analysis = []
    for n in names:
        e = explained.get(n.lower(), {})
        expl = clean_str(e.get("explanation"), 500)
        analysis.append({
            "name": n,
            "type": clean_str(e.get("type"), 80),
            "purpose": clean_str(e.get("purpose"), 200),
            "explanation": expl,
            "uncertainty": clean_str(e.get("uncertainty"), 300),
            "source_status": origin,
            "explanation_source": "general_knowledge" if expl else None,
        })

    # ---- nutrition (never mix package and online panels; never turn missing into 0)
    nutrition = {k: None for k in NUTRI_KEYS}
    nutrition["basis"] = None
    nut_origin = None
    if pkg and any(pkg["nutrition"].values()):
        nutrition.update(pkg["nutrition"])
        nutrition["basis"] = pkg["nutrition_basis"]
        nut_origin = "package"
    elif off and off.get("nutrition"):
        nutrition.update(off["nutrition"])
        nut_origin = "database"
    if nut_origin is None:
        not_determined.append("No nutrition panel could be read or found.")
    else:
        if nut_origin == "database":
            not_determined.append("Nutrition values come from the online database record, not from your package.")
        if not nutrition.get("basis"):
            not_determined.append("The basis of the nutrition values (per 100 g, per serving…) could not be read.")
        missing = [lbl for k, lbl in NUTRI_LABELS if not nutrition.get(k)]
        if missing:
            not_determined.append("Not available (not declared or not readable): " + ", ".join(missing) + ".")

    # ---- allergens
    declared = list(pkg["declared_allergens"]) if pkg else []
    declared += [f"May contain (precautionary statement): {a}" for a in (pkg["may_contain"] if pkg else [])]
    if not declared and off and (off.get("allergens") or off.get("traces")):
        declared += [f"{a} (per online record, not read from your package)" for a in off["allergens"]]
        declared += [f"May contain: {a} (per online record, not read from your package)" for a in off["traces"]]
    if not (pkg and (pkg["declared_allergens"] or pkg["may_contain"])):
        not_determined.append("No allergen statement was read from a package, so allergen status is unknown. "
                              "This does not mean the product is allergen-free.")
    matches = possible_allergen_matches(text)

    # ---- comparison
    discrepancies = compare_sources(pkg, off) if (pkg and off) else []

    # ---- concerns / notes (factual, no health judgements)
    concerns = []
    if pkg and pkg["declared_allergens"]:
        concerns.append({"point": "Declared allergens present", "reason": "The package declares: " + ", ".join(pkg["declared_allergens"]) + ".", "source": "Package label"})
    sugars = sugar_sources(names)
    if any(s["name"] in names[:3] for s in sugars):
        concerns.append({"point": "A sugar or sweetener is listed among the first ingredients",
                         "reason": "Ingredients are usually listed by weight, so an early position suggests a larger share. The amount itself is not known.",
                         "source": "Ingredient order on the label" if origin == "package" else "Online record"})
    for w in (pkg["warnings"] if pkg else []):
        concerns.append({"point": "Warning printed on the package", "reason": w, "source": "Package label"})
    if discrepancies:
        concerns.append({"point": "Package and online record differ", "reason": "See the Uncertainty tab for the differences.", "source": "Comparison"})
    positives = []
    if origin == "package":
        positives.append("The ingredient list was readable on the package")
    if nut_origin == "package":
        positives.append("A nutrition panel was readable on the package")
    if pkg and pkg["declared_allergens"]:
        positives.append("An allergen statement was read from the package")
    if pkg:
        not_determined.append("Label text was read by a small local AI model and can contain reading mistakes. Compare with the package.")

    # ---- sources
    if pkg:
        sources.append({"name": f"Label photo read by local model {cfg['OLLAMA_MODEL']} (may contain reading errors)", "url": None, "retrieved": today})
    if off:
        sources.append({"name": f"{off['source_name']} – record {off['code']} (ODbL, community-contributed)", "url": off["url"], "retrieved": off["retrieved"]})

    data_source = " + ".join(filter(None, ["Label photo (local AI reading)" if pkg else None, off["source_name"] if off else None]))
    return {
        "demo": False,
        "product_name": (pkg or {}).get("product_name") or name or (off or {}).get("product_name"),
        "brand": (pkg or {}).get("brand") or ((off or {}).get("brand") if off else None),
        "category": category or None,
        "barcode": code,
        "image_url": (off or {}).get("image_url"),
        "data_source": data_source,
        "last_updated": (off or {}).get("last_modified"),
        "ingredients_text": text,
        "ingredients": names,
        "ingredient_analysis": analysis,
        "nutrition_text": None,
        "nutrition": nutrition,
        "sugar_sources": sugars,
        "declared_allergens": declared,
        "possible_allergen_matches": matches,
        "possible_concerns": concerns,
        "positive_notes": positives,
        "country_regulations": regulations.get_regulations(cfg["REGULATIONS_PATH"], country, names),
        "sources": sources,
        "uncertain_text": uncertain,
        "not_determined": not_determined,
        "discrepancies": discrepancies,
        "analyzed_on": today,
    }
