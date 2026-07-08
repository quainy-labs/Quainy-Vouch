# MVP Bug List

Last updated: 2026-07-07

Scope: Sprint 3.3 - MVP Dogfood With Quainy

## Open Bugs And Product Gaps

| ID | Severity | Area | Issue | Suggested Fix |
| --- | --- | --- | --- | --- |
| MVP-001 | Medium | Draft quality | Deterministic drafts can feel repetitive across variants. | Wire a real model provider behind the `ModelProvider` contract with structured outputs. |
| MVP-002 | Medium | Claim grounding | Source-map candidates are overlap-based and can miss nuanced support. | Add stronger sentence-level retrieval and claim-to-evidence scoring. |
| MVP-003 | Medium | Review UX | Review desk shows source chunks but does not highlight exact supporting spans. | Add claim-to-source highlighting in the evidence panel. |
| MVP-004 | Low | Queue | Calendar is a queue list, not a calendar grid. | Add week/month calendar view after MVP hardening. |
| MVP-005 | Low | Export | Export copies text only; hashtags and metadata are not separately controllable. | Add export package with body, hashtags, source summary, and reviewer notes. |
| MVP-006 | Low | Evaluation | Dogfood ratings are documented manually. | Add a repeatable evaluation command that records generated cases as JSON. |

## Release Blockers

No Phase 3 release blockers remain for the local open-source MVP slice.

## Follow-Up After MVP

- Add persistent database repositories.
- Add real model provider integration.
- Add richer evaluator harness.
- Add source-span highlighting.
- Add proper calendar grid and queue filters.
