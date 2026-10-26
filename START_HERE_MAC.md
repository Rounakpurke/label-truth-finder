# Label Truth Finder — complete project

This package combines the full project with the S/A/B/C/D grade, Daily Allowance, Alternatives, Detailed Analysis, and two-model Ollama integration. It includes the React entry file `frontend/src/main.jsx`.

## Important
- This ZIP intentionally does **not** include your personal `backend/.env`, `frontend/.env.local`, virtual environment, `node_modules`, or built `dist` folder. Your existing local secrets/database are not included.
- Keep `qwen2.5vl:3b` for reading label images and `gemma4:e2b` for ingredient explanations. The grade is an illustrative educational heuristic, not an official or medical rating. Daily allowances are broad adult reference values.

## First-time setup on Mac
1. Extract this ZIP somewhere such as `~/Downloads/label-truth-finder-complete`.
2. In Terminal, run the backend commands:

```bash
cd ~/Downloads/label-truth-finder-complete/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp -n .env.example .env
```

3. Open `backend/.env` in a text editor if needed. Keep `OLLAMA_MODEL=qwen2.5vl:3b` and set `OLLAMA_EXPLAIN_MODEL=gemma4:e2b`. Do not share that file publicly. Ensure Ollama is running and `ollama list` shows both models.
4. Start backend in that Terminal: `python app.py` (leave it open).
5. Open a second Terminal and run:

```bash
cd ~/Downloads/label-truth-finder-complete/frontend
npm ci
npm run dev
```

6. Open `http://localhost:5173/`. Backend health: `http://127.0.0.1:5001/api/health`.

## Existing project folder
If you want to replace your working copy, first make a backup. This is a **new standalone folder**; test it before deleting or overwriting anything in your current folder. Do not copy your old `node_modules` or `.venv` into it.
