# Quainy Vouch

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/quainy-labs/Quainy-Vouch?style=for-the-badge)](./LICENSE)


Quainy Vouch is a source-grounded content workspace for any organization that needs public communication to stay accurate, reviewable, and tied to approved company knowledge.

It helps a team move from trusted sources to opportunities, briefs, drafts, review, scheduling, and learning signals. It is not an autonomous publisher and it is not a broad internal crawler.

## What It Does

- Collects approved sources, profile details, voice rules, claims, and content pillars.
- Turns source-backed context into timely content opportunities.
- Generates briefs and draft variants for channels such as LinkedIn, Reddit, and Instagram.
- Keeps humans in the approval loop before export, schedule, or publish-like actions.
- Tracks review decisions, rejected ideas, manual performance, and content memory.
- Supports organization users, roles, approval policy, calendar signals, trends, and strategy views.


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

- `VOUCH_DATA_BACKEND=postgres` enables PostgreSQL-backed persistence.
- `VOUCH_MODEL_PROVIDER=deterministic` uses deterministic generation.
- `VOUCH_EMBEDDING_PROVIDER=local_hash` uses local hash embeddings.
- `VOUCH_LINKEDIN_PUBLISHING_PROVIDER=local` uses the credential-free local publishing adapter.

Legacy `QUAINY_*` environment names are still accepted as fallbacks for existing local setups, but new deployments should use the neutral `VOUCH_*` names.

See `.env.example` for the full local configuration.

## AI Providers

The default setup is deterministic and does not require model credentials. Organization AI settings in the app support:

- Deterministic fallback.
- Local runtimes, configured separately for generation and embeddings.
- Cloud LLM providers through editable model, base URL, and secret-reference fields.

The AI settings panel stores environment variable names such as `OPENAI_API_KEY`, not raw secret values.

## Publishing Connections

Publishing settings use OAuth-style connector buttons for LinkedIn, Reddit, and Instagram.

Required OAuth environment variables:

- LinkedIn: `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI`
- Reddit: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_REDIRECT_URI`
- Instagram: `INSTAGRAM_CLIENT_ID`, `INSTAGRAM_CLIENT_SECRET`, `INSTAGRAM_REDIRECT_URI`

Optional scope/version overrides:

- `LINKEDIN_SCOPES`
- `REDDIT_SCOPES`
- `INSTAGRAM_SCOPES`
- `META_OAUTH_VERSION`

LinkedIn publishing is company-page first. The OAuth callback attempts to select an organization/company page target. Personal-profile posting is secondary and should only be enabled through an explicit product flow.

For local development, keep `VOUCH_LINKEDIN_PUBLISHING_PROVIDER=local`. For live LinkedIn API publishing, set `VOUCH_LINKEDIN_PUBLISHING_PROVIDER=api` and configure LinkedIn OAuth.

## Boundaries

- No autonomous publishing by default.
- No hidden broad workspace crawl.
- OAuth tokens are stored server-side and are not returned in API responses.
- Trends must connect to approved company context before becoming usable content.
- Development fixtures are not production onboarding.
- Raw secrets should stay in backend environment variables, not in UI payloads.

## Tech Stack

- Backend: FastAPI, Pydantic, Alembic, PostgreSQL/pgvector support.
- Frontend: Vite, React, TypeScript, CSS modules/stylesheets.
- Local defaults: deterministic model behavior and local hash embeddings.
- Optional providers: OpenAI-compatible client support through the `providers` extra.

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
