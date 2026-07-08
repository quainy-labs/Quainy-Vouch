# Security Notes

Quainy Vouch is designed around controlled context, source visibility, and human approval. The current open-source MVP is local-first and intentionally avoids broad integrations.

## Current MVP Boundaries

- No automated LinkedIn publishing.
- No LinkedIn OAuth.
- No Slack, email, Drive, or broad workspace crawling.
- No live model calls by default.
- No hidden data collection.
- No training on user data.
- Runtime storage is in memory for the current local prototype.

LinkedIn publishing and analytics research is tracked in `docs/integrations/linkedin_api_research.md`. Manual export remains the safe default until app permissions, OAuth, page roles, audit logging, and failure handling are implemented.

## Source Safety Model

The product only uses sources explicitly added to the workspace and marked as approved.

Source states:

- `approved`: available for retrieval, opportunity generation, brief building, and drafts.
- `disabled`: retained but unavailable to retrieval or generation.
- `archived`: retained for history but unavailable to active generation.

Server-side retrieval filters by organization and source approval status.

## Website And URL Sources

URL sources are single selected public pages.

Current policy:

- Only `http` and `https` page URIs are accepted.
- The system does not crawl entire domains.
- URL page ingestion strips scripts, styles, and HTML tags before chunking.
- Refresh re-ingests the selected page snapshot and creates a new source document version when content changes.
- Broad crawling, sitemap ingestion, authentication, and private-site access are outside the current sprint.

## GitHub Public Release Sources

GitHub release sources are selected public repository or release-note pages.

Current policy:

- Only `https://github.com/{owner}/{repo}` style URIs are accepted.
- Release/tag URIs are allowed for one selected public repo.
- No GitHub token is required.
- No private repository access is requested.
- The connector extracts pasted public release/changelog text and records owner, repo, release reference, and release date metadata when present.
- The system does not clone repos or crawl all issues, pull requests, branches, or files.

## Selected Notion Page Sources

The current private-source connector models a selected Notion page.

Current policy:

- Only selected page URIs are accepted, such as `notion://page/{page_id}` or a Notion page URL.
- Workspace-wide access is not accepted.
- Tokens are not stored in source text.
- The source document records selected-page scope metadata.
- Disabling or archiving the source revokes it from retrieval, opportunity generation, brief building, and draft generation.
- Source creation, ingestion, refresh, and status changes are auditable in source detail.

## Human Approval Model

Drafts are reviewable artifacts, not published output.

Before approval, reviewers can inspect:

- opportunity rationale
- platform-independent brief
- source chunks
- claim support status
- risk and quality checks
- duplicate memory
- decision history

High-risk unsupported factual claims block clean approval until edited.

## Secrets

The current MVP does not require secrets. Future model providers should use environment variables and should never commit keys.

Use `.env.example` as the public template and keep `.env` untracked.

## Data Retention

The current in-memory store resets when the backend process restarts. Persistent database support is a later hardening step.

## Responsible Use

Quainy Vouch should help reviewers make safer communication decisions. It should not be used as a fully autonomous publisher or as a way to bypass source review.
