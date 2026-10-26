"""Label Truth Finder backend (Flask). Run:  python app.py"""
import hashlib
import logging
import re

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

import analysis
import db
import images
import off_client
import ollama_client
from config import CATEGORIES, COUNTRIES, load_config
from errors import ApiError

log = logging.getLogger("ltf")


def err(message, code, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def _text(value, limit):
    value = re.sub(r"[\x00-\x08\x0b-\x1f]", "", value or "").strip()
    return value[:limit]


def create_app(overrides=None):
    cfg = load_config(overrides)
    app = Flask(__name__)
    app.config.update(cfg)
    app.config["MAX_CONTENT_LENGTH"] = (cfg["MAX_IMAGE_MB"] + 1) * 1024 * 1024
    CORS(app, origins=cfg["FRONTEND_ORIGINS"], methods=["GET", "POST", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type"])
    db.init_db(cfg["DATABASE_PATH"])
    app.teardown_appcontext(db.close_db)

    # ------------------------------------------------------------ errors
    @app.errorhandler(ApiError)
    def _api_error(e):
        return err(e.message, e.code, e.status)

    @app.errorhandler(HTTPException)
    def _http_error(e):
        if e.code == 413:
            return err(f"The upload is too large. Maximum image size is {cfg['MAX_IMAGE_MB']} MB.", "too_large", 413)
        return err(e.description or e.name, e.name.lower().replace(" ", "_"), e.code)

    @app.errorhandler(Exception)
    def _unexpected(e):
        log.exception("Unhandled error")  # details stay in the server terminal only
        return err("Something went wrong on the server. Check the backend terminal for details.", "server_error", 500)

    # ------------------------------------------------------------ routes
    @app.get("/api/health")
    def health():
        try:
            db.get_db().execute("SELECT 1")
            database = "ok"
        except Exception:
            database = "error"
        return jsonify({"status": "ok" if database == "ok" else "degraded", "database": database,
                        "ollama": ollama_client.status(cfg), "allowed_origins": cfg["FRONTEND_ORIGINS"]})

    @app.post("/api/analyze")
    def analyze():
        name = _text(request.form.get("product_name"), 120)
        barcode = _text(request.form.get("barcode"), 20)
        category = _text(request.form.get("category"), 20)
        country = _text(request.form.get("country"), 40) or "India"
        if barcode and not re.fullmatch(r"\d{8,14}", barcode):
            return err("Barcode must be 8–14 digits.", "bad_barcode", 400)
        if category not in CATEGORIES:
            return err("Unknown category.", "bad_category", 400)
        if country not in COUNTRIES:
            return err("Unknown country / jurisdiction.", "bad_country", 400)

        image_b64 = None
        upload = request.files.get("image")
        if upload and upload.filename:
            limit = cfg["MAX_IMAGE_MB"] * 1024 * 1024
            data = upload.read(limit + 1)
            if len(data) > limit:
                return err(f"Image must be under {cfg['MAX_IMAGE_MB']} MB.", "too_large", 413)
            image_b64 = images.prepare_image(data, upload.filename, upload.mimetype)  # in memory only
        if not image_b64 and not name and not barcode:
            return err("Add a label photo, a product name, or a barcode.", "missing_input", 400)

        report = analysis.run_analysis(cfg, image_b64, name, barcode, category, country)
        return jsonify(db.save_analysis(report))

    @app.get("/api/products/search")
    def search_products():
        q = _text(request.args.get("q"), 120)
        if len(q) < 2:
            return err("Enter at least 2 characters to search.", "bad_query", 400)
        try:
            results = off_client.search(cfg, q, _text(request.args.get("category"), 20))
        except off_client.OffError as e:
            return err(str(e), "off_unavailable", 502)
        return jsonify([{"id": r["code"], "product_name": r["product_name"], "brand": r["brand"], "barcode": r["code"],
                         "image_url": r["image_url"], "source": r["source_name"], "url": r["url"]} for r in results])

    @app.get("/api/history")
    def history():
        return jsonify(db.list_history())

    @app.delete("/api/history")
    def clear_history():
        return jsonify({"deleted": db.clear_history()})

    @app.get("/api/products/<product_id>/reviews")
    def product_reviews(product_id):
        return jsonify(db.list_reviews(product_id[:120]))

    @app.post("/api/reviews")
    def create_review():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return err("Send the review as JSON.", "bad_json", 400)
        product = _text(body.get("product"), 120)
        brand = _text(body.get("brand"), 80)
        text = _text(body.get("text"), 2000)
        user = _text(body.get("user"), 40) or "anonymous"
        rating = body.get("rating")
        if not product:
            return err("Enter the product name.", "bad_review", 400)
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            return err("Rating must be a whole number from 1 to 5.", "bad_review", 400)
        if len(text) < 10:
            return err("Write at least 10 characters.", "bad_review", 400)
        review, created = db.add_review(product, brand, rating, text, user)
        return jsonify(review), (201 if created else 200)

    @app.post("/api/reviews/<review_id>/helpful")
    def review_helpful(review_id):
        if not review_id.isdigit():
            return err("Review not found.", "not_found", 404)
        voter = hashlib.sha256(f"{request.remote_addr}|{request.headers.get('User-Agent', '')}".encode()).hexdigest()
        review, counted = db.vote_helpful(int(review_id), voter)
        if review is None:
            return err("Review not found.", "not_found", 404)
        return jsonify({**review, "already_voted": not counted})

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    application = create_app()
    application.run(host=application.config["HOST"], port=application.config["PORT"], debug=False)
