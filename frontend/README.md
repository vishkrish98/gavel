# Gavel frontend

React + Vite + TypeScript. Normally you don't need to touch this directory directly — `python
run.py` from the repo root serves the already-built `dist/` (committed to the repo, so a fresh
clone needs no Node at all).

## Developing

```bash
npm install
npm run dev
```

Opens on `http://localhost:5173` with hot reload. `vite.config.ts` proxies `/api` and `/health`
to the FastAPI backend on `http://127.0.0.1:8000` — start that separately with `python run.py`
(or `uvicorn backend.main:app --reload` from the repo root) while developing.

## Building

```bash
npm run build
```

Outputs to `dist/`, which is what `run.py` serves in production. Commit `dist/` after any change
here — `run.py` only rebuilds automatically if `dist/` is missing and Node is available.

## Structure

```
src/
  api.ts          — fetch wrapper for every backend route
  types.ts        — TypeScript types matching the backend's JSON shapes
  agentTheme.ts   — the 7 agent nameplates (name, role, color)
  App.tsx         — top-level layout, tab navigation, run polling
  screens/        — one component per screen (Start, Rules, Run, Review, Scenarios,
                    Consistency, Drafts, Cost)
  components/     — shared UI (state boxes, verdict chips, the injection banner, nameplates,
                    the event feed)
```
