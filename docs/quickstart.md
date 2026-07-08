# Open-Source Quickstart

This guide gets Quainy Vouch running locally with the seeded Quainy sample workspace.

## Prerequisites

- Python 3.12+
- `uv`
- Node.js 22+
- npm
- Docker Desktop, optional

The current MVP is deterministic and local-first. It does not require model keys.

## 1. Configure Environment

```bash
cp .env.example .env
```

The default values are enough for local development.

## 2. Run Without Docker

Install backend dependencies:

```bash
uv sync --extra dev
```

Start the API:

```bash
uv run uvicorn app.main:app --reload --app-dir backend
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Start the frontend:

```bash
npm run dev
```

Open:

- Frontend: `http://localhost:5173`
- API health: `http://127.0.0.1:8000/health`

## 3. Run With Docker Compose

```bash
docker compose up --build
```

Open `http://localhost:5173`.

## 4. Generate The First Draft

1. Open the seeded Quainy workspace.
2. Inspect the sample approved source in the Source Library.
3. Optionally add a `URL page` source by entering a single public page URI and approved page text or HTML.
4. Optionally add a `GitHub release` source by entering a selected public GitHub repo/release URI and approved release-note text.
5. Optionally add a `Notion page` source by entering a selected page URI and approved page text.
6. Generate opportunities.
7. Select an opportunity to create a platform-independent brief.
8. Generate LinkedIn company post drafts.
9. Review evidence, claims, risks, quality, and duplicate memory.
10. Edit, approve, reject with reason, export/copy, or schedule intent.

## 5. Verify The Project

```bash
uv run pytest -q
```

```bash
cd frontend
npm run build
```

Expected current result:

- Backend: all tests pass.
- Frontend: TypeScript and Vite production build pass.
