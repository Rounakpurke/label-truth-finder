# Label Truth Finder – frontend (React + Vite)

All backend calls live in `src/services/api.js`.

- Backend URL: `VITE_API_BASE_URL` (default `http://127.0.0.1:5001`)
- Demo mode (no backend, fake data clearly badged): `VITE_USE_MOCK=true`

Copy `.env.example` to `.env.local` to change either, then restart `npm run dev`.

```bash
npm ci
npm run dev      # http://localhost:5173
npm run build
```
See the top-level README for the full-stack setup.
