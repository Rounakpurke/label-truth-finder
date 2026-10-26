"""SQLite persistence: analysis history and community reviews."""
import datetime as dt
import hashlib
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
  id TEXT PRIMARY KEY, product_name TEXT, date TEXT, status TEXT,
  report_json TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT NOT NULL, product TEXT NOT NULL, brand TEXT,
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5), text TEXT NOT NULL, user TEXT NOT NULL,
  date TEXT NOT NULL, helpful INTEGER NOT NULL DEFAULT 0, fingerprint TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_fp ON reviews(fingerprint, created_at);
CREATE TABLE IF NOT EXISTS helpful_votes (
  review_id INTEGER NOT NULL, voter TEXT NOT NULL, PRIMARY KEY (review_id, voter));
"""
HISTORY_LIMIT = 200
DUPLICATE_WINDOW_S = 600


def init_db(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"], timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def product_id(product, brand=""):
    slug = re.sub(r"[^a-z0-9]+", "-", f"{product} {brand}".lower()).strip("-")
    return slug[:120] or "unknown"


# ---------------------------------------------------------------- history

def save_analysis(report):
    db = get_db()
    aid = "a-" + uuid.uuid4().hex[:12]
    report = {**report, "history_id": aid}
    db.execute("INSERT INTO analyses (id, product_name, date, status, report_json, created_at) VALUES (?,?,?,?,?,?)",
               (aid, report.get("product_name") or "Unnamed product", dt.date.today().isoformat(), "Completed",
                json.dumps(report), time.time()))
    db.execute("DELETE FROM analyses WHERE id NOT IN (SELECT id FROM analyses ORDER BY created_at DESC LIMIT ?)",
               (HISTORY_LIMIT,))
    db.commit()
    return report


def list_history(limit=50):
    rows = get_db().execute("SELECT * FROM analyses ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r["id"], "product_name": r["product_name"], "thumbnail": None, "date": r["date"],
             "status": r["status"], "demo": False, "report": json.loads(r["report_json"])} for r in rows]


def clear_history():
    db = get_db()
    n = db.execute("DELETE FROM analyses").rowcount
    db.commit()
    return n


# ---------------------------------------------------------------- reviews

def _review(r):
    return {"id": str(r["id"]), "product": r["product"], "brand": r["brand"] or "", "rating": r["rating"],
            "text": r["text"], "user": r["user"], "date": r["date"], "helpful": r["helpful"]}


def add_review(product, brand, rating, text, user):
    """Returns (review, created). A repeat of the same review within 10 minutes returns the original."""
    db = get_db()
    pid = product_id(product, brand)
    fp = hashlib.sha256(f"{pid}|{user.lower()}|{text.strip().lower()}".encode()).hexdigest()
    now = time.time()
    dup = db.execute("SELECT * FROM reviews WHERE fingerprint=? AND created_at>?", (fp, now - DUPLICATE_WINDOW_S)).fetchone()
    if dup:
        return _review(dup), False
    cur = db.execute(
        "INSERT INTO reviews (product_id, product, brand, rating, text, user, date, fingerprint, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (pid, product, brand, rating, text, user, dt.date.today().isoformat(), fp, now))
    db.commit()
    return _review(db.execute("SELECT * FROM reviews WHERE id=?", (cur.lastrowid,)).fetchone()), True


def list_reviews(pid, limit=200):
    db = get_db()
    if pid == "all":
        rows = db.execute("SELECT * FROM reviews ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY created_at DESC, id DESC LIMIT ?", (pid, limit)).fetchall()
    return [_review(r) for r in rows]


def vote_helpful(review_id, voter):
    """Returns (review, counted) or (None, False) if the review does not exist."""
    db = get_db()
    row = db.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
    if not row:
        return None, False
    cur = db.execute("INSERT OR IGNORE INTO helpful_votes (review_id, voter) VALUES (?,?)", (review_id, voter))
    counted = cur.rowcount == 1
    if counted:
        db.execute("UPDATE reviews SET helpful = helpful + 1 WHERE id=?", (review_id,))
    db.commit()
    return _review(db.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()), counted
