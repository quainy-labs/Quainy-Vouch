# Security Notes

Quainy Vouch is designed around controlled context, source visibility, and human approval. The current open-source MVP is local-first and intentionally avoids broad integrations.

## Current MVP Boundaries

- No live LinkedIn API publishing by default.
- No LinkedIn OAuth.
- No Slack, email, Drive, or broad workspace crawling.
- No live model calls by default.
- No hidden data collection.
- No training on user data.
- Runtime storage is in memory for the current local prototype.

LinkedIn publishing and analytics research is tracked in `docs/integrations/linkedin_api_research.md`. The current publishing adapter is local and credential-free; manual export remains the safe default until app permissions, OAuth, page roles, live provider calls, and production failure handling are implemented.

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

## Role Model

The local prototype includes workspace users with `owner`, `editor`, `reviewer`, and `viewer` roles. The default `local_user` is an owner. Owners can manage users, owners/editors can manage sources, and owners/reviewers can approve drafts. This is an application-level permission model, not production authentication.

## Approval Chains And Overrides

Organizations can require multiple distinct reviewers before a draft is approved, exported, or published. High-risk unsupported claims require an explicit override reason when overrides are enabled. Override events are written to the audit log and do not turn unsupported claims into source-backed claims.

## Analytics Boundary

Performance metrics can inform learning and prioritization, but they do not override source truth, brand rules, or reviewer approval. Manual metrics and imported analytics are stored as post-memory snapshots, not as approved company claims.

## Preference Learning Boundary

Reviewer edits and rejection reasons can generate profile suggestions. Suggestions are pending by default and require owner/editor approval before changing preferred phrases, banned phrases, or other durable profile memory. Dismissing a suggestion leaves profile memory unchanged.

## Trend And Calendar Boundary

Calendar events and trend signals are planning context, not approved claims by themselves. A trend can become a usable opportunity only when the relevance gate finds approved company source evidence. Trends without approved company context are retained as warnings with no source IDs, and the frontend does not allow creating briefs from those warned opportunities.

## Secrets

The current MVP does not require secrets. Future model providers should use environment variables and should never commit keys.

Use `.env.example` as the public template and keep `.env` untracked.

## Encryption Review

Current local mode stores runtime data in memory and does not persist source text or tokens to a database. Production storage should encrypt database volumes and backups at rest, use TLS in transit, and keep encryption keys outside the application database. Source text, generated drafts, post memory, integration metadata, and audit logs should be treated as sensitive workspace data.

## Connector Token Rotation

Current connectors avoid storing live connector tokens. Future OAuth/token connectors should support token revocation and rotation without deleting approved drafts or memory. Token rotation should log the actor, connector, previous token status, and new token status without writing token values to audit logs.

## Data Retention

The current in-memory store resets when the backend process restarts. Persistent database support is a later hardening step.

Organization owners can delete local workspace data through the organization delete endpoint. The API returns a deletion receipt with removed record counts. Persistent implementations should pair deletion receipts with backup-retention policy so users understand whether historical backups may contain deleted data until backup expiry.

See `docs/backup_restore.md` for backup, restore, and deletion expectations.

## Responsible Use

Quainy Vouch should help reviewers make safer communication decisions. It should not be used as a fully autonomous publisher or as a way to bypass source review.
