"""Talks to the local Ollama server. No cloud services involved."""
import json
import logging

import requests

from errors import ApiError

log = logging.getLogger(__name__)

NUTRITION_KEYS = ["energy", "protein", "carbohydrates", "sugars", "added_sugars",
                  "fat", "saturated_fat", "trans_fat", "fibre", "sodium"]

_STR_OR_NULL = {"anyOf": [{"type": "string"}, {"type": "null"}]}

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "product_name": _STR_OR_NULL,
        "brand": _STR_OR_NULL,
        "barcode": _STR_OR_NULL,
        "ingredients_text": _STR_OR_NULL,
        "nutrition_basis": _STR_OR_NULL,
        "nutrition": {"type": "object", "properties": {k: _STR_OR_NULL for k in NUTRITION_KEYS}},
        "declared_allergens": {"type": "array", "items": {"type": "string"}},
        "may_contain": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "uncertain_text": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["product_name", "brand", "barcode", "ingredients_text", "nutrition_basis",
                 "nutrition", "declared_allergens", "may_contain", "warnings", "uncertain_text"],
}

EXPLAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "ingredients": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": _STR_OR_NULL,
                    "purpose": _STR_OR_NULL,
                    "explanation": _STR_OR_NULL,
                    "uncertainty": _STR_OR_NULL,
                },
                "required": ["name", "type", "purpose", "explanation", "uncertainty"],
            },
        }
    },
    "required": ["ingredients"],
}

EXTRACT_PROMPT = """You are a careful label reader. Look at the product label image and transcribe ONLY text that is printed and clearly legible.

Rules:
- Never guess, infer or invent. If something is not visible or not readable, use null (for single values) or an empty list.
- Do not calculate or estimate nutrition values. Do not estimate calories from ingredients.
- Copy nutrition values exactly as printed, including the unit (for example "480 kcal", "7 g", "310 mg"). A value that is not printed must be null, never "0".
- "nutrition_basis" is the basis printed on the panel, for example "per 100 g", "per 100 ml" or "per serving (30 g)". Use null if unclear.
- "ingredients_text" is the complete ingredient line exactly as printed, without the word "Ingredients:". Keep the order. Use null if there is no readable ingredient list.
- "declared_allergens" lists allergens named in a "Contains ..." style allergen statement on the package. Copy the wording. If no such statement is visible, return an empty list.
- "may_contain" lists items from a precautionary statement such as "May contain traces of ..." (empty list if none).
- "warnings" lists printed warning statements (empty list if none).
- "barcode" only if the digits are fully readable, digits only; otherwise null.
- "uncertain_text" lists short descriptions of parts that are cropped, blurry or unreadable (for example "end of ingredient line is cropped").
- Do not state anything about bans, approvals, legality or health effects.
Return JSON only."""

EXPLAIN_PROMPT = """You explain food and cosmetic ingredients in simple language for shoppers.
For each ingredient name given, return: type (short category such as "Sweetener", "Preservative", "Cereal", "Emulsifier"), purpose (what it is typically used for in a product), explanation (one or two plain sentences), and uncertainty.

Rules:
- This is general knowledge, not a statement about this specific product.
- Do not call an ingredient dangerous, toxic or harmful, and do not give medical advice or health claims.
- Do not say whether any ingredient is banned, approved or legal anywhere.
- If you do not recognise an ingredient or code, set type, purpose and explanation to null and describe the problem in uncertainty.
- If you are only partly sure, say so in uncertainty. Otherwise uncertainty is null.
- Return one entry per ingredient, using exactly the names given.
Return JSON only."""


def _post_chat(cfg, payload):
    try:
        resp = requests.post(f"{cfg['OLLAMA_URL']}/api/chat", json=payload,
                             timeout=(5, cfg["OLLAMA_TIMEOUT"]))
    except requests.exceptions.ConnectionError:
        raise ApiError("Cannot reach Ollama. Start it with 'ollama serve' (or open the Ollama app) and try again.",
                       "ollama_offline", 503)
    except requests.exceptions.Timeout:
        raise ApiError("The local AI model took too long to respond. Try a smaller or clearer image, "
                       "or increase OLLAMA_TIMEOUT.", "ollama_timeout", 504)
    except requests.exceptions.RequestException:
        log.exception("Unexpected Ollama request error")
        raise ApiError("Could not communicate with Ollama.", "ollama_error", 502)
    return resp


def chat_json(cfg, messages, schema, model=None):
    """Call a selected Ollama model and return parsed JSON (dict).

    Defaults to OLLAMA_MODEL to preserve the existing vision-model behaviour.
    """
    model = model or cfg["OLLAMA_MODEL"]
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": schema,
        "options": {"temperature": 0, "num_ctx": 4096},
    }
    resp = _post_chat(cfg, payload)
    if resp.status_code == 404:
        raise ApiError(f"The model '{model}' is not installed in Ollama. "
                       f"Check with 'ollama list'.", "model_missing", 503)
    if resp.status_code >= 400:
        # Some Ollama versions reject a JSON schema; retry once with plain JSON mode.
        payload["format"] = "json"
        resp = _post_chat(cfg, payload)
        if resp.status_code == 404:
            raise ApiError(f"The model '{model}' is not installed in Ollama.", "model_missing", 503)
        if resp.status_code >= 400:
            log.error("Ollama returned HTTP %s: %s", resp.status_code, resp.text[:300])
            raise ApiError("The local AI model returned an error. Check the backend terminal for details.",
                           "ollama_error", 502)
    try:
        body = resp.json()
        content = body["message"]["content"]
    except (ValueError, KeyError, TypeError):
        raise ApiError("The local AI model returned an unexpected response.", "ollama_bad_output", 502)
    return parse_model_json(content)


def parse_model_json(text):
    if not isinstance(text, str) or not text.strip():
        raise ApiError("The local AI model returned an empty answer. Try again.", "ollama_bad_output", 502)
    candidates = [text.strip()]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except ValueError:
            continue
    raise ApiError("The local AI model's answer could not be understood (malformed JSON). Please try again, "
                   "ideally with a sharper, closer photo.", "ollama_bad_output", 502)


def extract_label(cfg, image_b64):
    messages = [{"role": "user", "content": EXTRACT_PROMPT, "images": [image_b64]}]
    return chat_json(cfg, messages, EXTRACT_SCHEMA)


def explain_ingredients(cfg, names):
    """General-knowledge explanations (text only). Returns the raw list of dicts."""
    if not names:
        return []
    messages = [
        {"role": "system", "content": EXPLAIN_PROMPT},
        {"role": "user", "content": "Ingredients:\n" + "\n".join(f"- {n}" for n in names)},
    ]
    # Use the text-focused model for explanations while keeping Qwen for image extraction.
    explain_model = cfg.get("OLLAMA_EXPLAIN_MODEL") or cfg["OLLAMA_MODEL"]
    data = chat_json(cfg, messages, EXPLAIN_SCHEMA, model=explain_model)
    items = data.get("ingredients")
    return items if isinstance(items, list) else []


def status(cfg):
    """Cheap health probe used by /api/health. Never raises."""
    try:
        r = requests.get(f"{cfg['OLLAMA_URL']}/api/tags", timeout=3)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:
        return {
            "reachable": False,
            "model": cfg["OLLAMA_MODEL"],
            "model_installed": False,
            "explanation_model": cfg.get("OLLAMA_EXPLAIN_MODEL", cfg["OLLAMA_MODEL"]),
            "explanation_model_installed": False,
        }
    want = cfg["OLLAMA_MODEL"]
    explain_want = cfg.get("OLLAMA_EXPLAIN_MODEL") or want
    installed = any(n == want or (":" not in want and n.startswith(want + ":")) for n in names)
    explain_installed = any(
        n == explain_want or (":" not in explain_want and n.startswith(explain_want + ":"))
        for n in names
    )
    return {
        "reachable": True,
        "model": want,
        "model_installed": installed,
        "explanation_model": explain_want,
        "explanation_model_installed": explain_installed,
    }
