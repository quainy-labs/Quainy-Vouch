# Regression Reports

The deterministic evaluation harness writes JSON reports that can be compared before and after prompt, adapter, retrieval, or risk-check changes.

Run:

```bash
uv run python scripts/run_eval.py
```

Default output:

```text
docs/evaluation/reports/latest.json
```

To save a named report:

```bash
uv run python scripts/run_eval.py --output docs/evaluation/reports/2026-07-07-baseline.json
```

## Current Golden Coverage

- Source-backed Quainy flow can generate reviewable drafts.
- Unsupported high-risk metric claims are flagged and blocked.
- Duplicate memory produces similar-post warnings.

## CI Command

```bash
uv run pytest backend/tests/test_evaluation_harness.py -q
```

The test runs the evaluation harness against `docs/evaluation/golden_cases.json` and fails if any golden case fails.
