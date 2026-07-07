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

## Format Adapters

Interface: `FormatAdapter`

Current concrete adapter:

- `LinkedInCompanyPostAdapter`

Purpose:

- Convert a platform-independent `ContentBrief` into platform-specific generation variants and quality checks.
- Keep LinkedIn out of core company intelligence so later blog, newsletter, Instagram caption, and carousel adapters can reuse the same brief.

Acceptance note:

- Core draft generation now receives a `FormatAdapter`.
- The LinkedIn wording and LinkedIn quality constraints live in `backend/app/format_adapters.py`.

## Model Providers

Interfaces:

- `ModelProvider`
- `EmbeddingProvider`

Purpose:

- Allow OpenAI, local models, mock providers, and future providers without changing the agent modules.
- Keep tests independent from live model calls.
- Support structured outputs and embeddings through replaceable providers.

Current phase scope:

- Contract only.
- The deterministic prototype remains in place until the relevant intelligence phase is active.

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
