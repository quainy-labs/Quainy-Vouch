# Backup And Restore Guide

Status: local-first MVP guidance

Quainy Vouch currently uses an in-memory runtime store. Data resets when the backend process restarts. This guide documents the production expectations before persistent storage is introduced.

## Current Local Mode

- Source text, chunks, drafts, memory, users, policies, analytics snapshots, and audit logs live in process memory.
- `.env` is intentionally untracked.
- No connector tokens are stored in source text.
- Deleting an organization removes its local in-memory workspace data and returns a deletion receipt.

## Production Backup Expectations

- Back up the application database on a fixed schedule.
- Encrypt database backups at rest.
- Store backup encryption keys outside the application database.
- Keep backup access limited to owner/admin operators.
- Include organizations, users, profiles, sources, source documents, chunks, briefs, drafts, decisions, memory, integrations, analytics snapshots, and audit logs.
- Test restore procedures before relying on backups for recovery.

## Restore Expectations

- Restore into an isolated environment first.
- Confirm organization boundaries before exposing restored data to users.
- Rotate connector tokens after restore if there is any suspicion that backup access was broader than intended.
- Rebuild embeddings if the embedding provider or vector schema changed.
- Re-run the regression test and eval harness after restore.

## Deletion Expectations

- Organization deletion must be owner/admin initiated.
- A deletion receipt should record who deleted the workspace, when it happened, and counts of removed records.
- Persistent implementations should keep only the minimum deletion audit required by policy and law.
- Deleted source text and generated drafts should not remain available to retrieval, generation, analytics, or memory.
