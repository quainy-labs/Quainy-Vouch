from __future__ import annotations

from pathlib import Path

import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    AIProviderConnectionTest,
    AIProviderSettings,
    AIProviderSettingsUpdate,
    ApprovalPolicy,
    ApprovalPolicyUpdate,
    AccountLogin,
    AnalyticsDashboard,
    BackgroundJob,
    BackgroundJobLog,
    CalendarEvent,
    CalendarEventCreate,
    CompanyProfile,
    CompanyProfileUpdate,
    ContentArtifact,
    ContentBrief,
    CurrentWorkspace,
    DeletionReceipt,
    Draft,
    DraftCreateResult,
    DraftPublishCreate,
    DraftScheduleCreate,
    DraftStatus,
    DraftUpdate,
    JobKind,
    KnowledgeReadiness,
    LinkedInIntegration,
    LinkedInIntegrationUpdate,
    ModelCallLog,
    OnboardingDecision,
    OnboardingState,
    OnboardingStep,
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
    SignupCreate,
    Source,
    SourceCreate,
    SourceDetail,
    SourceUpdate,
    StrategyDashboard,
    TrendSignal,
    TrendSignalCreate,
    User,
    UserCreate,
    UserRole,
    UserUpdate,
)
from app.risk_checks import high_risk_unsupported_claims
from app.store import (
    ApprovalBlockedError,
    AuthenticationError,
    DataStore,
    NotFoundError,
    PermissionDeniedError,
    ReviewDecisionRequiredError,
)


ROOT = Path(__file__).resolve().parents[2]


def build_store() -> DataStore:
    data_backend = os.getenv("QUAINY_DATA_BACKEND", "memory").strip().lower()
    if data_backend == "postgres":
        from app.postgres_store import PostgresDataStore

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when QUAINY_DATA_BACKEND=postgres.")
        return PostgresDataStore(database_url, ROOT / "docs" / "architecture" / "database_schema.sql")
    return DataStore()


store = build_store()


def enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def fixture_mode() -> str:
    environment = os.getenv("QUAINY_ENV", "development").strip().lower()
    data_backend = os.getenv("QUAINY_DATA_BACKEND", "memory").strip().lower()
    explicit_mode = os.getenv("QUAINY_FIXTURE_MODE")
    explicit_seed = os.getenv("QUAINY_ENABLE_DEV_SEED")

    if environment == "production":
        if enabled(explicit_seed) or (explicit_mode and explicit_mode.strip().lower() != "none"):
            raise RuntimeError("Deterministic fixtures cannot be enabled when QUAINY_ENV=production.")
        return "none"
    if explicit_mode:
        return explicit_mode.strip().lower()
    if explicit_seed is not None:
        return "sample" if enabled(explicit_seed) else "none"
    return "sample" if data_backend == "memory" else "none"


FIXTURE_MODE = fixture_mode()
SEEDED_ORG_ID = store.seed_quainy(ROOT) if FIXTURE_MODE == "sample" else None

app = FastAPI(title="Quainy Vouch API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
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


def authentication_failed(error: AuthenticationError) -> HTTPException:
    return HTTPException(status_code=401, detail=str(error))


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise AuthenticationError("Authorization header must use Bearer token.")
    return authorization[len(prefix) :].strip()


def allow_fixture_fallback() -> bool:
    return FIXTURE_MODE == "sample"


def actor_from_auth(
    organization_id: str,
    authorization: str | None,
    fallback_actor_id: str | None = None,
) -> str:
    token = bearer_token(authorization)
    if token:
        return store.actor_id_for_token(token, organization_id)
    if allow_fixture_fallback():
        return fallback_actor_id or "local_user"
    raise AuthenticationError("Authentication required.")


def actor_from_optional_auth(organization_id: str, authorization: str | None) -> str | None:
    token = bearer_token(authorization)
    if token:
        return store.actor_id_for_token(token, organization_id)
    if allow_fixture_fallback():
        return None
    raise AuthenticationError("Authentication required.")


def require_org_role(
    organization_id: str,
    authorization: str | None,
    allowed_roles: set[UserRole],
    fallback_actor_id: str | None = None,
) -> str:
    actor_id = actor_from_auth(organization_id, authorization, fallback_actor_id)
    store.require_role(organization_id, actor_id, allowed_roles)
    return actor_id


def summarize_list_result(items: list[object], id_attr: str = "id") -> dict[str, object]:
    return {
        "count": len(items),
        "ids": [getattr(item, id_attr) for item in items if getattr(item, id_attr, None)],
    }


def summarize_one_result(item: object, id_attr: str = "id") -> dict[str, object]:
    item_id = getattr(item, id_attr, None)
    return {"id": item_id} if item_id else {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "seeded_organization_id": SEEDED_ORG_ID or ""}


@app.get("/bootstrap")
def bootstrap() -> dict[str, object]:
    if not SEEDED_ORG_ID:
        raise HTTPException(status_code=404, detail="Development bootstrap workspace is disabled.")
    org = store.get_organization(SEEDED_ORG_ID)
    return {
        "organization": org,
        "profile": store.profiles[org.id],
        "sources": store.list_sources(org.id),
        "opportunities": store.list_opportunities(org.id),
        "memory": store.list_memory(org.id),
    }


@app.post("/auth/signup")
def signup(payload: SignupCreate) -> dict[str, object]:
    try:
        token, workspace = store.signup(payload)
        return {"token": token, "workspace": workspace}
    except PermissionDeniedError as error:
        raise permission_denied(error) from error


@app.post("/auth/login")
def login(payload: AccountLogin) -> dict[str, object]:
    try:
        token, workspace = store.login(payload)
        return {"token": token, "workspace": workspace}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/me", response_model=CurrentWorkspace)
def current_workspace(authorization: str | None = Header(default=None)) -> CurrentWorkspace:
    try:
        token = bearer_token(authorization)
        if not token:
            raise AuthenticationError("Authentication required.")
        return store.current_workspace(token)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/onboarding/profile", response_model=OnboardingState)
def decide_onboarding_profile(
    organization_id: str,
    payload: OnboardingDecision,
    authorization: str | None = Header(default=None),
) -> OnboardingState:
    try:
        actor_id = actor_from_auth(organization_id, authorization, None)
        return store.decide_onboarding_profile(organization_id, actor_id, payload)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations", response_model=Organization)
def create_organization(payload: OrganizationCreate) -> Organization:
    return store.create_organization(payload)


@app.get("/organizations", response_model=list[Organization])
def list_organizations(authorization: str | None = Header(default=None)) -> list[Organization]:
    try:
        token = bearer_token(authorization)
        if token:
            return [store.current_workspace(token).organization]
        if allow_fixture_fallback():
            return store.list_organizations()
        raise AuthenticationError("Authentication required.")
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}", response_model=Organization)
def get_organization(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> Organization:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.get_organization(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}", response_model=Organization)
def update_organization(
    organization_id: str,
    payload: OrganizationUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> Organization:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.update_organization(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/users", response_model=list[User])
def list_users(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[User]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_users(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/users", response_model=User)
def create_user(
    organization_id: str,
    payload: UserCreate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> User:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.create_user(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/users/{user_id}", response_model=User)
def update_user(
    organization_id: str,
    user_id: str,
    payload: UserUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> User:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.update_user(organization_id, user_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/approval-policy", response_model=ApprovalPolicy)
def get_approval_policy(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> ApprovalPolicy:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.get_approval_policy(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/approval-policy", response_model=ApprovalPolicy)
def update_approval_policy(
    organization_id: str,
    payload: ApprovalPolicyUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> ApprovalPolicy:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.update_approval_policy(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/ai-provider-settings", response_model=AIProviderSettings)
def get_ai_provider_settings(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> AIProviderSettings:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.get_ai_provider_settings(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/ai-provider-settings", response_model=AIProviderSettings)
def update_ai_provider_settings(
    organization_id: str,
    payload: AIProviderSettingsUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> AIProviderSettings:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.update_ai_provider_settings(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/ai-provider-settings/test", response_model=AIProviderConnectionTest)
def test_ai_provider_settings(
    organization_id: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> AIProviderConnectionTest:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.test_ai_provider_settings(organization_id, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.delete("/organizations/{organization_id}", response_model=DeletionReceipt)
def delete_organization(
    organization_id: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> DeletionReceipt:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.delete_organization(organization_id, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/profile", response_model=CompanyProfile)
def get_profile(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> CompanyProfile:
    try:
        actor_from_optional_auth(organization_id, authorization)
        store.get_organization(organization_id)
        return store.profiles[organization_id]
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/profile", response_model=CompanyProfile)
def update_profile(
    organization_id: str,
    payload: CompanyProfileUpdate,
    authorization: str | None = Header(default=None),
) -> CompanyProfile:
    try:
        actor = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        profile = store.update_profile(organization_id, payload, actor)
        if bearer_token(authorization):
            store.mark_onboarding_step(organization_id, actor, OnboardingStep.profile_started, profile_skipped=False)
        return profile
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/linkedin-integration", response_model=LinkedInIntegration)
def get_linkedin_integration(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> LinkedInIntegration:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.get_linkedin_integration(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/linkedin-integration", response_model=LinkedInIntegration)
def update_linkedin_integration(
    organization_id: str,
    payload: LinkedInIntegrationUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> LinkedInIntegration:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.update_linkedin_integration(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/sources", response_model=Source)
def create_source(
    organization_id: str,
    payload: SourceCreate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> Source:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        source = store.create_source(organization_id, payload, actor_id)
        store.run_job(
            organization_id,
            actor_id,
            JobKind.source_ingest,
            "source",
            source.id,
            {"source_id": source.id, "source_type": source.source_type},
            lambda: store.ingest_source(source.id, actor_id),
            lambda chunks: {"chunk_count": len(chunks)},
        )
        if authorization:
            store.mark_onboarding_step(organization_id, actor_id, OnboardingStep.source_added)
        return source
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/sources", response_model=list[Source])
def list_sources(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[Source]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_sources(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/knowledge-readiness", response_model=KnowledgeReadiness)
def knowledge_readiness(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> KnowledgeReadiness:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.knowledge_readiness(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/sources/{source_id}", response_model=SourceDetail)
def get_source(
    source_id: str,
    authorization: str | None = Header(default=None),
) -> SourceDetail:
    try:
        source = store.get_source(source_id)
        actor_from_optional_auth(source.organization_id, authorization)
        return store.get_source_detail(source_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/sources/{source_id}", response_model=Source)
def update_source(
    source_id: str,
    payload: SourceUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> Source:
    try:
        source = store.get_source(source_id)
        actor_id = require_org_role(source.organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.update_source(source_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/sources/{source_id}/ingest")
def ingest_source(
    source_id: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    try:
        source = store.get_source(source_id)
        actor_id = require_org_role(source.organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        _job, chunks = store.run_job(
            source.organization_id,
            actor_id,
            JobKind.source_ingest,
            "source",
            source_id,
            {"source_id": source_id},
            lambda: store.ingest_source(source_id, actor_id),
            lambda result: {"chunk_count": len(result)},
        )
        return {"source_id": source_id, "chunk_count": len(chunks), "chunks": chunks}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/sources/{source_id}/refresh")
def refresh_source(
    source_id: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    try:
        source = store.get_source(source_id)
        actor_id = require_org_role(source.organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        _job, chunks = store.run_job(
            source.organization_id,
            actor_id,
            JobKind.source_refresh,
            "source",
            source_id,
            {"source_id": source_id},
            lambda: store.ingest_source(source_id, actor_id),
            lambda result: {"chunk_count": len(result)},
        )
        return {"chunks": chunks, "message": "Source refreshed from the selected page snapshot."}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/retrieval/query", response_model=list[RetrievalResult])
def retrieve_source_chunks(
    organization_id: str,
    payload: RetrievalQuery,
    authorization: str | None = Header(default=None),
) -> list[RetrievalResult]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return [
            RetrievalResult(chunk=chunk, source=source, score=score)
            for chunk, source, score in store.retrieve_chunks(organization_id, payload.query, payload.limit)
        ]
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/opportunities/generate")
def generate_opportunities(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, opportunities = store.run_job(
            organization_id,
            actor_id,
            JobKind.opportunity_generation,
            "organization",
            organization_id,
            {"organization_id": organization_id},
            lambda: store.generate_opportunities(organization_id, actor_id),
            summarize_list_result,
        )
        if actor_id:
            store.mark_onboarding_step(organization_id, actor_id, OnboardingStep.first_opportunity_generated)
        if not opportunities:
            return {"opportunities": [], "message": "No strong opportunity found from approved context."}
        return {"opportunities": opportunities}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/opportunities")
def list_opportunities(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[object]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_opportunities(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/calendar-events", response_model=list[CalendarEvent])
def list_calendar_events(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[CalendarEvent]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_calendar_events(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/calendar-events", response_model=CalendarEvent)
def create_calendar_event(
    organization_id: str,
    payload: CalendarEventCreate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> CalendarEvent:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.create_calendar_event(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/trend-signals", response_model=list[TrendSignal])
def list_trend_signals(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[TrendSignal]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_trend_signals(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/trend-signals", response_model=TrendSignal)
def create_trend_signal(
    organization_id: str,
    payload: TrendSignalCreate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> TrendSignal:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.create_trend_signal(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/trend-opportunities/generate")
def generate_trend_opportunities(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, opportunities = store.run_job(
            organization_id,
            actor_id,
            JobKind.trend_opportunity_generation,
            "organization",
            organization_id,
            {"organization_id": organization_id},
            lambda: store.generate_trend_opportunities(organization_id, actor_id),
            summarize_list_result,
        )
        return {"opportunities": opportunities}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/opportunities/{opportunity_id}/briefs", response_model=ContentBrief)
def create_brief(
    opportunity_id: str,
    authorization: str | None = Header(default=None),
) -> ContentBrief:
    try:
        opportunity = store.get_opportunity(opportunity_id)
        actor_id = require_org_role(opportunity.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        brief = store.create_brief(opportunity_id, actor_id)
        if actor_id:
            store.mark_onboarding_step(brief.organization_id, actor_id, OnboardingStep.first_brief_created)
        return brief
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/briefs/{brief_id}", response_model=ContentBrief)
def get_brief(
    brief_id: str,
    authorization: str | None = Header(default=None),
) -> ContentBrief:
    try:
        brief = store.get_brief(brief_id)
        actor_from_optional_auth(brief.organization_id, authorization)
        return brief
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/briefs/{brief_id}/drafts", response_model=DraftCreateResult)
def generate_drafts(
    brief_id: str,
    platform: str = "linkedin",
    content_type: str = "company_post",
    authorization: str | None = Header(default=None),
) -> DraftCreateResult:
    try:
        brief = store.get_brief(brief_id)
        actor_id = require_org_role(brief.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, drafts = store.run_job(
            brief.organization_id,
            actor_id,
            JobKind.draft_generation,
            "brief",
            brief_id,
            {"brief_id": brief_id, "platform": platform, "content_type": content_type},
            lambda: store.generate_drafts(brief_id, platform, content_type, actor_id),
            summarize_list_result,
        )
        if drafts:
            if actor_id:
                store.mark_onboarding_step(drafts[0].organization_id, actor_id, OnboardingStep.first_draft_created)
        return DraftCreateResult(drafts=drafts)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/drafts/{draft_id}", response_model=Draft)
def get_draft(
    draft_id: str,
    authorization: str | None = Header(default=None),
) -> Draft:
    try:
        draft = store.get_draft(draft_id)
        actor_from_optional_auth(draft.organization_id, authorization)
        return draft
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/drafts/{draft_id}", response_model=Draft)
def update_draft(
    draft_id: str,
    payload: DraftUpdate,
    authorization: str | None = Header(default=None),
) -> Draft:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        return store.update_draft_body(draft_id, payload.body, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/drafts/{draft_id}/reviewer-package", response_model=ReviewerPackage)
def reviewer_package(
    draft_id: str,
    authorization: str | None = Header(default=None),
) -> ReviewerPackage:
    try:
        draft = store.get_draft(draft_id)
        actor_from_optional_auth(draft.organization_id, authorization)
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
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/regenerate", response_model=DraftCreateResult)
def regenerate_draft(
    draft_id: str,
    authorization: str | None = Header(default=None),
) -> DraftCreateResult:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, drafts = store.run_job(
            draft.organization_id,
            actor_id,
            JobKind.draft_regeneration,
            "draft",
            draft_id,
            {"draft_id": draft_id},
            lambda: store.regenerate_drafts_for_draft(draft_id, actor_id),
            summarize_list_result,
        )
        return DraftCreateResult(drafts=drafts)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/approve")
def approve_draft(
    draft_id: str,
    payload: ReviewDecisionCreate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> object:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.reviewer}, actor_id)
        decision = store.approve_draft(draft_id, payload, actor_id)
        draft = store.get_draft(draft_id)
        if bearer_token(authorization) and draft.status == DraftStatus.approved:
            store.mark_onboarding_step(draft.organization_id, actor_id, OnboardingStep.first_artifact_approved)
        return decision
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except ApprovalBlockedError as error:
        raise approval_blocked(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/reject")
def reject_draft(
    draft_id: str,
    payload: ReviewDecisionCreate,
    authorization: str | None = Header(default=None),
) -> object:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.reviewer}, "local_user")
        return store.reject_draft(draft_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except ReviewDecisionRequiredError as error:
        raise bad_review_decision(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/export")
def export_draft(
    draft_id: str,
    authorization: str | None = Header(default=None),
) -> object:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        return store.export_draft(draft_id, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except ApprovalBlockedError as error:
        raise approval_blocked(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/schedule")
def schedule_draft(
    draft_id: str,
    payload: DraftScheduleCreate,
    authorization: str | None = Header(default=None),
) -> object:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        return store.schedule_draft(draft_id, payload.scheduled_for, payload.reason, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/publish/linkedin", response_model=PublishResult)
def publish_draft_to_linkedin(
    draft_id: str,
    payload: DraftPublishCreate,
    authorization: str | None = Header(default=None),
) -> PublishResult:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, result = store.run_job(
            draft.organization_id,
            actor_id,
            JobKind.linkedin_publish,
            "draft",
            draft_id,
            payload.model_dump(mode="json"),
            lambda: store.publish_draft_to_linkedin(draft_id, payload, actor_id),
            lambda publish_result: publish_result.model_dump(mode="json"),
        )
        return result
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except ApprovalBlockedError as error:
        raise approval_blocked(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/jobs", response_model=list[BackgroundJob])
def list_jobs(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[BackgroundJob]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_jobs(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/model-calls", response_model=list[ModelCallLog])
def list_model_calls(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[ModelCallLog]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_model_call_logs(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, BackgroundJob | list[BackgroundJobLog]]:
    try:
        job = store.get_job(job_id)
        actor_from_optional_auth(job.organization_id, authorization)
        return {"job": job, "logs": store.list_job_logs(job_id)}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/jobs/{job_id}/retry")
def retry_job(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, BackgroundJob | list[BackgroundJobLog]]:
    try:
        job = store.get_job(job_id)
        actor_id = require_org_role(job.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        job = store.reset_job_for_retry(job_id, actor_id)
        if job.kind in {JobKind.source_ingest, JobKind.source_refresh}:
            store.run_existing_job(
                job.id,
                lambda: store.ingest_source(job.entity_id, actor_id),
                lambda chunks: {"chunk_count": len(chunks)},
            )
        elif job.kind == JobKind.opportunity_generation:
            store.run_existing_job(
                job.id,
                lambda: store.generate_opportunities(job.organization_id, actor_id),
                summarize_list_result,
            )
        elif job.kind == JobKind.trend_opportunity_generation:
            store.run_existing_job(
                job.id,
                lambda: store.generate_trend_opportunities(job.organization_id, actor_id),
                summarize_list_result,
            )
        elif job.kind == JobKind.draft_generation:
            store.run_existing_job(
                job.id,
                lambda: store.generate_drafts(
                    str(job.payload["brief_id"]),
                    str(job.payload.get("platform", "linkedin")),
                    str(job.payload.get("content_type", "company_post")),
                    actor_id,
                ),
                summarize_list_result,
            )
        elif job.kind == JobKind.draft_regeneration:
            store.run_existing_job(
                job.id,
                lambda: store.regenerate_drafts_for_draft(job.entity_id, actor_id),
                summarize_list_result,
            )
        elif job.kind == JobKind.linkedin_publish:
            payload = DraftPublishCreate(**job.payload)
            store.run_existing_job(
                job.id,
                lambda: store.publish_draft_to_linkedin(job.entity_id, payload, actor_id),
                lambda result: result.model_dump(mode="json"),
            )
        elif job.kind == JobKind.analytics_import:
            store.run_existing_job(
                job.id,
                lambda: store.import_linkedin_analytics(job.organization_id, actor_id),
                summarize_list_result,
            )
        elif job.kind == JobKind.performance_capture:
            payload = PerformanceMetricsCreate(**job.payload)
            store.run_existing_job(
                job.id,
                lambda: store.record_performance_metrics(job.entity_id, payload, actor_id),
                summarize_one_result,
            )
        elif job.kind == JobKind.preference_suggestion_generation:
            store.run_existing_job(
                job.id,
                lambda: store.generate_preference_suggestions(job.organization_id, actor_id),
                summarize_list_result,
            )
        else:
            raise PermissionDeniedError("This job kind cannot be retried.")
        return {"job": store.get_job(job.id), "logs": store.list_job_logs(job.id)}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/memory")
def memory(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[object]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_memory(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/preference-suggestions", response_model=list[PreferenceSuggestion])
def list_preference_suggestions(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[PreferenceSuggestion]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_preference_suggestions(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/preference-suggestions/generate", response_model=list[PreferenceSuggestion])
def generate_preference_suggestions(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[PreferenceSuggestion]:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, suggestions = store.run_job(
            organization_id,
            actor_id,
            JobKind.preference_suggestion_generation,
            "organization",
            organization_id,
            {"organization_id": organization_id},
            lambda: store.generate_preference_suggestions(organization_id, actor_id),
            summarize_list_result,
        )
        return suggestions
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/preference-suggestions/{suggestion_id}/approve", response_model=PreferenceSuggestion)
def approve_preference_suggestion(
    suggestion_id: str,
    payload: PreferenceSuggestionDecision,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> PreferenceSuggestion:
    try:
        suggestion = store.get_preference_suggestion(suggestion_id)
        actor_id = require_org_role(suggestion.organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.approve_preference_suggestion(suggestion_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/preference-suggestions/{suggestion_id}/dismiss", response_model=PreferenceSuggestion)
def dismiss_preference_suggestion(
    suggestion_id: str,
    payload: PreferenceSuggestionDecision,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> PreferenceSuggestion:
    try:
        suggestion = store.get_preference_suggestion(suggestion_id)
        actor_id = require_org_role(suggestion.organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.dismiss_preference_suggestion(suggestion_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/memory/{memory_id}/performance", response_model=PostMemory)
def record_memory_performance(
    memory_id: str,
    payload: PerformanceMetricsCreate,
    authorization: str | None = Header(default=None),
) -> PostMemory:
    try:
        memory_item = store.get_memory(memory_id)
        actor_id = require_org_role(memory_item.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, memory = store.run_job(
            memory_item.organization_id,
            actor_id,
            JobKind.performance_capture,
            "post_memory",
            memory_id,
            payload.model_dump(mode="json"),
            lambda: store.record_performance_metrics(memory_id, payload, actor_id),
            summarize_one_result,
        )
        return memory
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/analytics/import", response_model=list[PostMemory])
def import_linkedin_analytics(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[PostMemory]:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, imported = store.run_job(
            organization_id,
            actor_id,
            JobKind.analytics_import,
            "organization",
            organization_id,
            {"organization_id": organization_id},
            lambda: store.import_linkedin_analytics(organization_id, actor_id),
            summarize_list_result,
        )
        return imported
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/analytics", response_model=AnalyticsDashboard)
def analytics_dashboard(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> AnalyticsDashboard:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.analytics_dashboard(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/strategy", response_model=StrategyDashboard)
def strategy_dashboard(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> StrategyDashboard:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.strategy_dashboard(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/content-artifacts", response_model=list[ContentArtifact])
def content_artifacts(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[ContentArtifact]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_content_artifacts(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/calendar", response_model=list[Draft])
def calendar(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[Draft]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_calendar(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/audit-logs")
def audit_logs(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[object]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_audit_logs(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
