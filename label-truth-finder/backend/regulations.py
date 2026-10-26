"""Country regulation data. Deliberately conservative: nothing is 'banned/approved/legal' without a cited official source."""
import json
import logging
import re

log = logging.getLogger(__name__)
VALID = {"confirmed", "none_found"}
REQUIRED = ("status", "explanation", "source_name", "source_url", "date")


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            entries = json.load(f).get("entries", [])
        return entries if isinstance(entries, list) else []
    except (OSError, ValueError):
        log.warning("Could not read regulations file %s", path)
        return []


def default_entry(country):
    return {
        "country": country,
        "subject": "Whole product and all ingredients",
        "status": "not_verified",
        "verification_status": "not_verified",
        "explanation": ("No official regulatory source (for example FSSAI for India) was checked for this product "
                        "or its ingredients, so no ban, approval or legality statement is made. This is not a "
                        "statement that the product is permitted."),
        "source_name": None,
        "source_url": None,
        "date": None,
    }


def get_regulations(path, country, ingredient_names):
    """Always returns at least the 'not verified' entry; adds curated entries that match an ingredient."""
    out = [default_entry(country)]
    text = " | ".join(ingredient_names).lower()
    for e in _load(path):
        if not isinstance(e, dict) or e.get("country") != country:
            continue
        terms = [str(t).lower() for t in e.get("match", []) if t]
        if not any(re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", text) for t in terms):
            continue
        complete = e.get("status") in VALID and all(e.get(k) for k in REQUIRED)
        entry = {
            "country": country,
            "subject": e.get("subject") or ", ".join(terms),
            "status": e["status"] if complete else "not_verified",
            "verification_status": "verified_against_official_source" if complete else "not_verified",
            "explanation": e.get("explanation") if complete else
            "A curated entry exists but is missing an official source or date, so it is not verified.",
            "source_name": e.get("source_name") if complete else None,
            "source_url": e.get("source_url") if complete else None,
            "date": e.get("date") if complete else None,
        }
        out.append(entry)
    return out
