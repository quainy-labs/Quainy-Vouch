# Quainy Dogfood Evaluation Log

Last updated: 2026-07-07

Scope: Sprint 3.3 - MVP Dogfood With Quainy

This log evaluates the seeded Quainy workspace against the MVP promise: source-grounded LinkedIn-style company drafts with human review, memory, and manual export/queue.

## Evaluation Setup

- Workspace: Quainy seeded local workspace.
- Source: `Quainy Vouch sample context`.
- Profile: Quainy voice rules, preferred phrases, banned phrases, approved claims, forbidden claims, and content pillars.
- Format: LinkedIn company post.
- Review standard:
  - Approval-ready: could be approved with only light edits.
  - Near approval-ready: useful but needs a small reviewer edit.
  - Needs revision: source support, specificity, risk, or voice issue must be fixed.

## Generated Opportunity/Draft Cases

| Case | Opportunity Angle | Variant | Human Rating | Review Notes |
| --- | --- | --- | --- | --- |
| 01 | Approved company knowledge | Practical | Approval-ready | Clear source-backed framing and human approval message. |
| 02 | Approved company knowledge | Reflective | Approval-ready | Good Quainy fit; useful trust framing. |
| 03 | Approved company knowledge | Direct | Near approval-ready | Strong, but could use a sharper first line. |
| 04 | Source-backed public content | Practical | Approval-ready | Specific and aligned with product source of truth. |
| 05 | Source-backed public content | Reflective | Near approval-ready | Useful, but middle paragraph can be more concrete. |
| 06 | Source-backed public content | Direct | Approval-ready | Strongest operational framing. |
| 07 | Product judgment | Practical | Approval-ready | Connects judgment to source visibility well. |
| 08 | Product judgment | Reflective | Near approval-ready | Good direction; needs one Quainy-specific example. |
| 09 | Product judgment | Direct | Approval-ready | Clear critique of generic AI content. |
| 10 | Production readiness | Practical | Approval-ready | Voice matches Quainy: serious, practical, grounded. |
| 11 | Production readiness | Reflective | Near approval-ready | Good product tone; trim one general AI sentence. |
| 12 | Production readiness | Direct | Approval-ready | Strong source-to-review flow. |
| 13 | Human approval | Practical | Approval-ready | Makes the trust model understandable. |
| 14 | Human approval | Reflective | Approval-ready | Good human-in-control framing. |
| 15 | Human approval | Direct | Near approval-ready | Useful, but a little repetitive with source-backed note. |
| 16 | Review workflow | Practical | Approval-ready | Shows edit/approve/export value clearly. |
| 17 | Review workflow | Reflective | Near approval-ready | Good but should mention reviewer evidence more directly. |
| 18 | Review workflow | Direct | Approval-ready | Concise and product-specific. |
| 19 | Duplicate memory | Practical | Near approval-ready | Useful concept; needs clearer example of memory benefit. |
| 20 | Duplicate memory | Direct | Needs revision | Too abstract; should add a concrete previous-post comparison. |

## Acceptance Summary

- Approval-ready or near approval-ready cases: 19 of 20.
- Unsupported claims: flagged when high-risk unsupported metrics or market claims are introduced during review.
- Duplicate checks: approved/exported draft memory produces similar-post warnings on later drafts.
- Labor reduction: the flow is meaningfully faster than writing from scratch once sources and profile are present, but the review desk still needs stronger source excerpt mapping in later hardening.

## Automated Regression Command

```bash
uv run python scripts/run_eval.py
```

The runner uses `docs/evaluation/golden_cases.json` and writes `docs/evaluation/reports/latest.json`.

## Human Evaluation Notes

- Best current use: Quainy company-page drafts about source-backed communication, product judgment, production readiness, and human approval.
- Most common edit needed: make the first line more specific to the opportunity.
- Most important trust signal: seeing claims, source chunks, risk warnings, similar memory, and decision history in the same review flow.
- Biggest MVP limitation: generated body text is deterministic and template-like until a real model provider is wired behind the existing provider contract.
