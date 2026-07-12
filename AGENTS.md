# AGENTS.md

## Scope
This file applies to the whole repository.

## Context Discipline
- Keep context small. Read only files needed for the current task.
- Prefer `rg` and focused `sed -n` ranges over opening large files.
- Do not load broad product docs unless the task directly asks for them.
- Preserve user changes. Do not revert unrelated modified files.

## Project Shape
- Quainy Vouch is a source-grounded content workspace for turning approved company knowledge into human-reviewed public content.
- Backend: FastAPI app in `backend/app`.
- Frontend: Vite + React app in `frontend/src`.
- Scripts: local setup, evaluation, and workspace creation in `scripts`.
- Product and architecture docs live in `docs`.

## Common Commands
- Backend dev: `uv run uvicorn app.main:app --reload --app-dir backend`
- Frontend dev: `cd frontend && npm run dev`
- Backend tests: `uv run pytest -q`
- Frontend build: `cd frontend && npm run build`
- Quainy sample workspace: `uv run --extra providers python scripts/create_quainy_test_workspace.py`

## UI Product Direction
- Prefer browse-first screens with explicit edit/save actions.
- Keep section navigation local to the current feature area.
- Do not reintroduce global Sources or Voice panels across unrelated sections.
- Avoid mixed display/edit states unless the user intentionally enters edit mode.

## Editing Rules
- Use existing app patterns before adding new abstractions.
- Keep changes scoped to the request.
- Use `apply_patch` for manual edits.
- Keep secrets out of the repository.
