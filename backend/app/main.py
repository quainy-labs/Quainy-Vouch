from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    ApprovalPolicy,
    ApprovalPolicyUpdate,
    AnalyticsDashboard,
    CalendarEvent,
    CalendarEventCreate,
    CompanyProfile,
    CompanyProfileUpdate,
    ContentArtifact,
    ContentBrief,
    DeletionReceipt,
    Draft,
    DraftCreateResult,
    DraftPublishCreate,
    DraftScheduleCreate,
    DraftUpdate,
    LinkedInIntegration,
    LinkedInIntegrationUpdate,
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
    PerformanceMetricsCreate,
    PostMemory,
    PreferenceSuggestion,
    PreferenceSuggestionDecision,
    PublishResult,
    ReviewDecisionCreate,
    ReviewerPackage,
    RetrievalQuery,
    RetrievalResult,
    Source,
    SourceCreate,
    SourceDetail,
    SourceUpdate,
    StrategyDashboard,
    TrendSignal,
    TrendSignalCreate,
    User,
    UserCreate,
    UserUpdate,
)
from app.risk_checks import high_risk_unsupported_claims
from app.store import ApprovalBlockedError, DataStore, NotFoundError, PermissionDeniedError, ReviewDecisionRequiredError


ROOT = Path(__file__).resolve().parents[2]
store = DataStore()
SEEDED_ORG_ID = store.seed_quainy(ROOT)

app = FastAPI(title="Quainy Vouch API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def not_found(error: NotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))


def approval_blocked(error: ApprovalBlockedError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(error))


def bad_review_decision(error: ReviewDecisionRequiredError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


def permission_denied(error: PermissionDeniedError) -> HTTPException:
    return HTTPException(status_code=403, detail=str(error))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "seeded_organization_id": SEEDED_ORG_ID}


@app.get("/bootstrap")
def bootstrap() -> dict[str, object]:
    org = store.get_organization(SEEDED_ORG_ID)
    return {
        "organization": org,
        "profile": store.profiles[org.id],
        "sources": store.list_sources(org.id),
        "opportunities": store.list_opportunities(org.id),
        "memory": store.list_memory(org.id),
    }


@app.post("/organizations", response_model=Organization)
def create_organization(payload: OrganizationCreate) -> Organization:
    return store.create_organization(payload)


@app.get("/organizations", response_model=list[Organization])
def list_organizations() -> list[Organization]:
    return store.list_organizations()


@app.get("/organizations/{organization_id}", response_model=Organization)
def get_organization(organization_id: str) -> Organization:
    try:
        return store.get_organization(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}", response_model=Organization)
def update_organization(organization_id: str, payload: OrganizationUpdate) -> Organization:
    try:
        return store.update_organization(organization_id, payload)
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/users", response_model=list[User])
def list_users(organization_id: str) -> list[User]:
    try:
        return store.list_users(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/users", response_model=User)
def create_user(organization_id: str, payload: UserCreate, actor_id: str = "local_user") -> User:
    try:
        return store.create_user(organization_id, payload, actor_id)
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/users/{user_id}", response_model=User)
def update_user(organization_id: str, user_id: str, payload: UserUpdate, actor_id: str = "local_user") -> User:
    try:
        return store.update_user(organization_id, user_id, payload, actor_id)
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/approval-policy", response_model=ApprovalPolicy)
def get_approval_policy(organization_id: str) -> ApprovalPolicy:
    try:
        return store.get_approval_policy(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/approval-policy", response_model=ApprovalPolicy)
def update_approval_policy(
    organization_id: str,
    payload: ApprovalPolicyUpdate,
    actor_id: str = "local_user",
) -> ApprovalPolicy:
    try:
        return store.update_approval_policy(organization_id, payload, actor_id)
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.delete("/organizations/{organization_id}", response_model=DeletionReceipt)
def delete_organization(organization_id: str, actor_id: str = "local_user") -> DeletionReceipt:
    try:
        return store.delete_organization(organization_id, actor_id)
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/profile", response_model=CompanyProfile)
def get_profile(organization_id: str) -> CompanyProfile:
    try:
        store.get_organization(organization_id)
        return store.profiles[organization_id]
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/profile", response_model=CompanyProfile)
def update_profile(organization_id: str, payload: CompanyProfileUpdate) -> CompanyProfile:
    try:
        return store.update_profile(organization_id, payload)
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/linkedin-integration", response_model=LinkedInIntegration)
def get_linkedin_integration(organization_id: str) -> LinkedInIntegration:
    try:
        return store.get_linkedin_integration(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/linkedin-integration", response_model=LinkedInIntegration)
def update_linkedin_integration(organization_id: str, payload: LinkedInIntegrationUpdate) -> LinkedInIntegration:
    try:
        return store.update_linkedin_integration(organization_id, payload)
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/sources", response_model=Source)
def create_source(organization_id: str, payload: SourceCreate, actor_id: str = "local_user") -> Source:
    try:
        source = store.create_source(organization_id, payload, actor_id)
        store.ingest_source(source.id, actor_id)
        return source
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/sources", response_model=list[Source])
def list_sources(organization_id: str) -> list[Source]:
    try:
        return store.list_sources(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/sources/{source_id}", response_model=SourceDetail)
def get_source(source_id: str) -> SourceDetail:
    try:
        return store.get_source_detail(source_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/sources/{source_id}", response_model=Source)
def update_source(source_id: str, payload: SourceUpdate, actor_id: str = "local_user") -> Source:
    try:
        return store.update_source(source_id, payload, actor_id)
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/sources/{source_id}/ingest")
def ingest_source(source_id: str, actor_id: str = "local_user") -> dict[str, object]:
    try:
        chunks = store.ingest_source(source_id, actor_id)
        return {"source_id": source_id, "chunk_count": len(chunks), "chunks": chunks}
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/sources/{source_id}/refresh")
def refresh_source(source_id: str, actor_id: str = "local_user") -> dict[str, object]:
    try:
        chunks = store.ingest_source(source_id, actor_id)
        return {"chunks": chunks, "message": "Source refreshed from the selected page snapshot."}
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/retrieval/query", response_model=list[RetrievalResult])
def retrieve_source_chunks(organization_id: str, payload: RetrievalQuery) -> list[RetrievalResult]:
    try:
        return [
            RetrievalResult(chunk=chunk, source=source, score=score)
            for chunk, source, score in store.retrieve_chunks(organization_id, payload.query, payload.limit)
        ]
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/opportunities/generate")
def generate_opportunities(organization_id: str) -> dict[str, object]:
    try:
        opportunities = store.generate_opportunities(organization_id)
        if not opportunities:
            return {"opportunities": [], "message": "No strong opportunity found from approved context."}
        return {"opportunities": opportunities}
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/opportunities")
def list_opportunities(organization_id: str) -> list[object]:
    return store.list_opportunities(organization_id)


@app.get("/organizations/{organization_id}/calendar-events", response_model=list[CalendarEvent])
def list_calendar_events(organization_id: str) -> list[CalendarEvent]:
    try:
        return store.list_calendar_events(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/calendar-events", response_model=CalendarEvent)
def create_calendar_event(
    organization_id: str,
    payload: CalendarEventCreate,
    actor_id: str = "local_user",
) -> CalendarEvent:
    try:
        return store.create_calendar_event(organization_id, payload, actor_id)
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/trend-signals", response_model=list[TrendSignal])
def list_trend_signals(organization_id: str) -> list[TrendSignal]:
    try:
        return store.list_trend_signals(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/trend-signals", response_model=TrendSignal)
def create_trend_signal(
    organization_id: str,
    payload: TrendSignalCreate,
    actor_id: str = "local_user",
) -> TrendSignal:
    try:
        return store.create_trend_signal(organization_id, payload, actor_id)
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/trend-opportunities/generate")
def generate_trend_opportunities(organization_id: str) -> dict[str, object]:
    try:
        opportunities = store.generate_trend_opportunities(organization_id)
        return {"opportunities": opportunities}
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/opportunities/{opportunity_id}/briefs", response_model=ContentBrief)
def create_brief(opportunity_id: str) -> ContentBrief:
    try:
        return store.create_brief(opportunity_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/briefs/{brief_id}", response_model=ContentBrief)
def get_brief(brief_id: str) -> ContentBrief:
    try:
        return store.get_brief(brief_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/briefs/{brief_id}/drafts", response_model=DraftCreateResult)
def generate_drafts(brief_id: str, platform: str = "linkedin", content_type: str = "company_post") -> DraftCreateResult:
    try:
        return DraftCreateResult(drafts=store.generate_drafts(brief_id, platform, content_type))
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/drafts/{draft_id}", response_model=Draft)
def get_draft(draft_id: str) -> Draft:
    try:
        return store.get_draft(draft_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/drafts/{draft_id}", response_model=Draft)
def update_draft(draft_id: str, payload: DraftUpdate) -> Draft:
    try:
        return store.update_draft_body(draft_id, payload.body)
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/drafts/{draft_id}/reviewer-package", response_model=ReviewerPackage)
def reviewer_package(draft_id: str) -> ReviewerPackage:
    try:
        draft = store.get_draft(draft_id)
        brief = store.get_brief(draft.content_brief_id)
        opportunity = store.get_opportunity(brief.opportunity_id)
        sources = [store.get_source(source_id) for source_id in brief.source_ids]
        source_chunks = [chunk for chunk in store.approved_chunks(draft.organization_id) if chunk.source_id in brief.source_ids]
        unsupported = high_risk_unsupported_claims(draft.claims)
        approval_progress = store.approval_progress(draft.id)
        draft.approval_metadata = approval_progress
        if unsupported:
            suggested_action = "Review unsupported claims before approval."
        elif approval_progress["remaining_reviewer_count"]:
            suggested_action = f"Needs {approval_progress['remaining_reviewer_count']} more approval(s)."
        else:
            suggested_action = "Ready for human approval."
        return ReviewerPackage(
            draft=draft,
            brief=brief,
            opportunity=opportunity,
            sources=sources,
            source_chunks=source_chunks,
            decision_history=store.list_draft_decisions(draft.id),
            suggested_action=suggested_action,
        )
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/regenerate", response_model=DraftCreateResult)
def regenerate_draft(draft_id: str) -> DraftCreateResult:
    try:
        return DraftCreateResult(drafts=store.regenerate_drafts_for_draft(draft_id))
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/approve")
def approve_draft(draft_id: str, payload: ReviewDecisionCreate, actor_id: str = "local_user") -> object:
    try:
        return store.approve_draft(draft_id, payload, actor_id)
    except ApprovalBlockedError as error:
        raise approval_blocked(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/reject")
def reject_draft(draft_id: str, payload: ReviewDecisionCreate) -> object:
    try:
        return store.reject_draft(draft_id, payload)
    except ReviewDecisionRequiredError as error:
        raise bad_review_decision(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/export")
def export_draft(draft_id: str) -> object:
    try:
        return store.export_draft(draft_id)
    except ApprovalBlockedError as error:
        raise approval_blocked(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/schedule")
def schedule_draft(draft_id: str, payload: DraftScheduleCreate) -> object:
    try:
        return store.schedule_draft(draft_id, payload.scheduled_for, payload.reason)
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/publish/linkedin", response_model=PublishResult)
def publish_draft_to_linkedin(draft_id: str, payload: DraftPublishCreate) -> PublishResult:
    try:
        return store.publish_draft_to_linkedin(draft_id, payload)
    except ApprovalBlockedError as error:
        raise approval_blocked(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/memory")
def memory(organization_id: str) -> list[object]:
    return store.list_memory(organization_id)


@app.get("/organizations/{organization_id}/preference-suggestions", response_model=list[PreferenceSuggestion])
def list_preference_suggestions(organization_id: str) -> list[PreferenceSuggestion]:
    try:
        return store.list_preference_suggestions(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/preference-suggestions/generate", response_model=list[PreferenceSuggestion])
def generate_preference_suggestions(organization_id: str) -> list[PreferenceSuggestion]:
    try:
        return store.generate_preference_suggestions(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/preference-suggestions/{suggestion_id}/approve", response_model=PreferenceSuggestion)
def approve_preference_suggestion(
    suggestion_id: str,
    payload: PreferenceSuggestionDecision,
    actor_id: str = "local_user",
) -> PreferenceSuggestion:
    try:
        return store.approve_preference_suggestion(suggestion_id, payload, actor_id)
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/preference-suggestions/{suggestion_id}/dismiss", response_model=PreferenceSuggestion)
def dismiss_preference_suggestion(
    suggestion_id: str,
    payload: PreferenceSuggestionDecision,
    actor_id: str = "local_user",
) -> PreferenceSuggestion:
    try:
        return store.dismiss_preference_suggestion(suggestion_id, payload, actor_id)
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/memory/{memory_id}/performance", response_model=PostMemory)
def record_memory_performance(memory_id: str, payload: PerformanceMetricsCreate) -> PostMemory:
    try:
        return store.record_performance_metrics(memory_id, payload)
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/analytics/import", response_model=list[PostMemory])
def import_linkedin_analytics(organization_id: str) -> list[PostMemory]:
    try:
        return store.import_linkedin_analytics(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/analytics", response_model=AnalyticsDashboard)
def analytics_dashboard(organization_id: str) -> AnalyticsDashboard:
    try:
        return store.analytics_dashboard(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/strategy", response_model=StrategyDashboard)
def strategy_dashboard(organization_id: str) -> StrategyDashboard:
    try:
        return store.strategy_dashboard(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/content-artifacts", response_model=list[ContentArtifact])
def content_artifacts(organization_id: str) -> list[ContentArtifact]:
    try:
        return store.list_content_artifacts(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/calendar", response_model=list[Draft])
def calendar(organization_id: str) -> list[Draft]:
    try:
        return store.list_calendar(organization_id)
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/audit-logs")
def audit_logs(organization_id: str) -> list[object]:
    return store.list_audit_logs(organization_id)
