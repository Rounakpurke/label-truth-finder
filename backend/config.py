import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Must match frontend/src/pages/Settings.jsx and Analyze.jsx
COUNTRIES = ["India", "United States", "European Union", "United Kingdom", "Canada", "Australia"]
CATEGORIES = ["", "Food", "Beverage", "Skincare", "Cosmetics", "Other"]


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def load_config(overrides=None):
    cfg = {
        "HOST": os.getenv("HOST", "0.0.0.0"),
        "PORT": _int("PORT", 5001),
        "OLLAMA_URL": os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
        # Vision model: reads text and values from label photos.
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "qwen2.5vl:3b"),
        # Text model: explains ingredients. Falls back to the vision model if unset.
        "OLLAMA_EXPLAIN_MODEL": os.getenv("OLLAMA_EXPLAIN_MODEL", "gemma4:e2b"),
        "OLLAMA_TIMEOUT": _int("OLLAMA_TIMEOUT", 240),
        "MAX_IMAGE_MB": _int("MAX_IMAGE_MB", 10),
        "FRONTEND_ORIGINS": [
            o.strip()
            for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
            if o.strip()
        ],
        "DATABASE_PATH": os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "label_truth_finder.db")),
        "OFF_CONTACT": os.getenv("OFF_CONTACT", "local-prototype"),
        "OFF_TIMEOUT": _int("OFF_TIMEOUT", 10),
        "REGULATIONS_PATH": str(BASE_DIR / "data" / "regulations.json"),
    }
    if overrides:
        cfg.update(overrides)
    return cfg
