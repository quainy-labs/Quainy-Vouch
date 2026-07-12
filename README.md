# Quainy Vouch

Quainy Vouch is a source-grounded content workspace for teams that need public communication to stay accurate, reviewable, and tied to approved company knowledge.

It helps a team move from trusted sources to opportunities, briefs, drafts, review, scheduling, and learning signals. It is not an autonomous publisher and it is not a broad internal crawler.

## What It Does

- Collects approved sources, profile details, voice rules, claims, and content pillars.
- Turns source-backed context into timely content opportunities.
- Generates briefs and draft variants for channels such as LinkedIn, blog, newsletter, and Instagram.
- Keeps humans in the approval loop before export, schedule, or publish-like actions.
- Tracks review decisions, rejected ideas, manual performance, and content memory.
- Supports organization users, roles, approval policy, calendar signals, trends, and strategy views.


## Tech Stack

- Backend: FastAPI, Pydantic, Alembic, PostgreSQL/pgvector support.
- Frontend: Vite, React, TypeScript, CSS modules/stylesheets.
- Local defaults: deterministic model behavior and local hash embeddings.
- Optional providers: OpenAI-compatible client support through the `providers` extra.

## Quickstart

Copy environment settings:

```bash
cp .env.example .env
```

Install backend dependencies:

```bash
uv sync --extra dev
```

Run the API:

```bash
uv run uvicorn app.main:app --reload --app-dir backend
```

Install and run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The API defaults to `http://127.0.0.1:8000`.

## Create A Sample Workspace

With the API running, create a Quainy test workspace:

```bash
uv run --extra providers python scripts/create_quainy_test_workspace.py
```

The script creates a fresh owner account, organization profile, approved sources, opportunities, a brief, and a LinkedIn draft. It prints the generated email and password at the end.

For local model generation, make sure Ollama or another OpenAI-compatible local runtime is reachable at the configured base URL.

## Useful Commands

Run backend tests:

```bash
uv run pytest -q
```

Build the frontend:

```bash
cd frontend
npm run build
```

Run the deterministic evaluation harness:

```bash
uv run python scripts/run_eval.py
```

Run the full local stack with Docker Compose:

```bash
docker compose up --build
```

## Important Environment Flags

- `QUAINY_DATA_BACKEND=postgres` enables PostgreSQL-backed persistence.
- `QUAINY_FIXTURE_MODE=none` keeps seeded sample data off.
- `QUAINY_FIXTURE_MODE=sample` enables local sample fixtures for development.
- `QUAINY_MODEL_PROVIDER=deterministic` uses deterministic generation.
- `QUAINY_EMBEDDING_PROVIDER=local_hash` uses local hash embeddings.
- `QUAINY_LINKEDIN_PUBLISHING_PROVIDER=local` uses the credential-free local publishing adapter.

See `.env.example` for the full local configuration.

## Boundaries

- No autonomous publishing by default.
- No hidden broad workspace crawl.
- No live LinkedIn OAuth flow by default.
- Trends must connect to approved company context before becoming usable content.
- Development fixtures are not production onboarding.
- Raw secrets should stay in backend environment variables, not in UI payloads.

## Documentation

- [Open-source quickstart](./docs/quickstart.md)
- [Security notes](./docs/security.md)
- [Backup and restore guide](./docs/backup_restore.md)
- [Frontend production requirements](./docs/product/frontend_production_requirements.md)
- [Production readiness checklist](./docs/product/production_readiness_checklist.md)
- [System overview](./docs/architecture/system_overview.md)
- [API schema](./docs/architecture/api_schema.yaml)
- [Database schema](./docs/architecture/database_schema.sql)
- [Contributing](./CONTRIBUTING.md)

## License

Apache-2.0. See [LICENSE](./LICENSE).
