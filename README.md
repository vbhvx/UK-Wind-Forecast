# Windward

Windward is a two-service electricity-market dashboard. A React client visualizes analysis produced by a FastAPI backend, including Elexon-oriented market data handling and analysis routines.

## Repository layout

- `frontend/` — Vite, React 19, TypeScript, Recharts, and the browser API client.
- `backend/app/` — FastAPI application, schemas, Elexon client, and analysis module.
- `docker-compose.yml` — production-style frontend and backend containers.

## Run with Docker

Docker is the documented full-stack path:

```bash
cd 22_Windward
docker compose up --build
```

The client is published on `http://localhost:3000`; the API health check is `http://localhost:8000/api/health`.

## Run the frontend locally

```bash
cd frontend
npm install
npm run dev
```

Available frontend checks are `npm run build` and `npm run lint`. The Python backend dependencies are pinned in `backend/requirements.txt`; run it with an environment capable of serving the FastAPI application in `backend/app/main.py` when not using Docker.

The project has no committed environment template. Review `backend/app/main.py` and the Compose configuration before changing API addresses or deployment settings.
