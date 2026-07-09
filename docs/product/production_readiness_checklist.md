# Quainy Vouch Production Readiness Checklist

Last updated: 2026-07-09

This checklist tracks the move from deterministic prototype behavior to a production-ready product that real organizations can use end to end.

Quainy Vouch is production-first. Test fixtures and deterministic providers may exist for engineering, but the product experience must never depend on a seeded Quainy workspace or a local demo mode.

The target flow is:

```text
Signup
  -> fast onboarding
  -> organization profile setup or skip
  -> approved source or link setup
  -> ranked source-grounded opportunities
  -> brief creation
  -> target platform and content-type selection
  -> generated draft
  -> human review, edit, save, and approval
  -> publish, schedule, or export
  -> published content ID
  -> performance capture
  -> memory, analytics, and learning loop
```

## Working Rule

Every phase must be architected, developed, tested, and documented before the next phase starts.

Done means a real user can complete the workflow, not merely that an endpoint or placeholder exists.

For each phase:

- [ ] Architecture and data model are defined.
- [ ] API contracts are defined.
- [ ] User flow, empty states, error states, and success states are defined.
- [ ] Backend implementation is complete.
- [ ] Frontend implementation is complete where applicable.
- [ ] Unit and flow tests cover the main risks.
- [ ] Security and tenant boundaries are reviewed.
- [ ] Documentation is updated.
- [ ] Phase gate is recorded in `PHASE_EXECUTION_STATUS.md`.

## Phase 0: Production Scope Lock

Goal: lock the production product scope before implementation starts.

- [x] Define the intended production user flow from signup to learning loop.
- [x] Add this production-readiness checklist.
- [x] Replace local/demo mode as a product goal with production-first requirements.
- [x] Define the production MVP target.
- [x] Add phase-by-phase implementation gates.
- [x] Remove seeded Quainy organization from the intended production experience.
- [x] Define progressive context accuracy, opportunity ranking, publishing IDs, manual performance capture, and one-person-company usefulness as product requirements.
- [ ] Update environment/config naming when implementation begins so production cannot accidentally boot demo fixtures.
- [ ] Confirm first deployment target for production use.
- [ ] Confirm first real beta organization profile.

Acceptance gate:

- [x] The team can point to one checklist that controls the production-readiness work.
- [x] The active phase is clear.
- [x] The current prototype still passes backend tests and frontend build.

## Phase 1: Signup, Auth, And Onboarding

Goal: replace local-owner assumptions with real account and organization setup.

- [ ] Design user account, auth session, organization membership, and onboarding state models.
- [ ] Add signup and login routes.
- [ ] Add authenticated current-user route.
- [ ] Add organization creation during onboarding.
- [ ] Add frictionless organization profile setup with skip-for-later behavior.
- [ ] Add fast source setup entry point for uploads, pasted context, and links.
- [ ] Add onboarding progress that improves as users add more context later.
- [ ] Replace production use of `actor_id="local_user"` with authenticated actor resolution.
- [ ] Add signup, login, onboarding, and first dashboard UI.
- [ ] Add tests for unauthenticated access, signup, org creation, skipped profile, fast source setup, and role ownership.

Acceptance gate:

- [ ] A new user can sign up, create an organization, skip or complete profile setup, add context quickly, and land in the product without Quainy-seeded assumptions.

## Phase 2: Persistent Database

Goal: move durable product data out of the in-memory store.

- [ ] Choose production database target for first release.
- [ ] Implement PostgreSQL repository layer.
- [ ] Add Alembic migrations.
- [ ] Add persistent tables for users, memberships, organizations, profiles, sources, chunks, opportunities, briefs, drafts, approvals, memory, integrations, jobs, and audit logs.
- [ ] Add pgvector-ready chunk storage.
- [ ] Keep deterministic test fixtures available without exposing them as product mode.
- [ ] Update Docker Compose with Postgres and pgvector.
- [ ] Add persistence tests for restart-safe workflows.

Acceptance gate:

- [ ] Restarting the backend does not lose user, organization, source, draft, review, or memory data.

## Phase 3: Tenant Isolation And RBAC

Goal: enforce organization safety server-side.

- [ ] Add central auth dependency for actor resolution.
- [ ] Add central `require_org_role` authorization helper.
- [ ] Enforce membership on every organization-scoped query.
- [ ] Prevent cross-organization source, brief, draft, memory, analytics, integration, and audit access.
- [ ] Record real actor identity in audit logs.
- [ ] Add role-aware frontend actions and permission errors.
- [ ] Add cross-tenant and role regression tests.

Acceptance gate:

- [ ] A user from one organization cannot read or mutate another organization's data by changing IDs.

## Phase 4: Background Jobs

Goal: make ingestion, generation, publishing, and analytics reliable.

- [ ] Design job model and status lifecycle.
- [ ] Add queue backend and worker service.
- [ ] Move source ingestion to jobs.
- [ ] Move source refresh to jobs.
- [ ] Move opportunity generation to jobs.
- [ ] Move draft generation to jobs.
- [ ] Move publishing and analytics import to jobs.
- [ ] Add retry, failure, and job-log behavior.
- [ ] Add frontend progress, retry, and failure states.

Acceptance gate:

- [ ] Long-running operations complete through tracked jobs instead of synchronous request work.

## Phase 5: Real LLM Provider Layer

Goal: introduce real model reasoning without weakening source-grounding.

- [ ] Define structured output schemas for opportunities, briefs, drafts, claim extraction, risk checks, and strategy recommendations.
- [ ] Implement real provider calls behind existing provider interfaces.
- [ ] Keep deterministic provider for tests.
- [ ] Add prompt version metadata to every generated artifact.
- [ ] Add model call logging with provider, model, prompt version, source IDs, and token/cost metadata when available.
- [ ] Add invalid-output repair or safe failure behavior.
- [ ] Add refusal behavior for insufficient context.
- [ ] Add evaluation tests for good, stale, duplicate, unsupported, thin-context, and off-voice cases.

Acceptance gate:

- [ ] A real model provider can generate useful content while unsupported claims remain flagged or blocked.

## Phase 6: BYO LLM And Local LLM Support

Goal: let organizations use their own model provider or local model runtime.

- [ ] Design organization-level AI provider settings.
- [ ] Support OpenAI.
- [ ] Support OpenAI-compatible endpoints.
- [ ] Support a local runtime path such as Ollama or vLLM.
- [ ] Separate generation model config from embedding model config.
- [ ] Add encrypted secret storage or secret-vault abstraction.
- [ ] Add provider connection test endpoint.
- [ ] Add Settings UI for AI providers.
- [ ] Ensure provider secrets are never returned in API responses or audit logs.

Acceptance gate:

- [ ] An organization can configure its own provider, test it, and generate content with it.

## Phase 7: Source Setup And Knowledge Readiness

Goal: make source setup feel like a guided company knowledge base.

- [ ] Add knowledge readiness model.
- [ ] Score profile completeness, approved source count, freshness, pillar coverage, and retrieval quality.
- [ ] Add guided source onboarding for pasted text, file upload, URL, release notes, selected Notion page, and later Drive.
- [ ] Implement durable file upload storage.
- [ ] Implement safe URL fetching and extraction.
- [ ] Add source refresh scheduling.
- [ ] Add redaction hooks for secrets, private names, financials, and internal-only details.
- [ ] Add source versioning and revocation tests.
- [ ] Rank opportunities better as the organization adds more approved context.

Acceptance gate:

- [ ] A new organization can add approved context and understand whether there is enough safe knowledge to generate useful opportunities.

## Phase 8: Opportunity, Brief, And Draft Intelligence

Goal: make the core content intelligence loop excellent.

- [ ] Upgrade opportunity engine to use profile, sources, freshness, memory, calendar, trends, and performance.
- [ ] Rank opportunities by source support, relevance to today's date, important events, trends, audience fit, tone fit, freshness, and prior performance.
- [ ] Keep briefs platform-independent.
- [ ] Improve platform adapters for LinkedIn, blog, newsletter, Instagram caption, and carousel outline.
- [ ] Add explicit target platform and content-type selection before draft generation.
- [ ] Show why-now rationale, source basis, risks, confidence, and unsupported claims on every artifact.
- [ ] Add draft comparison and evidence inspection UX.
- [ ] Add tests for thin context refusal, source IDs, duplicate penalties, and platform-independent briefs.

Acceptance gate:

- [ ] A real organization can move from approved context to reviewable drafts with visible evidence and risk metadata.

## Phase 9: Publishing And Export

Goal: safely send approved content outside the product.

- [ ] Keep manual export as the safe default.
- [ ] Implement LinkedIn OAuth.
- [ ] Add company page selection.
- [ ] Validate publishing permissions.
- [ ] Publish only approved content.
- [ ] Store provider result and published URL.
- [ ] Store durable published/exported content IDs for every external artifact.
- [ ] Preserve approved content on publish failure.
- [ ] Add publish audit logs.
- [ ] Add frontend connect, page select, publish, export, and failure recovery UI.
- [ ] Add manual performance entry by published/exported content ID when direct analytics is unavailable.

Acceptance gate:

- [ ] A reviewed and approved post can be published or exported without bypassing approval, and it has an ID that can receive performance data later.

## Phase 10: Analytics, Learning, And Strategy

Goal: improve recommendations without letting metrics override truth.

- [ ] Import or record post performance metrics.
- [ ] Support manual performance capture by published/exported content ID.
- [ ] Maintain post memory by platform and content type.
- [ ] Generate preference suggestions from edits and rejections.
- [ ] Require human approval before durable profile memory changes.
- [ ] Build strategy recommendations with evidence and confidence.
- [ ] Use performance stats to improve opportunity ranking and draft strategy over time.
- [ ] Add tests proving analytics influence recommendations but not source truth.

Acceptance gate:

- [ ] The product learns from usage while keeping source truth, brand rules, and human approval in control.

## Phase 11: Security, Ops, And Production Deployment

Goal: make the product deployable, observable, recoverable, and safe.

- [ ] Add production Docker setup.
- [ ] Add production environment template.
- [ ] Add health and readiness checks.
- [ ] Add structured logs.
- [ ] Add error monitoring plan.
- [ ] Add rate limiting.
- [ ] Add CORS policy for production.
- [ ] Add TLS and secret management notes.
- [ ] Add backup and restore process for production storage.
- [ ] Add data deletion and retention policy.
- [ ] Add CI checks for backend tests, frontend build, migrations, and lint/type checks.

Acceptance gate:

- [ ] Staging can run with production-like services and recover from backup.

## Phase 12: Real Organization Beta

Goal: validate the complete product with real organizations.

- [ ] Select 1 to 3 trusted beta organizations.
- [ ] Onboard each organization without engineer intervention where possible.
- [ ] Connect or add real approved sources.
- [ ] Configure real or BYO model provider.
- [ ] Generate opportunities and drafts.
- [ ] Complete human review and approval.
- [ ] Export or publish approved content.
- [ ] Record feedback, quality scores, and missing workflow steps.
- [ ] Fix beta blockers before broader release.

Acceptance gate:

- [ ] A real organization can use Quainy Vouch from signup to approved/published/exported content with trusted source evidence.
