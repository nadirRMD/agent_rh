# Agent RH

FastAPI backend plus a Next.js frontend for the Agent RH project.

## Backend

### Requirements

- Python 3.14 or newer
- `uv` recommended for dependency management

### Install

```bash
uv sync
```

If you prefer `pip`, you can also install the project directly:

```bash
pip install .
```

### Run

```bash
uv run agent-rh
```

The API starts on `http://127.0.0.1:8000` by default.

## Frontend

### Requirements

- Node.js 22 or newer
- `npm`

### Install

```bash
cd frontend
npm install
```

### Run

```bash
cd frontend
npm run dev
```

The UI starts on `http://127.0.0.1:3000` by default and proxies requests to the backend through `frontend/app/api/chat/route.js`.

If your backend runs somewhere else, set `BACKEND_URL` before starting Next.js.

## Frontend authentication

The Next.js app now shows a login screen before the chat interface.

- The signed access token uses `FRONTEND_AUTH_SECRET`

## One-command dev mode

From the repo root, run:

```bash
./dev.sh
```

This starts the backend on `http://127.0.0.1:8000` and the frontend on `http://127.0.0.1:3000`.

On the first run, `dev.sh` will install the frontend dependencies automatically if `frontend/node_modules` is missing.

Before starting, `dev.sh` now checks that both ports are free and clears the local runtime cache in `/tmp/agent-rh-dev` plus the Next.js build output in `frontend/.next`.

It also seeds the frontend auth defaults for local development unless you set your own `FRONTEND_AUTH_SECRET`.

To stop a running dev session cleanly, use:

```bash
./dev.sh --stop
```

## Vercel deployment

Deploy the frontend and backend as two separate Vercel projects from the same repository:

1. Frontend project:
   - Root directory: `frontend`
   - Framework: Next.js
2. Backend project:
   - Root directory: repository root
   - Entry point: `app.py`

Required environment variables:

- Frontend project:
  - `BACKEND_URL` = URL of the deployed backend project
  - `FRONTEND_AUTH_SECRET`
- Backend project:
  - `OPENAI_API_KEY`
  - `FRONTEND_AUTH_SECRET`
  - `JIBBLE_CLIENT_ID`
  - `JIBBLE_CLIENT_SECRET`
  - `MICROSOFT_CLIENT_ID`
  - `MICROSOFT_TENANT_ID` if you do not want the default `common`
  - `MICROSOFT_TIMEZONE` if you do not want the default `Europe/Paris`
  - `AGENT_RH_FRONTEND_ORIGIN` if you want to restrict CORS to a specific frontend domain

For local development, you can keep using:

```bash
./dev.sh
```
