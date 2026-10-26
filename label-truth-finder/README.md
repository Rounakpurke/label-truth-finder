# Label Truth Finder

React + Vite frontend, Python Flask backend, local Ollama vision AI (`qwen2.5vl:3b`), SQLite, Open Food Facts. No API keys, no paid services, no cloud LLM.

```
frontend/   React UI (your original design, wired to the backend)
backend/    Flask API, SQLite, Ollama + Open Food Facts clients, tests
```

## Setup on macOS (first time)

**1. Check Python and Node** (Terminal):
```bash
python3 --version     # need 3.10+
node --version        # need 18+
```
Missing? `brew install python node` (Homebrew: https://brew.sh) or install from python.org / nodejs.org.

**2. Check Ollama and the model:**
```bash
ollama list           # must show qwen2.5vl:3b
```
If the Ollama menu-bar app is running, Ollama is already serving. Otherwise run `ollama serve` in its own Terminal window and leave it open. (If it says the address is already in use, it is already running – fine.)

**3. Terminal window A – backend:**
```bash
cd label-truth-finder/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp -n .env.example .env
python app.py
```
Leave this window open. Check it: open http://127.0.0.1:5001/api/health – you want `"status":"ok"`, `"reachable":true`, `"model_installed":true`.

**4. Terminal window B – frontend:**
```bash
cd label-truth-finder/frontend
npm ci
npm run dev
```
Leave it open and open **http://localhost:5173**.

**Next times:** Window A: `cd backend && source .venv/bin/activate && python app.py`. Window B: `cd frontend && npm run dev`.
Keep open: Ollama (app or `ollama serve`), window A and window B.

## Using it
Analyze Product → upload a label photo (and/or barcode, product name). The first analysis after starting Ollama is slow (model loading); later ones are faster. Photos are processed in memory and never saved; reports and reviews are stored in `backend/data/label_truth_finder.db`.

## What works
- Image → ingredients, nutrition (units/basis kept, unreadable = “Not available”, never 0), declared allergens, warnings, barcode, uncertain text
- Ingredient-by-ingredient explanations (labelled general knowledge, not label text)
- Possible allergen matches kept separate from declared allergens
- Open Food Facts / Open Beauty Facts lookup by barcode (and by name for name-only searches), with source URL + date and a package-vs-online discrepancy list
- Persistent history (open / clear), community reviews (rating, helpful votes, duplicate-submit protection)
- Country regulation section (always **Not verified** until you add sourced entries)
- Optional demo mode: `VITE_USE_MOCK=true`

## Known limitations (please read)
- **Regulations are not implemented as live checks.** No official source is queried; results are “Not verified”.
- A 3B vision model can misread labels, especially small, curved or glossy text. Always compare with the package. Use sharp, well-lit, close photos.
- Image-only analysis has no online lookup unless a barcode is typed or clearly readable (by design, to avoid wrong-product matches).
- Allergen keyword matching is naive; absence of a match is **not** proof of safety. People with serious allergies must check the original package and seek professional advice.
- Ingredient explanations come from the small model and may be wrong or missing; unknown items are left blank.
- Reviews have unverified usernames and no abuse protection – fine locally, **not** for public deployment. “Helpful” votes are de-duplicated by IP + browser string only.
- Settings (country, category) stay in browser localStorage; thumbnails are not stored.
- Open Food Facts data is crowd-sourced and can be wrong or outdated.

## Troubleshooting
| Problem | Fix |
|---|---|
| UI says “Cannot reach the backend” | Window A not running, or wrong port. Open http://127.0.0.1:5001/api/health. If you changed `PORT`, set `VITE_API_BASE_URL` in `frontend/.env.local` and restart `npm run dev`. |
| Port 5000 busy | macOS AirPlay Receiver uses it; that's why this project uses **5001**. For another port: `PORT=5002` in `backend/.env`. |
| `Address already in use` (5001/5173) | `lsof -i :5001` then `kill <PID>`; Vite will offer the next free port – but then add that origin to `FRONTEND_ORIGINS` in `backend/.env`. |
| Browser console shows a CORS error | Your page's address isn't in `FRONTEND_ORIGINS` (use exactly `http://localhost:5173` or `http://127.0.0.1:5173`); restart the backend after editing `.env`. |
| “Cannot reach Ollama” | Open the Ollama app or run `ollama serve`; check `curl http://127.0.0.1:11434/api/tags`. |
| “Model … is not installed” | `ollama list`; install with `ollama pull qwen2.5vl:3b`, or set `OLLAMA_MODEL` to the exact name shown. |
| Timeout / very slow | First request loads the model. Raise `OLLAMA_TIMEOUT` in `.env`, close heavy apps, use a closer photo. |
| “Malformed JSON” / garbage reading | Retry with a sharper photo, one panel at a time (ingredients, then nutrition). |
| `pip install` fails | Make sure the venv is active (`(.venv)` in the prompt) and `python3 --version` ≥ 3.10. |
| `npm install` fails | `node --version` ≥ 18; delete `node_modules` and retry. |
| Open Food Facts “timed out / not reached” | Check your internet; the label-photo analysis still works without it. |
