# Windward frontend

The Windward browser client is a Vite/React 19 application. It renders the dashboard and calls the companion FastAPI service through `src/api/client.ts`.

```bash
cd 22_Windward/frontend
npm install
npm run dev
```

Use `npm run build` for a production bundle, `npm run preview` to serve it locally, and `npm run lint` for Oxlint. For the complete application, start the repository-level Compose stack; it exposes this UI on port 3000 and the API on port 8000.
