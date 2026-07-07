# Contributing To Quainy Vouch

Quainy Vouch is built in small, reviewable increments. Before opening or implementing a change, keep the change scoped to one product area and avoid mixing architecture, backend, frontend, and documentation churn unless the feature needs it.

## Build Order

1. Keep the product trust model intact.
2. Make backend behavior testable before depending on it in the UI.
3. Keep platform-specific behavior behind adapters.
4. Add documentation when behavior or setup changes.

## Local Checks

Run backend tests:

```bash
uv run pytest -q
```

Run frontend build:

```bash
cd frontend
npm run build
```

## Product Discipline

- Keep approved-source filtering server-side.
- Keep LinkedIn as an adapter, not the product boundary.
- Keep humans in control before publishing or export.
- Do not add broad internal access in the MVP.
- Do not mark a feature complete until the user workflow, edge states, tests, documentation, and UX expectations are covered.
- Design every screen around the person reviewing source-backed content: evidence, risk, relevance, and next action should be easy to understand.
