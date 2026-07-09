# LinkedIn API Research And Validation

Status: Sprint 7.1 research gate

Last checked: 2026-07-08

Official references:

- Share on LinkedIn: https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
- Posts API: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
- Organization access control by role: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/organization-access-control-by-role
- Organization share statistics: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/share-statistics

## Product Boundary

Quainy Vouch should not require LinkedIn API approval to be useful. The open-source MVP keeps manual export/copy as the default publishing path and provides a credential-free local publishing adapter for workflow validation. Live API publishing can be added only after app access, organization role checks, OAuth scopes, and failure handling are validated.

## Permission Checklist

- Create and configure a LinkedIn developer app.
- Confirm which LinkedIn product grants are available for organization publishing and analytics.
- Validate and request `w_organization_social` before attempting company-page publishing.
- Validate `w_member_social` only if member-profile publishing is ever added; it is not enough for the company-page MVP path.
- Validate and request `r_organization_social` before importing organization/page post analytics.
- Validate whether organization role lookup requires `r_organization_admin` or `rw_organization_admin` for the selected API path.
- Validate the connected member has the required organization/page administrator role before allowing a publish attempt.
- Store OAuth tokens outside source text and never in committed files.
- Treat missing permission, expired token, missing page role, and API rejection as expected operational states.

## OAuth App Setup Notes

- OAuth should be introduced behind a dedicated LinkedIn integration settings screen.
- The user should explicitly choose the organization/page to connect.
- The app should store only the minimum integration metadata needed for publishing and analytics.
- Revocation should disable publishing and analytics import without deleting approved drafts or post memory.
- Audit logs should record connect, refresh, revoke, publish attempt, publish success, publish failure, and analytics import events.

## Publishing Feasibility Decision

Decision: local adapter now, live provider later.

Rationale:

- The current product supports human-reviewed drafts, approval, scheduling intent, export/copy, local publish-result storage, and memory.
- LinkedIn company-page publishing depends on external app access and organization role validation.
- The product must never lose approved content if API publishing fails.

Implementation gate for Sprint 7.2:

- Only drafts with an approval memory record can be published.
- The selected draft must still pass current risk checks before publishing.
- The system must store publish request, response status, provider post ID when available, and failure reason.
- The reviewer must retain a manual export fallback.

## Analytics Feasibility Decision

Decision: feasible later with a manual metrics fallback.

Rationale:

- Organization share statistics appear to be the relevant path for company-page post performance.
- Analytics availability depends on permissions and page/admin access.
- Performance should become one learning signal, not a replacement for source truth, brand rules, or reviewer judgment.

Implementation gate for Sprint 7.3:

- Store performance snapshots separately from source-backed content memory.
- Support manual metrics entry when API analytics is unavailable.
- Keep engagement metrics out of claim grounding and approval truth checks.
- Audit analytics imports and manual metric edits.
