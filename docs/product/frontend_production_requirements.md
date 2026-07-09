# Frontend Production Requirements

Last updated: 2026-07-09

This document resets the frontend requirement for Quainy Vouch. The current UI is not production ready. It proves that backend modules can be called, but it does not yet feel like a trusted product that a company would use every day.

The frontend must stop behaving like a local demo console. The open-source product can run locally, but the experience must still feel production-grade, trustworthy, platform-aware, and valuable from the first screen.

## Product Experience Principle

The default experience must show what is ready, important, and safe to act on today.

Users should not land in edit forms. Editing company memory, sources, settings, and integrations should be available, but not be the primary first impression.

The first screen should answer:

- What content is ready for today?
- What needs review?
- What is scheduled?
- Which platforms are supported?
- Why is each suggestion relevant?
- What source evidence supports it?
- What risks should I review?
- What should I do next?

## Current Frontend Gap

The current frontend is not production ready because:

- The default view is still too edit-heavy.
- Generated posts, articles, newsletters, captions, and carousels are not the central product surface.
- Platform support is hidden inside a draft format selector instead of being a clear platform workspace.
- There is no "Today" content command center.
- There is no clear content pipeline: idea, brief, draft, review, approved, scheduled, exported, published.
- Review and trust signals are fragmented across panels.
- Source setup feels like a raw ingestion tool, not a guided knowledge base.
- Company profile editing appears too early and too prominently.
- Input controls and forms are still too dense for regular business users.
- Empty states do not sell the value of the product.
- The app still uses local/demo language in visible UX.
- There is no clear distinction between production capabilities, simulated adapters, and future live integrations.
- Multi-platform support exists technically in adapters, but the UI does not present it as a real product capability.
- There is no durable content library view where users can see all generated, approved, exported, or published work.

## Target Information Architecture

### 1. Today

Default landing view.

Purpose:

- Show ready-for-review content first.
- Show today's recommended opportunities.
- Show scheduled/upcoming content.
- Show blockers and trust warnings.

Required sections:

- Ready today
- Needs review
- Suggested opportunities
- Scheduled queue
- Source health
- Platform coverage summary

Primary actions:

- Generate today's recommendations
- Review draft
- Approve
- Schedule
- Export
- Add source only when source health is blocking generation

The user should not see company profile edit boxes here.

### 2. Content Studio

Purpose:

- Create and manage actual content artifacts.
- Make platform and format choices explicit.

Required sections:

- Platform selector:
  - LinkedIn company post
  - Blog outline / article
  - Newsletter email
  - Instagram caption
  - Instagram carousel outline
- Opportunity selector
- Brief preview
- Draft variants
- Platform-specific preview
- Review actions

Required behavior:

- User can see what platform each draft belongs to.
- User can generate drafts for a selected platform without hunting through a small dropdown.
- User can compare variants.
- User can move approved content into calendar/queue.

### 3. Content Library

Purpose:

- Show all content artifacts, not just transient generated state.

Required filters:

- Draft
- Needs review
- Approved
- Scheduled
- Exported
- Published
- Rejected
- Platform
- Content type
- Source-backed / warned

Required columns/cards:

- Title or hook
- Platform
- Content type
- Status
- Source count
- Risk status
- Last updated
- Scheduled/published date

### 4. Calendar

Purpose:

- Show when approved content is planned.
- Separate company/public events from content scheduling.

Required sections:

- Upcoming scheduled content
- Company events
- Public holidays/events
- Recommended moments to create content

### 5. Sources

Purpose:

- Manage approved company knowledge.
- Explain whether enough safe context exists.

Required sections:

- Source health summary
- Approved sources
- Disabled/archived sources
- Add source flow
- Source detail
- Retrieval test only as an advanced/debug tool

Source creation should be guided:

- Add a document
- Paste approved text
- Add a URL
- Add release notes
- Add selected Notion page

The user should not start with connector metadata fields.

### 6. Strategy

Purpose:

- Help users understand what is working and what to do next.

Required sections:

- Content pillar coverage
- Topic repetition map
- Performance by content type
- Platform performance
- Suggested next direction
- Explainability for recommendations

### 7. Settings

Purpose:

- Configure company memory, users, roles, approval policy, and integrations.

Required sections:

- Company profile
- Voice and claims
- Users and roles
- Approval policy
- Platform integrations
- Export/publishing settings

Settings should never be the default landing experience.

## Visual Design Requirements

The UI should feel modern, calm, and trustworthy. Use a refined glassmorphism direction without making readability worse.

Required style direction:

- Glass-like navigation and summary surfaces.
- Soft translucent panels over a restrained background.
- Strong content hierarchy.
- Cards for content artifacts only.
- Minimal decorative effects.
- Clear active states.
- Professional form controls.
- No raw browser-looking dropdowns or date inputs.
- No walls of visible edit fields.
- Forms should appear in drawers, modals, side panels, or focused editor sections.

Control requirements:

- Inputs must have consistent height, border, radius, focus ring, hover state, and disabled state.
- Selects must have custom visual treatment and clear selected value.
- Date/time inputs must be wrapped or styled so they do not look broken across browsers.
- Textareas must be sized for purpose, not all giant by default.
- Labels must be human-readable, not schema-like.
- Advanced fields must be collapsed by default.
- Form sections must have clear save/cancel actions.

## Functional Frontend Requirements

### Today View

The product is not ready until the default view can show:

- At least one generated content recommendation when approved sources exist.
- Empty-state guidance when no source context exists.
- Drafts needing review.
- Approved content ready to export or schedule.
- Upcoming scheduled content.
- Source health and blockers.

### Platform Clarity

The product is not ready until users can clearly see:

- Which platforms are supported.
- Which content types each platform supports.
- Whether publishing is live, simulated, export-only, or not connected.
- Which platform a draft was generated for.
- Which platform-specific checks were applied.

### Content Artifact Persistence

The product is not ready until generated artifacts are easy to find again.

The UI must include a persistent content library that shows:

- Opportunities
- Briefs
- Draft variants
- Approved content
- Exported/published content
- Rejected content

### Trust Surface

Every draft review view must show:

- Source evidence
- Claim support
- Risk warnings
- Duplicate warnings
- Freshness warnings
- Generation metadata
- Platform adapter used
- Why it matters today

This should be visible without forcing users to inspect technical panels.

### Empty States

Every empty state must explain:

- What is missing.
- Why it matters.
- The best next action.

Bad empty state:

- "No results."

Good empty state:

- "No review-ready content yet. Add an approved source or generate today's recommendations."

## Backend And Product Gaps Exposed By Frontend

The frontend cannot become production-grade without addressing these product gaps:

- Persistent database storage is needed; in-memory state makes the product feel temporary.
- Background job status is needed for ingestion and generation.
- Draft/content artifact listing endpoints need to support content library views.
- Opportunity, brief, and draft lifecycle status needs a clearer product model.
- Platform capability metadata endpoint is needed.
- Publishing state must distinguish export-only, simulated publish, and live integration.
- Source health endpoint is needed.
- Today/recommendations endpoint is needed.
- Audit events should be shown as trust history, not raw logs.
- Multi-platform generation should be explicit in the API and UI, not hidden behind query strings.

## Revised Frontend Build Phases

### Frontend Phase A: Product Shell Reset

Status: Implemented

Goal:

- Replace demo-console layout with production information architecture.

Deliverables:

- Today default view.
- Glass-style navigation.
- Content-first dashboard.
- Settings moved out of the landing experience.
- Source and profile edit forms moved into focused editors.

Acceptance:

- User lands on content readiness, not edit boxes.
- User can understand what to do next within 10 seconds.

Evidence:

- Default navigation now opens Today.
- Settings/profile editing is no longer the first screen.
- Browser smoke check confirmed Today, seven top-level views, source health, platform summary, and no desktop/mobile horizontal overflow.

### Frontend Phase B: Content Studio

Status: Implemented

Goal:

- Make content generation and review feel like the core product.

Deliverables:

- Platform cards.
- Format-specific generation flow.
- Draft variant comparison.
- Platform preview.
- Review and approval actions.

Acceptance:

- User can generate LinkedIn, blog/newsletter, or Instagram variants from a clear platform workflow.
- User can see exactly what was generated and why.

Evidence:

- Studio shows platform cards for LinkedIn, Blog, Newsletter, Instagram caption, and Instagram carousel.
- Browser smoke check confirmed opportunity-to-brief routing into Studio and draft generation with three variants.
- Studio now shows a read-first platform preview with draft chrome, artifact body, evidence count, claim support, risk count, duplicate-memory count, adapter metadata, why-today context, and source evidence preview before the edit/review controls.

### Frontend Phase C: Content Library And Calendar

Status: Implemented

Goal:

- Make generated content durable and findable.

Deliverables:

- Content library.
- Status filters.
- Platform filters.
- Calendar view.
- Queue management.

Acceptance:

- User can find previously generated, approved, scheduled, exported, rejected, or published content.

Evidence:

- API exposes durable content artifacts across opportunities, briefs, drafts, and published memory through `GET /organizations/{organization_id}/content-artifacts`.
- Content Library now uses the durable artifact endpoint with lifecycle filters, platform filtering, artifact status, source/risk counts, updated timestamps, and Studio routing for draft artifacts.
- Calendar now includes a dated two-week board that combines scheduled/exported/published content with company and public calendar events, plus the existing queue management list.

### Frontend Phase D: Trust And Source UX

Status: Implemented

Goal:

- Make the system feel safe for companies.

Deliverables:

- Source health dashboard.
- Guided source onboarding.
- Evidence side panel.
- Claim/risk explanation UI.
- Trust history timeline.

Acceptance:

- User can see why the system trusts or refuses a recommendation.

Evidence:

- Today now includes source health with approved, disabled, and archived source counts.
- Sources now includes a source health dashboard and guided onboarding choices for company documents, pasted approved text, public URLs, release notes, and Notion pages.
- Studio now includes a trust-history timeline showing source basis, opportunity relevance, brief grounding, draft adapter, review checks, reviewer action, and recorded decisions outside the technical review rail.
- Review desk already exposes risk, quality, claims, evidence, source chunks, duplicate memory, and approval decision history.

### Frontend Phase E: Strategy Dashboard

Status: Implemented

Goal:

- Help companies understand content performance and next direction.

Deliverables:

- Content pillar coverage.
- Topic repetition map.
- Performance by platform/content type.
- Suggested next content direction.

Acceptance:

- Recommendations remain explainable and source-aware.

Evidence:

- API exposes `GET /organizations/{organization_id}/strategy` with pillar coverage, topic repetition, performance by platform, performance by content type, and suggested directions.
- Strategy view now surfaces suggested next directions with confidence and source basis, content pillar coverage, topic repetition, and platform/content-type performance before raw analytics controls.

## Quality Gate

No frontend phase should be marked complete unless:

- The primary workflow is visible without reading documentation.
- The default view is not an edit form.
- Platform support is clear.
- Generated artifacts are visible and findable.
- Trust evidence is visible.
- Empty states are useful.
- Forms are progressive and not overwhelming.
- The UI has been checked in desktop and mobile viewports.
- `npm run build` passes.
- Backend contract tests pass when relevant.
