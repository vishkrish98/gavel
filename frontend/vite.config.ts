import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
// In dev (`npm run dev`), proxy API calls to the FastAPI backend (run.py / uvicorn on 8000) so
// api.ts's same-origin fetches work without CORS. In production, run.py serves frontend/dist
// from the same FastAPI app, so no proxy is needed there.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
