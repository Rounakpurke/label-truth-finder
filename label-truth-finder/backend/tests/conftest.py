import io
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as app_module  # noqa: E402
import ollama_client  # noqa: E402

EXTRACT = {
    "product_name": "Demo Oat Cookies", "brand": "Demo Brand", "barcode": None,
    "ingredients_text": "Wheat flour, sugar, palm oil, oats, milk solids, salt, raising agent (500)",
    "nutrition_basis": "per 100 g",
    "nutrition": {"energy": "480 kcal", "protein": "7 g", "carbohydrates": "66 g", "sugars": "22 g",
                  "added_sugars": None, "fat": "20 g", "saturated_fat": "9 g", "trans_fat": None,
                  "fibre": "3 g", "sodium": "310 mg"},
    "declared_allergens": ["Wheat (gluten)", "Milk"], "may_contain": [], "warnings": [],
    "uncertain_text": ["End of the ingredient line is cropped"],
}


def png_bytes(size=(64, 64)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 180, 120)).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def cfg(tmp_path):
    return {"DATABASE_PATH": str(tmp_path / "t.db"), "OLLAMA_TIMEOUT": 1, "OFF_TIMEOUT": 1}


@pytest.fixture
def client(cfg):
    return app_module.create_app(cfg).test_client()


@pytest.fixture
def mock_ollama(monkeypatch):
    monkeypatch.setattr(ollama_client, "extract_label", lambda c, b64: dict(EXTRACT))
    monkeypatch.setattr(ollama_client, "explain_ingredients", lambda c, names: [
        {"name": n, "type": "Test type", "purpose": "Test purpose", "explanation": "Test explanation.", "uncertainty": None}
        for n in names])


def upload(client, data=None, filename="label.png", mimetype="image/png", **fields):
    form = {"product_name": "", "barcode": "", "category": "", "country": "India", **fields}
    if data is not False:
        form["image"] = (io.BytesIO(data if data is not None else png_bytes()), filename, mimetype)
    return client.post("/api/analyze", data=form, content_type="multipart/form-data")
