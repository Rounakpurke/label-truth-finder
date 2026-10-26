# ZIP inspection and verification report

Inspection date: 2026-10-26

## Contents found
- `frontend/`: React 18 + Vite UI, pages for Dashboard, Analyze, History, Reviews and Settings, API service, and clearly separated mock data.
- `backend/`: Flask API, SQLite persistence, image validation/re-encoding, Ollama client, Open Food Facts/Open Beauty Facts client, conservative regulation-data loader, and pytest tests.
- Root, frontend and backend README/setup files, package lockfile, and environment templates.

## Findings
- Frontend and backend are wired together: the frontend defaults to `http://127.0.0.1:5001`; Vite uses port `5173`; Flask defaults to port `5001`; CORS allows localhost Vite origins.
- Mock data exists but is opt-in via `VITE_USE_MOCK=true`; the example config sets it to `false`.
- The model receives image bytes as base64 through Ollama's local `/api/chat` endpoint. Image processing is in-memory and re-encodes images to JPEG.
- SQLite stores report history, reviews and helpful votes. The database is created on backend startup.
- Regulatory data ships empty, and the regulation module defaults to `not_verified`; no live official-source verification is implemented.
- Existing tests cover input validation, mocked successful analysis, Ollama failures, online lookup behavior, history and review flows.
- Documentation was made safer for repeat setup: environment templates use `cp -n`, and frontend setup uses `npm ci` to respect the committed lockfile.

## Tests actually run in this environment
- Python source syntax compilation: passed for all 12 backend Python files.
- JSON parsing: passed for all 3 JSON files.
- Frontend production build: attempted, but could not run because dependency installation was interrupted and left a broken/partial `node_modules` (`vite: Permission denied`). The partial directory was removed from the deliverable.
- Backend pytest suite: not run. Flask is not installed in the execution environment, and package installation could not reach the package index due to unavailable DNS/network access.
- Live Ollama, model inference, Open Food Facts internet requests, and browser integration: not run in this environment.

## Important limitations
The static checks do not prove runtime correctness. Run the documented commands on the Mac after dependencies install. Confirm the health endpoint reports Ollama reachable and the model installed before testing image analysis. Allergen matching is heuristic, online product data is community-contributed, and regulatory status remains Not verified unless a dated official source has been curated.
