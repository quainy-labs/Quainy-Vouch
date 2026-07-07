# Quainy Vouch

Quainy Vouch is a local-first, source-grounded content intelligence product for turning approved company knowledge into human-reviewed public communication.

The current codebase contains a local prototype of the MVP heart:

- approved source ingestion
- Quainy company profile and voice rules
- source-backed opportunity generation
- LinkedIn-style draft variants
- claim, risk, quality, freshness, and duplicate metadata
- human approve, reject, export, and memory actions

This prototype is intentionally deterministic. It proves the trust workflow before live model-provider adapters are introduced.

## Project Docs

- [Contributing](./CONTRIBUTING.md)
- [Architecture API Schema](./docs/architecture/api_schema.yaml)
- [Architecture Database Schema](./docs/architecture/database_schema.sql)
- [Module Interfaces](./docs/architecture/module_interfaces.md)

## Local Development

Backend:

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload --app-dir backend
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the frontend at `http://localhost:5173`. The API runs at `http://127.0.0.1:8000`.

## Tests

```bash
uv run pytest -q
```

## Docker Compose

```bash
docker compose up --build
```

The Compose setup starts the backend and frontend only. PostgreSQL, pgvector, queues, and model adapters are later hardening steps.

## Current Boundaries

- No automated LinkedIn publishing.
- No broad internal workspace crawling.
- No live model calls.
- No hidden data collection.
- Seeded data comes from a small public sample context in `backend/app/sample_data.py`.

## Roadmap Direction

1. Persistent storage for organizations, profiles, sources, chunks, memory, and audit logs.
2. Provider abstractions for models and embeddings.
3. Stronger ingestion, retrieval, and claim grounding.
4. Review, approval, export, calendar, and memory hardening.
5. Additional source connectors and format adapters.
