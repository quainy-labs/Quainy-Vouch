# Module Interfaces

Phase: 0.2 - Data Model And Architecture Lock

The code-level interfaces live in `backend/app/contracts.py`. These interfaces match the roadmap modules and let each module be implemented independently in later phases.

## Source Connectors

Interface: `SourceConnector`

Purpose:

- Extract text and metadata from manual notes, markdown, text files, URLs, and later selected private sources.
- Keep source-specific extraction separate from ingestion and retrieval.

Current phase scope:

- Contract only.
- Manual markdown/text behavior remains a local prototype.

## Context Retriever

Interface: `ContextRetriever`

Purpose:

- Return approved, organization-scoped source chunks.
- Enforce source approval and tenant boundaries server-side.

Later implementation must never retrieve disabled or cross-organization chunks.

## Agent Modules

Interfaces:

- `ContentOpportunityGenerator`
- `RelevanceScorer`
- `BriefBuilder`
- `DraftGenerator`
- `ClaimExtractor`
- `ClaimGroundingChecker`
- `QualityRiskChecker`
- `DuplicateChecker`
- `ReviewerPackageBuilder`
- `LearningSignalRecorder`

Purpose:

- Keep the agent modular instead of one giant prompt.
- Make opportunity generation, brief creation, draft generation, claim checking, risk checking, duplicate checking, review packaging, and learning signals independently testable.

Current concrete Sprint 2.1 implementation:

- `backend/app/opportunities.py`
- `OpportunityGenerator`
- `RelevanceScorer`
- `FreshnessScorer`

The opportunity generator returns only source-backed opportunities and returns an empty list when approved context is too thin.

## Format Adapters

Interface: `FormatAdapter`

Current concrete Sprint 2.2 pieces:

- `PlatformIndependentBriefBuilder`
- `LinkedInCompanyPostAdapter`

Purpose:

- Convert a platform-independent `ContentBrief` into platform-specific generation variants and quality checks.
- Keep LinkedIn out of core company intelligence so later blog, newsletter, Instagram caption, and carousel adapters can reuse the same brief.
- Store generation metadata on each draft so reviewers can see which adapter and prompt contract produced it.

Acceptance note:

- Core draft generation now receives a `FormatAdapter`.
- `ContentBrief.objective` stays platform-independent.
- The LinkedIn wording and LinkedIn quality constraints live in `backend/app/format_adapters.py`.

Current concrete Sprint 2.3 implementation:

- `backend/app/drafts.py`
- `SourceGroundedDraftGenerator`

The draft generator creates three adapter-owned variants, uses approved evidence chunks, stores source IDs and source-map candidates, and records adapter/prompt metadata for reviewer visibility.

Current concrete Sprint 2.4 implementation:

- `backend/app/risk_checks.py`
- `SimpleClaimExtractor`
- `SourceClaimGroundingChecker`
- `QualityRiskChecker`

Draft generation and draft edits rerun claim grounding, banned phrase checks, staleness warnings, generic-content warnings, and approval-blocking risk checks before a draft can be cleanly approved.

Current concrete Sprint 2.5 implementation:

- `PostMemory`
- `idea_fingerprint`
- `duplicate_check`

Duplicate memory compares drafts against approved/exported memory using text similarity, idea fingerprints, and local embedding cosine similarity. Similar previous posts are returned in draft review metadata for reviewer visibility.

Current concrete Sprint 3.1 implementation:

- `ReviewerPackage`
- `ApprovalDecision`
- Review desk UI

The reviewer package includes source evidence, warnings, duplicate memory, claims, and decision history. Review actions persist approve/reject/export decisions, reject requires a reviewer reason, and saved draft edits refresh review checks.

Current concrete Sprint 3.2 implementation:

- Manual draft scheduling
- Calendar/queue API
- Queue UI

Drafts can be approved, exported/copied, or assigned a manual scheduled date/time. The queue lists approved, scheduled, and exported drafts for the organization.

Current concrete Sprint 3.3 implementation:

- Seeded Quainy workspace
- Quainy dogfood evaluation log
- MVP bug list

The local MVP has a seeded Quainy workspace, approved sample source ingestion, a documented 20-case dogfood review, and a public MVP issue list for open-source hardening.

Current concrete Sprint 4.2 implementation:

- Golden cases: `docs/evaluation/golden_cases.json`
- Eval runner: `scripts/run_eval.py`
- Regression report guide: `docs/evaluation/regression_reports.md`

The evaluation harness runs deterministic source-backed, unsupported-claim, and duplicate-memory cases without live model calls.

Current concrete Sprint 4.3 implementation:

- Provider factories: `build_model_provider`, `build_embedding_provider`
- Default deterministic model provider
- Optional OpenAI model provider adapter
- Local hash embedding provider
- Prompt version registry

Generated drafts store adapter, prompt, model provider, and embedding provider metadata. Tests use deterministic providers and require no live API calls.

Current concrete Sprint 5.1 implementation:

- `UrlPageConnector`
- `POST /sources/{source_id}/refresh`

URL sources accept one selected public `http(s)` page URI, strip unsafe/non-content HTML, store connector metadata, and refresh by re-ingesting the selected page snapshot. The connector does not crawl domains by default.

Current concrete Sprint 5.2 implementation:

- `GitHubReleaseConnector`

GitHub release sources accept a selected public `github.com/{owner}/{repo}` or release/tag URI, extract pasted public release/changelog text, and store owner, repo, release reference, release date, and public-only access metadata. The connector does not request private repo access or crawl full repositories.

Current concrete Sprint 5.3 implementation:

- `NotionSelectedPageConnector`

Notion page sources accept only selected page URIs, store selected-page scope metadata, and rely on source disable/archive as the MVP revocation path. Source access actions are visible through source audit logs.

Current concrete Sprint 6.1 implementation:

- `BlogOutlineAdapter`

The blog outline adapter reuses the same platform-independent `ContentBrief` as the LinkedIn adapter. It renders markdown blog outlines with a title, introduction, reader intent, three source-backed sections, and a conclusion. The Review Desk can generate either LinkedIn company posts or blog outlines from the selected brief without rebuilding the opportunity, retrieval, risk, or approval flow.

Current concrete Sprint 6.2 implementation:

- `NewsletterEmailAdapter`

The newsletter adapter also reuses the platform-independent `ContentBrief`. It renders email drafts with subject line options, opening, context, source-backed detail, takeaway, and source references. Newsletter voice is separated from LinkedIn formatting while preserving the same source-grounded truth and review workflow.

Current concrete Sprint 6.3 implementation:

- `InstagramCaptionAdapter`
- `InstagramCarouselOutlineAdapter`

Instagram adapters reuse the same `ContentBrief` while keeping visual-first constraints in adapter-owned output. Captions include visual direction, short caption copy, source-backed notes, and hashtag guidance. Carousel outlines include visual direction, five slide plans, source-backed detail, and a separate caption note.

## Model Providers

Interfaces:

- `ModelProvider`
- `EmbeddingProvider`

Purpose:

- Allow OpenAI, local models, mock providers, and future providers without changing the agent modules.
- Keep tests independent from live model calls.
- Support structured outputs and embeddings through replaceable providers.

Current phase scope:

- `backend/app/providers.py` includes deterministic local model and embedding providers, an optional OpenAI model provider adapter, and provider factory functions.
- `backend/app/prompt_registry.py` stores prompt version names used by briefs and format adapters.
- Tests use deterministic providers and never require live model calls.
- Draft generation metadata stores model, embedding, adapter, and prompt version details.

## Storage Boundary

Draft schema:

- `docs/architecture/database_schema.sql`

Purpose:

- Represent the core entities from the roadmap before implementing persistent repositories.
- Preserve future pgvector support while allowing a local SQLite path during early development.

## API Boundary

Draft schema:

- `docs/architecture/api_schema.yaml`

Purpose:

- Declare the REST surface before implementation expands.
- Keep the UI and API aligned with the roadmap workflows.
