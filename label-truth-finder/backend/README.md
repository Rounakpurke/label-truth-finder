# Label Truth Finder – backend (Flask)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env    # optional: put your email/GitHub name in OFF_CONTACT
python app.py               # http://127.0.0.1:5001
pytest -q                   # tests (no Ollama or internet needed)
```

## Files
| File | Purpose |
|---|---|
| `app.py` | Flask app, routes, CORS, JSON error handlers |
| `analysis.py` | Builds the report the frontend expects; allergen/sugar matching; online-vs-package comparison |
| `ollama_client.py` | Local Ollama calls (`/api/chat`), JSON-schema output, error mapping |
| `off_client.py` | Open Food Facts / Open Beauty Facts lookups |
| `regulations.py`, `data/regulations.json` | Regulation entries (ships empty, see below) |
| `images.py` | Upload validation; images are re-encoded in memory, never saved |
| `db.py` | SQLite (history, reviews, helpful votes) |

## Endpoints
| Method & path | What it does |
|---|---|
| `GET /api/health` | Backend, database and Ollama/model status |
| `POST /api/analyze` | multipart: `image`, `product_name`, `barcode`, `category`, `country` → report JSON (saved to history) |
| `GET /api/products/search?q=` | Open Food Facts name search |
| `GET /api/history` · `DELETE /api/history` | Saved reports / clear all |
| `GET /api/products/<id>/reviews` | Reviews for a product (`all` = every review) |
| `POST /api/reviews` | JSON `{product, brand, rating 1-5, text ≥10 chars, user}` |
| `POST /api/reviews/<id>/helpful` | +1 helpful (one vote per browser/IP+agent) |

Errors are always `{"error": {"code": "...", "message": "..."}}` with no tracebacks.

## How analysis works
1. Image is validated (extension, MIME, real decode, ≤ `MAX_IMAGE_MB`), downscaled and re-encoded as JPEG **in memory** (EXIF dropped).
2. Call 1 – vision model transcribes only what is printed (JSON schema; unreadable → `null`/empty).
3. Ingredients are split in Python; call 2 (text only) adds *general-knowledge* explanations, clearly labelled as such.
4. Barcode (typed, or read from the photo and checksum-valid) → Open Food Facts lookup. Name-only searches are accepted only on a clear name match (≥60% of your words), otherwise 404 – nothing is substituted.
5. Package values are never overwritten by online values; differences are listed under `discrepancies`.
6. Possible allergen matches are keyword hits only and never replace the package's declared allergens.

## Regulations
`data/regulations.json` ships with no entries, so every country returns **Not verified** with an explanation. An entry is only reported as `confirmed`/`none_found` if it has `status, explanation, source_name, source_url, date`; otherwise it is downgraded. Add entries only after checking the official source yourself (e.g. FSSAI). Entry format:
```json
{"country": "India", "match": ["ins 123"], "subject": "Example additive", "status": "confirmed",
 "explanation": "...", "source_name": "Regulator name", "source_url": "https://...", "date": "2026-01-31"}
```

## Open Food Facts
Data is community-contributed under the ODbL licence; the app shows source, link and retrieval date for every record. Set `OFF_CONTACT` so requests carry an identifiable User-Agent. Please respect their rate limits.
