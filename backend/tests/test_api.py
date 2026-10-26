import json
import shutil
import subprocess
from pathlib import Path

import pytest
import requests

import app as app_module
import off_client
import ollama_client
import regulations
from tests.conftest import EXTRACT, png_bytes, upload

ROOT = Path(__file__).resolve().parents[2]
OFF_PRODUCT = {"status": 1, "product": {
    "code": "8901058851137", "product_name": "Demo Oat Cookies", "brands": "Demo Brand",
    "ingredients_text": "Wheat flour, sugar, palm oil, oats, milk solids, salt",
    "allergens_tags": ["en:gluten", "en:milk"], "last_modified_t": 1760000000,
    "nutriments": {"energy-kcal_100g": 470, "sugars_100g": 22, "sodium_100g": 0.31}}}


# ------------------------------------------------------------ health
def test_health_ollama_offline(client, monkeypatch):
    def boom(*a, **k):
        raise requests.exceptions.ConnectionError()
    monkeypatch.setattr(requests, "get", boom)
    body = client.get("/api/health").get_json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["ollama"]["reachable"] is False


def test_unknown_route_is_json(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and "message" in r.get_json()["error"]


# ------------------------------------------------------------ upload validation
def test_requires_some_input(client):
    r = upload(client, data=False)
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "missing_input"


@pytest.mark.parametrize("fields,code", [({"barcode": "12ab"}, "bad_barcode"), ({"country": "Narnia"}, "bad_country"),
                                         ({"category": "Weapons"}, "bad_category")])
def test_field_validation(client, fields, code):
    assert upload(client, **fields).get_json()["error"]["code"] == code


def test_rejects_wrong_extension_and_mime_and_fake_image(client, mock_ollama):
    assert upload(client, filename="x.gif", mimetype="image/gif").status_code == 400
    assert upload(client, filename="x.png", mimetype="text/plain").status_code == 400
    assert upload(client, data=b"not really an image").status_code == 400
    assert upload(client, data=b"").status_code in (400,)


def test_rejects_oversized(cfg):
    from app import create_app
    c = create_app({**cfg, "MAX_IMAGE_MB": 1}).test_client()
    r = upload(c, data=b"0" * (3 * 1024 * 1024))
    assert r.status_code == 413 and "message" in r.get_json()["error"]


# ------------------------------------------------------------ successful analysis & shape
def test_analyze_image_shape_and_semantics(client, mock_ollama):
    r = upload(client, product_name="")
    assert r.status_code == 200
    d = r.get_json()
    assert d["product_name"] == "Demo Oat Cookies" and d["demo"] is False
    assert d["nutrition"]["added_sugars"] is None and d["nutrition"]["trans_fat"] is None  # not turned into 0
    assert d["nutrition"]["basis"] == "per 100 g"
    assert "Wheat (gluten)" in d["declared_allergens"]
    allergens = {m["allergen"] for m in d["possible_allergen_matches"]}
    assert {"Cereals containing gluten", "Milk"} <= allergens
    assert d["ingredients"][-1] == "raising agent (500)"
    assert all(i["source_status"] == "package" and i["explanation_source"] == "general_knowledge" for i in d["ingredient_analysis"])
    assert any(c["point"] == "Declared allergens present" and c["source"] == "Package label" for c in d["possible_concerns"])
    # regulations: nothing claimed
    assert d["country_regulations"][0]["status"] == "not_verified" and d["country_regulations"][0]["country"] == "India"
    assert {s["name"] for s in d["sugar_sources"]} == {"sugar"}
    assert d["history_id"].startswith("a-")


def test_possible_matches_are_not_declared(client, mock_ollama, monkeypatch):
    e = dict(EXTRACT, declared_allergens=[], ingredients_text="Water, coconut milk, cocoa butter")
    monkeypatch.setattr(ollama_client, "extract_label", lambda c, b: dict(e))
    d = upload(client).get_json()
    assert d["declared_allergens"] == []
    assert d["possible_allergen_matches"] == []          # coconut milk / cocoa butter are not dairy
    assert any("allergen-free" in n for n in d["not_determined"])


def test_normalization_handles_junk_model_output(client, monkeypatch):
    junk = {"product_name": 5, "ingredients_text": None, "nutrition": {"energy": {"value": 100, "unit": "kcal"}, "protein": "N/A", "fat": 0},
            "declared_allergens": "milk", "warnings": None, "barcode": "abc"}
    monkeypatch.setattr(ollama_client, "extract_label", lambda c, b: junk)
    monkeypatch.setattr(ollama_client, "explain_ingredients", lambda c, n: [])
    d = upload(client).get_json()
    assert d["nutrition"]["energy"] == "100 kcal" and d["nutrition"]["protein"] is None
    assert d["declared_allergens"] == ["milk"] and d["ingredients"] == []
    assert any("ingredient" in n.lower() for n in d["not_determined"])


def test_explanation_failure_degrades_gracefully(client, monkeypatch, mock_ollama):
    from errors import ApiError
    def fail(c, n):
        raise ApiError("model busy", "ollama_timeout", 504)
    monkeypatch.setattr(ollama_client, "explain_ingredients", fail)
    r = upload(client)
    assert r.status_code == 200 and r.get_json()["ingredient_analysis"][0]["explanation"] is None


# ------------------------------------------------------------ Ollama failures
def _post_raises(monkeypatch, exc):
    def boom(*a, **k):
        raise exc
    monkeypatch.setattr(requests, "post", boom)


def test_ollama_offline(client, monkeypatch):
    _post_raises(monkeypatch, requests.exceptions.ConnectionError("refused"))
    r = upload(client)
    assert r.status_code == 503 and r.get_json()["error"]["code"] == "ollama_offline"
    assert "Traceback" not in r.get_data(as_text=True)


def test_ollama_timeout(client, monkeypatch):
    _post_raises(monkeypatch, requests.exceptions.ReadTimeout())
    assert upload(client).status_code == 504


class FakeResp:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._b, self.text = status, body, text
    def json(self):
        if self._b is None:
            raise ValueError()
        return self._b


def test_ollama_malformed_json_and_missing_model(client, monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResp(body={"message": {"content": "sorry, here is text"}}))
    assert upload(client).get_json()["error"]["code"] == "ollama_bad_output"
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResp(status=404, text="model not found"))
    assert upload(client).get_json()["error"]["code"] == "model_missing"


def test_ollama_json_wrapped_in_text_is_recovered():
    assert ollama_client.parse_model_json('Sure!\n{"a": 1}\nDone') == {"a": 1}


def test_ollama_schema_rejected_then_json_mode_retry(client, monkeypatch, cfg):
    calls = []
    def post(url, json=None, **k):
        calls.append(json["format"])
        return FakeResp(status=400) if len(calls) == 1 else FakeResp(body={"message": {"content": '{"x": 1}'}})
    monkeypatch.setattr(requests, "post", post)
    assert ollama_client.chat_json({**app_module.load_config(cfg)}, [], {"type": "object"}) == {"x": 1}
    assert calls[1] == "json"


# ------------------------------------------------------------ Open Food Facts
def test_barcode_lookup_and_discrepancy(client, mock_ollama, monkeypatch):
    prod = json.loads(json.dumps(OFF_PRODUCT))
    prod["product"]["nutriments"]["energy-kcal_100g"] = 300   # package says 480
    monkeypatch.setattr(off_client, "_get", lambda cfg, url, params: prod)
    d = upload(client, barcode="8901058851137").get_json()
    assert d["data_source"] == "Label photo (local AI reading) + Open Food Facts"
    assert any(s["url"] == "https://world.openfoodfacts.org/product/8901058851137" and s["retrieved"] for s in d["sources"])
    assert d["nutrition"]["energy"] == "480 kcal"            # package value is NOT overwritten
    assert any("Calories" in n and "300" in n for n in d["discrepancies"])


def test_barcode_only_uses_database_and_labels_it(client, mock_ollama, monkeypatch):
    monkeypatch.setattr(off_client, "_get", lambda cfg, url, params: OFF_PRODUCT)
    d = client.post("/api/analyze", data={"barcode": "8901058851137", "country": "India"}).get_json()
    assert d["nutrition"]["sodium"] == "310 mg" and d["ingredient_analysis"][0]["source_status"] == "database"
    assert any("online" in n.lower() for n in d["not_determined"])
    assert "(per online record" in d["declared_allergens"][0]


def test_barcode_not_found_is_404_not_a_substitute(client, monkeypatch):
    monkeypatch.setattr(off_client, "_get", lambda cfg, url, params: {"status": 0})
    r = client.post("/api/analyze", data={"barcode": "8901058851137"})
    assert r.status_code == 404 and r.get_json()["error"]["code"] == "not_found"


def test_online_timeout_is_clean_502(client, monkeypatch):
    def boom(*a, **k):
        raise requests.exceptions.Timeout()
    monkeypatch.setattr(requests, "get", boom)
    r = client.post("/api/analyze", data={"barcode": "8901058851137"})
    assert r.status_code == 502 and "timed out" in r.get_json()["error"]["message"]


def test_online_failure_with_image_still_returns_label_analysis(client, mock_ollama, monkeypatch):
    def boom(*a, **k):
        raise requests.exceptions.ConnectionError()
    monkeypatch.setattr(requests, "get", boom)
    r = upload(client, barcode="8901058851137")
    assert r.status_code == 200 and any("lookup failed" in n for n in r.get_json()["not_determined"])


def test_name_search_requires_clear_match(client, monkeypatch):
    other = {"products": [{"code": "1", "product_name": "Chocolate Bar", "brands": "Zed"}]}
    monkeypatch.setattr(off_client, "_get", lambda cfg, url, params: other)
    assert client.post("/api/analyze", data={"product_name": "Oat Cookies"}).status_code == 404
    good = {"products": [{"code": "2", "product_name": "Oat Cookies", "brands": "Demo", "ingredients_text": "Oats, sugar"}]}
    monkeypatch.setattr(off_client, "_get", lambda cfg, url, params: good)
    monkeypatch.setattr(ollama_client, "explain_ingredients", lambda c, n: [])
    d = client.post("/api/analyze", data={"product_name": "Oat Cookies"}).get_json()
    assert d["barcode"] is None and any("matched by product name" in u for u in d["uncertain_text"])


def test_search_endpoint(client, monkeypatch):
    monkeypatch.setattr(off_client, "_get", lambda cfg, url, params: {"products": [{"code": "2", "product_name": "Oat Cookies", "brands": "Demo"}]})
    r = client.get("/api/products/search?q=oat")
    assert r.get_json()[0]["id"] == "2"
    assert client.get("/api/products/search?q=").status_code == 400


def test_gtin_checksum():
    from analysis import valid_gtin
    assert valid_gtin("4006381333931") and not valid_gtin("4006381333932")


# ------------------------------------------------------------ history persistence
def test_history_persists_across_restart_and_clears(cfg, mock_ollama):
    c1 = app_module.create_app(cfg).test_client()
    upload(c1)
    c2 = app_module.create_app(cfg).test_client()   # "server restart"
    h = c2.get("/api/history").get_json()
    assert len(h) == 1 and h[0]["report"]["product_name"] == "Demo Oat Cookies" and h[0]["thumbnail"] is None
    assert c2.delete("/api/history").get_json()["deleted"] == 1
    assert c2.get("/api/history").get_json() == []


def test_failed_analysis_not_saved(client, monkeypatch):
    _post_raises(monkeypatch, requests.exceptions.ConnectionError())
    upload(client)
    assert client.get("/api/history").get_json() == []


# ------------------------------------------------------------ reviews
REVIEW = {"product": "Demo Oat Cookies", "brand": "Demo Brand", "rating": 4, "text": "Tasty but a bit sweet.", "user": "sam"}


def test_review_flow(client):
    r = client.post("/api/reviews", json=REVIEW)
    assert r.status_code == 201
    rid = r.get_json()["id"]
    again = client.post("/api/reviews", json=REVIEW)                 # accidental double submit
    assert again.status_code == 200 and again.get_json()["id"] == rid
    lst = client.get("/api/products/all/reviews").get_json()
    assert len(lst) == 1 and lst[0]["helpful"] == 0 and lst[0]["date"]
    assert client.get("/api/products/demo-oat-cookies-demo-brand/reviews").get_json()[0]["id"] == rid
    assert client.get("/api/products/other/reviews").get_json() == []
    h1 = client.post(f"/api/reviews/{rid}/helpful").get_json()
    h2 = client.post(f"/api/reviews/{rid}/helpful").get_json()
    assert h1["helpful"] == 1 and h2["helpful"] == 1 and h2["already_voted"] is True
    assert client.post("/api/reviews/999/helpful").status_code == 404


@pytest.mark.parametrize("patch", [{"rating": 0}, {"rating": 6}, {"rating": "5"}, {"rating": True}, {"text": "short"}, {"product": " "}])
def test_review_validation(client, patch):
    assert client.post("/api/reviews", json={**REVIEW, **patch}).status_code == 400


def test_review_bad_json_and_defaults(client):
    assert client.post("/api/reviews", data="nope", content_type="text/plain").status_code == 400
    r = client.post("/api/reviews", json={**REVIEW, "user": ""})
    assert r.get_json()["user"] == "anonymous"


# ------------------------------------------------------------ regulations
def test_regulation_entries_need_official_source(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"entries": [
        {"country": "India", "match": ["tartrazine"], "status": "confirmed", "explanation": "x"},   # no source -> downgraded
        {"country": "India", "match": ["ins 500"], "status": "confirmed", "explanation": "Test only", "source_name": "Test Regulator",
         "source_url": "https://example.org/rule", "date": "2026-01-01"}]}))
    out = regulations.get_regulations(str(f), "India", ["Tartrazine", "Raising agent (INS 500)"])
    assert out[0]["status"] == "not_verified"
    assert out[1]["status"] == "not_verified" and out[1]["source_url"] is None
    assert out[2]["status"] == "confirmed" and out[2]["source_url"]
    assert regulations.get_regulations(str(f), "Canada", ["Tartrazine"])[0]["country"] == "Canada"


# ------------------------------------------------------------ frontend compatibility
@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_report_has_every_key_frontend_mock_has(client, mock_ollama):
    out = subprocess.run(["node", "--input-type=module", "-e",
                          "import {mockAnalysis as m} from './frontend/src/mock/mockData.js';"
                          "console.log(JSON.stringify({top:Object.keys(m),nutrition:Object.keys(m.nutrition),"
                          "ing:Object.keys(m.ingredient_analysis[0]),reg:Object.keys(m.country_regulations[0]),"
                          "concern:Object.keys(m.possible_concerns[0]),src:Object.keys(m.sources[0]),sugar:Object.keys(m.sugar_sources[0]),"
                          "match:Object.keys(m.possible_allergen_matches[0])}))"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    want = json.loads(out)
    d = upload(client).get_json()
    assert set(want["top"]) - {"demo"} <= set(d) | {"demo"}
    assert set(want["nutrition"]) <= set(d["nutrition"])
    for key, field in [("ing", "ingredient_analysis"), ("reg", "country_regulations"), ("concern", "possible_concerns"),
                       ("src", "sources"), ("sugar", "sugar_sources"), ("match", "possible_allergen_matches")]:
        assert set(want[key]) <= set(d[field][0]), field



# ------------------------------------------------------------ explainable food grade
def test_food_grade_requires_food_category_and_comparable_basis():
    assert app_module.analysis.food_grade({"basis": "per 100 g"}, "Skincare", [])["grade"] == "Not rated"
    assert app_module.analysis.food_grade({"basis": "per serving"}, "Food", [])["grade"] == "Not rated"


def test_food_grade_is_explainable_and_does_not_treat_missing_as_zero():
    grade = app_module.analysis.food_grade({
        "basis": "per 100 g", "sugars": "25 g", "saturated_fat": "6 g",
        "sodium": "500 mg", "protein": None, "fibre": None, "energy": "500 kcal"
    }, "Food", ["Oats", "Sugar"])
    assert grade["grade"] in {"S", "A", "B", "C", "D"}
    assert grade["score"] is not None
    assert any("sugars" in reason.lower() for reason in grade["reasons"])
    assert any("not included" in reason.lower() for reason in grade["reasons"])
    assert any("not an official" in item.lower() for item in grade["limitations"])


def test_daily_guidance_and_alternatives_are_returned_as_general_references():
    analysis = app_module.analysis
    nutrition = {
        "basis": "per 100 g", "energy": "480 kcal", "sugars": "22 g",
        "saturated_fat": "9 g", "sodium": "500 mg", "fibre": "2 g", "protein": "7 g",
    }
    guidance = analysis.daily_dietary_guidance(nutrition)
    assert guidance["population"] == "General adult reference only"
    assert any(row["nutrient"] == "Sodium" and "2,000 mg/day" in row["daily_reference"] for row in guidance["rows"])
    sugar = next(row for row in guidance["rows"] if row["nutrient"] == "Sugars")
    assert "naturally occurring" in sugar["context"]
    swaps = analysis.alternative_suggestions("Demo Oat Cookies", nutrition, "Food")
    assert swaps and any("sugar" in (item["title"] + item["reason"]).lower() for item in swaps)
