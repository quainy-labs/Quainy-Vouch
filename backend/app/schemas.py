from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def normalize_confidence_score(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip().rstrip("%")
        try:
            value = float(stripped)
        except ValueError:
            return value
    if isinstance(value, (int, float)) and value > 1:
        if value <= 10:
            return value / 10
        if value <= 100:
            return value / 100
    return value


class SourceStatus(str, Enum):
    approved = "approved"
    disabled = "disabled"
    archived = "archived"


class CalendarEventType(str, Enum):
    company = "company"
    public = "public"


class CalendarEventCreate(BaseModel):
    title: str = Field(min_length=1)
    event_date: datetime
    event_type: CalendarEventType = CalendarEventType.company
    description: str | None = None
    relevance_terms: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def clean_event_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_optional_event_description(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("relevance_terms")
    @classmethod
    def clean_event_terms(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            item = value.strip().lower()
            if item and item not in cleaned:
                cleaned.append(item)
        return cleaned


class CalendarEvent(CalendarEventCreate):
    id: str = Field(default_factory=lambda: new_id("event"))
    organization_id: str
    created_at: datetime = Field(default_factory=now_utc)


class TrendSignalCreate(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=10)
    industry: str | None = None
    relevance_terms: list[str] = Field(default_factory=list)
    source_uri: str | None = None

    @field_validator("title", "summary", "industry", "source_uri")
    @classmethod
    def clean_optional_trend_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned

    @field_validator("relevance_terms")
    @classmethod
    def clean_trend_terms(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            item = value.strip().lower()
            if item and item not in cleaned:
                cleaned.append(item)
        return cleaned


class TrendSignal(TrendSignalCreate):
    id: str = Field(default_factory=lambda: new_id("trend"))
    organization_id: str
    created_at: datetime = Field(default_factory=now_utc)


class UserRole(str, Enum):
    owner = "owner"
    editor = "editor"
    reviewer = "reviewer"
    viewer = "viewer"


class DraftStatus(str, Enum):
    draft = "draft"
    needs_review = "needs_review"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    scheduled = "scheduled"
    exported = "exported"
    published = "published"


class Decision(str, Enum):
    approve = "approve"
    reject = "reject"
    schedule = "schedule"
    export = "export"
    publish = "publish"
    regenerate = "regenerate"


class PreferenceSuggestionStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    dismissed = "dismissed"


class PreferenceSuggestionKind(str, Enum):
    voice_phrase = "voice_phrase"
    rejected_pattern = "rejected_pattern"
    memory_update = "memory_update"


class PublishingProvider(str, Enum):
    linkedin = "linkedin"
    reddit = "reddit"
    instagram = "instagram"


class LinkedInPublishTarget(str, Enum):
    company_page = "company_page"
    personal_profile = "personal_profile"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class JobKind(str, Enum):
    source_ingest = "source_ingest"
    source_refresh = "source_refresh"
    opportunity_generation = "opportunity_generation"
    trend_opportunity_generation = "trend_opportunity_generation"
    draft_generation = "draft_generation"
    draft_regeneration = "draft_regeneration"
    linkedin_publish = "linkedin_publish"
    analytics_import = "analytics_import"
    performance_capture = "performance_capture"
    preference_suggestion_generation = "preference_suggestion_generation"


class ModelCallStatus(str, Enum):
    succeeded = "succeeded"
    failed = "failed"


class OnboardingStep(str, Enum):
    account_created = "account_created"
    organization_created = "organization_created"
    profile_started = "profile_started"
    profile_skipped = "profile_skipped"
    source_added = "source_added"
    first_opportunity_generated = "first_opportunity_generated"
    first_brief_created = "first_brief_created"
    first_draft_created = "first_draft_created"
    first_artifact_approved = "first_artifact_approved"


class AccountCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)

    @field_validator("name", "email", "password")
    @classmethod
    def clean_account_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned

    @field_validator("email")
    @classmethod
    def clean_account_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned:
            raise ValueError("Email must contain @")
        return cleaned


class AccountLogin(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def clean_login_email(cls, value: str) -> str:
        return value.strip().lower()


class Account(BaseModel):
    id: str = Field(default_factory=lambda: new_id("acct"))
    name: str
    email: str
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class OnboardingState(BaseModel):
    organization_id: str
    account_id: str
    completed_steps: list[OnboardingStep] = Field(default_factory=list)
    profile_skipped: bool = False
    completed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=now_utc)

    @computed_field
    @property
    def completion_percent(self) -> int:
        meaningful_steps = {
            OnboardingStep.account_created,
            OnboardingStep.organization_created,
            OnboardingStep.profile_started,
            OnboardingStep.profile_skipped,
            OnboardingStep.source_added,
            OnboardingStep.first_opportunity_generated,
            OnboardingStep.first_brief_created,
            OnboardingStep.first_draft_created,
            OnboardingStep.first_artifact_approved,
        }
        profile_done = OnboardingStep.profile_started in self.completed_steps or self.profile_skipped
        count = len([step for step in self.completed_steps if step in meaningful_steps])
        if profile_done and OnboardingStep.profile_started not in self.completed_steps:
            count += 1
        return min(100, round((count / 8) * 100))


class OnboardingDecision(BaseModel):
    skip_profile: bool = False


class AuthenticatedWorkspace(BaseModel):
    token: str
    account: Account
    organization: "Organization"
    user: "User"
    profile: "CompanyProfile"
    onboarding: OnboardingState


class CurrentWorkspace(BaseModel):
    account: Account
    organization: "Organization"
    user: "User"
    profile: "CompanyProfile"
    sources: list["Source"] = Field(default_factory=list)
    onboarding: OnboardingState


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1)
    website_url: str | None = None
    industry: str | None = None
    description: str | None = None
    audience_summary: str | None = None
    default_timezone: str = "UTC"

    @field_validator("name", "default_timezone")
    @classmethod
    def non_empty_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    website_url: str | None = None
    industry: str | None = None
    description: str | None = None
    audience_summary: str | None = None
    default_timezone: str | None = None

    @field_validator("name", "default_timezone")
    @classmethod
    def optional_non_empty_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned


class Organization(OrganizationCreate):
    id: str = Field(default_factory=lambda: new_id("org"))
    status: str = "active"
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class SignupCreate(AccountCreate):
    organization_name: str = Field(min_length=1)
    website_url: str | None = None
    industry: str | None = None
    description: str | None = None
    audience_summary: str | None = None
    default_timezone: str = "UTC"

    @field_validator("organization_name", "default_timezone")
    @classmethod
    def clean_signup_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned


class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str | None = None
    role: UserRole = UserRole.viewer

    @field_validator("name")
    @classmethod
    def clean_user_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned

    @field_validator("email")
    @classmethod
    def clean_optional_user_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    email: str | None = None
    role: UserRole | None = None

    @field_validator("name", "email")
    @classmethod
    def clean_optional_user_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class User(UserCreate):
    id: str = Field(default_factory=lambda: new_id("user"))
    organization_id: str
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CompanyProfileUpdate(BaseModel):
    one_liner: str | None = None
    mission: str | None = None
    product_summary: str | None = None
    audience: str | None = None
    voice_rules: list[str] = Field(default_factory=list)
    preferred_phrases: list[str] = Field(default_factory=list)
    banned_phrases: list[str] = Field(default_factory=list)
    approved_claims: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    content_pillars: list[str] = Field(default_factory=list)
    sensitive_topics: list[str] = Field(default_factory=list)

    @field_validator(
        "voice_rules",
        "preferred_phrases",
        "banned_phrases",
        "approved_claims",
        "forbidden_claims",
        "content_pillars",
        "sensitive_topics",
    )
    @classmethod
    def clean_string_lists(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            item = value.strip()
            if item and item not in cleaned:
                cleaned.append(item)
        return cleaned

    @field_validator("one_liner", "mission", "product_summary", "audience")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class CompanyProfile(CompanyProfileUpdate):
    organization_id: str
    updated_at: datetime = Field(default_factory=now_utc)


class SourceCreate(BaseModel):
    source_type: str = "manual_note"
    title: str = Field(min_length=1)
    uri: str | None = None
    raw_text: str = Field(min_length=20)
    approval_status: SourceStatus = SourceStatus.approved
    freshness_days: int = 180

    @field_validator("source_type", "title", "raw_text")
    @classmethod
    def clean_source_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned

    @model_validator(mode="after")
    def validate_uri_source(self) -> "SourceCreate":
        if self.source_type == "url":
            parsed = urlparse(self.uri or "")
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("URL sources require a single http(s) page URI")
        if self.source_type == "github_release":
            parsed = urlparse(self.uri or "")
            parts = [part for part in parsed.path.split("/") if part]
            if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com" or len(parts) < 2:
                raise ValueError("GitHub release sources require a selected public github.com owner/repo URI")
        if self.source_type == "notion_page":
            parsed = urlparse(self.uri or "")
            notion_page_uri = parsed.scheme == "notion" and parsed.netloc == "page" and bool(parsed.path.strip("/"))
            notion_web_uri = parsed.scheme in {"http", "https"} and parsed.netloc.endswith("notion.so")
            if not notion_page_uri and not notion_web_uri:
                raise ValueError("Notion sources require a selected page URI")
        return self


class SourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    uri: str | None = None
    raw_text: str | None = Field(default=None, min_length=20)
    approval_status: SourceStatus | None = None
    freshness_days: int | None = None

    @field_validator("title")
    @classmethod
    def clean_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned

    @field_validator("raw_text")
    @classmethod
    def clean_optional_raw_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) < 20:
            raise ValueError("Raw text must contain at least 20 characters")
        return cleaned


class Source(BaseModel):
    id: str = Field(default_factory=lambda: new_id("src"))
    organization_id: str
    source_type: str
    title: str
    uri: str | None = None
    approval_status: SourceStatus = SourceStatus.approved
    freshness_days: int = 180
    last_ingested_at: datetime | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class SourceDetail(BaseModel):
    source: Source
    raw_text: str
    chunk_count: int
    audit_logs: list["AuditLog"] = Field(default_factory=list)


class KnowledgeReadinessSignal(BaseModel):
    key: str
    label: str
    score: float = Field(ge=0.0, le=1.0)
    status: str
    detail: str


class KnowledgeReadinessRecommendation(BaseModel):
    title: str
    detail: str
    action: str
    priority: str = "medium"


class KnowledgeReadiness(BaseModel):
    organization_id: str
    overall_score: float = Field(ge=0.0, le=1.0)
    status: str
    profile_completeness: float = Field(ge=0.0, le=1.0)
    approved_source_count: int = 0
    stale_source_count: int = 0
    covered_pillar_count: int = 0
    total_pillar_count: int = 0
    retrievable_chunk_count: int = 0
    signals: list[KnowledgeReadinessSignal] = Field(default_factory=list)
    recommendations: list[KnowledgeReadinessRecommendation] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=now_utc)


class SourceDocument(BaseModel):
    id: str = Field(default_factory=lambda: new_id("doc"))
    source_id: str
    title: str
    raw_text: str
    normalized_text: str
    content_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class SourceChunk(BaseModel):
    id: str = Field(default_factory=lambda: new_id("chk"))
    source_document_id: str | None = None
    source_id: str
    organization_id: str
    chunk_text: str
    chunk_index: int
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class RetrievalQuery(BaseModel):
    query: str = Field(min_length=2)
    limit: int = Field(default=6, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Query must contain at least two characters")
        return cleaned


class RetrievalResult(BaseModel):
    chunk: SourceChunk
    source: Source
    score: float


class OpportunityRecommendation(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    why_now: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        return normalize_confidence_score(value)


class OpportunityRecommendationSet(BaseModel):
    recommendations: list[OpportunityRecommendation] = Field(default_factory=list)


class ContentOpportunity(BaseModel):
    id: str = Field(default_factory=lambda: new_id("opp"))
    organization_id: str
    title: str
    summary: str
    reason_today: str
    source_ids: list[str]
    freshness_score: float
    relevance_score: float
    confidence_score: float
    status: str = "suggested"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class ContentBrief(BaseModel):
    id: str = Field(default_factory=lambda: new_id("brief"))
    opportunity_id: str
    organization_id: str
    objective: str
    audience: str
    key_message: str
    supporting_points: list[str]
    claims: list[str]
    do_not_say: list[str] = Field(default_factory=list)
    source_ids: list[str]
    risks: list[str] = Field(default_factory=list)
    prompt_version: str = "brief_builder.v1"
    builder_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class BriefRecommendation(BaseModel):
    objective: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    key_message: str = Field(min_length=1)
    supporting_points: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class DraftGenerationSpec(BaseModel):
    id: str = Field(default_factory=lambda: new_id("spec"))
    content_brief_id: str
    platform: str
    content_type: str
    adapter_name: str
    adapter_version: str
    prompt_version: str
    rules: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class ClaimCheck(BaseModel):
    text: str
    claim_type: str
    confidence: float
    support_status: str
    supporting_chunk_ids: list[str] = Field(default_factory=list)
    risk_reason: str | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        return normalize_confidence_score(value)


class Draft(BaseModel):
    id: str = Field(default_factory=lambda: new_id("draft"))
    content_brief_id: str
    organization_id: str
    platform: str = "linkedin"
    content_type: str = "company_post"
    body: str
    hook: str
    hashtags: list[str] = Field(default_factory=list)
    status: DraftStatus = DraftStatus.needs_review
    source_ids: list[str] = Field(default_factory=list)
    source_map: dict[str, list[str]] = Field(default_factory=dict)
    risk_report: list[str] = Field(default_factory=list)
    quality_report: list[str] = Field(default_factory=list)
    duplicate_report: dict[str, Any] = Field(default_factory=dict)
    claims: list[ClaimCheck] = Field(default_factory=list)
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    approval_metadata: dict[str, Any] = Field(default_factory=dict)
    scheduled_for: datetime | None = None
    exported_at: datetime | None = None
    published_at: datetime | None = None
    publish_result: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class DraftVariantRecommendation(BaseModel):
    hook: str = Field(min_length=1)
    body: str = Field(min_length=1)
    hashtags: list[str] = Field(default_factory=list)


class DraftRecommendationSet(BaseModel):
    variants: list[DraftVariantRecommendation] = Field(default_factory=list)


class ClaimExtractionResult(BaseModel):
    claims: list[str] = Field(default_factory=list)


class RiskCheckResult(BaseModel):
    risks: list[str] = Field(default_factory=list)
    quality_notes: list[str] = Field(default_factory=list)


class StrategyRecommendation(BaseModel):
    title: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    source_basis: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        return normalize_confidence_score(value)


class StrategyRecommendationSet(BaseModel):
    recommendations: list[StrategyRecommendation] = Field(default_factory=list)


class DraftCreateResult(BaseModel):
    drafts: list[Draft]


class DraftUpdate(BaseModel):
    body: str


class DraftScheduleCreate(BaseModel):
    scheduled_for: datetime
    reason: str | None = None


class ApprovalPolicyUpdate(BaseModel):
    required_reviewer_count: int = Field(default=1, ge=1, le=10)
    require_approval_before_export: bool = True
    require_approval_before_publish: bool = True
    allow_risk_override: bool = True


class ApprovalPolicy(ApprovalPolicyUpdate):
    organization_id: str
    updated_at: datetime = Field(default_factory=now_utc)


class LinkedInIntegrationUpdate(BaseModel):
    selected_page_urn: str | None = None
    selected_page_name: str | None = None
    oauth_status: str = "not_connected"
    permissions: list[str] = Field(default_factory=list)
    publishing_enabled: bool = False

    @field_validator("selected_page_urn", "selected_page_name", "oauth_status")
    @classmethod
    def clean_optional_integration_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("permissions")
    @classmethod
    def clean_permissions(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            item = value.strip()
            if item and item not in cleaned:
                cleaned.append(item)
        return cleaned


class LinkedInIntegration(LinkedInIntegrationUpdate):
    organization_id: str
    updated_at: datetime = Field(default_factory=now_utc)


class PublishingConnection(BaseModel):
    organization_id: str
    provider: PublishingProvider
    oauth_status: str = "not_connected"
    scopes: list[str] = Field(default_factory=list)
    access_token: str | None = Field(default=None, exclude=True)
    refresh_token: str | None = Field(default=None, exclude=True)
    token_type: str | None = None
    expires_at: datetime | None = None
    account_id: str | None = None
    account_name: str | None = None
    selected_target_id: str | None = None
    selected_target_name: str | None = None
    selected_target_type: str | None = None
    publishing_enabled: bool = False
    updated_at: datetime = Field(default_factory=now_utc)

    @computed_field
    @property
    def access_token_configured(self) -> bool:
        return bool(self.access_token)

    @computed_field
    @property
    def refresh_token_configured(self) -> bool:
        return bool(self.refresh_token)


class PublishingOAuthStart(BaseModel):
    provider: str
    authorization_url: str


class PublishingOAuthCallback(BaseModel):
    provider: PublishingProvider
    status: str
    message: str
    connection: PublishingConnection


class AIProviderKind(str, Enum):
    deterministic = "deterministic"
    openai = "openai"
    gemini = "gemini"
    openai_compatible = "openai_compatible"
    local = "local"


class AIProviderRuntime(str, Enum):
    none = "none"
    ollama = "ollama"
    vllm = "vllm"
    lm_studio = "lm_studio"
    custom = "custom"


class AIProviderSettingsUpdate(BaseModel):
    generation_provider: AIProviderKind = AIProviderKind.deterministic
    generation_model: str = "deterministic-structured-v1"
    generation_base_url: str | None = None
    generation_api_key_env_var: str | None = None
    generation_local_runtime: AIProviderRuntime = AIProviderRuntime.none
    embedding_provider: AIProviderKind = AIProviderKind.deterministic
    embedding_model: str = "local-hash"
    embedding_base_url: str | None = None
    embedding_api_key_env_var: str | None = None
    embedding_local_runtime: AIProviderRuntime = AIProviderRuntime.none
    enabled: bool = True

    @model_validator(mode="before")
    @classmethod
    def map_legacy_local_runtime(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("local_runtime"):
            data.setdefault("generation_local_runtime", data["local_runtime"])
            data.setdefault("embedding_local_runtime", data["local_runtime"])
        return data

    @field_validator(
        "generation_model",
        "generation_base_url",
        "generation_api_key_env_var",
        "embedding_model",
        "embedding_base_url",
        "embedding_api_key_env_var",
    )
    @classmethod
    def clean_optional_provider_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("generation_api_key_env_var", "embedding_api_key_env_var")
    @classmethod
    def validate_secret_reference(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Secret reference can only include letters, numbers, underscores, and hyphens")
        return value

    @model_validator(mode="after")
    def validate_provider_requirements(self) -> AIProviderSettingsUpdate:
        if self.generation_provider in {AIProviderKind.openai_compatible, AIProviderKind.local} and not self.generation_base_url:
            raise ValueError("Generation base URL is required for cloud LLM or local runtime providers")
        if self.embedding_provider in {AIProviderKind.openai_compatible, AIProviderKind.local} and not self.embedding_base_url:
            raise ValueError("Embedding base URL is required for cloud LLM or local runtime providers")
        if self.generation_provider == AIProviderKind.openai and not self.generation_api_key_env_var:
            self.generation_api_key_env_var = "OPENAI_API_KEY"
        if self.generation_provider == AIProviderKind.gemini and not self.generation_api_key_env_var:
            self.generation_api_key_env_var = "GEMINI_API_KEY"
        if self.embedding_provider == AIProviderKind.openai and not self.embedding_api_key_env_var:
            self.embedding_api_key_env_var = "OPENAI_API_KEY"
        if self.embedding_provider == AIProviderKind.gemini:
            raise ValueError("Gemini embedding is not supported yet. Use deterministic, local, or OpenAI-compatible embeddings.")
        return self


class AIProviderSettings(AIProviderSettingsUpdate):
    organization_id: str
    generation_api_key_configured: bool = False
    embedding_api_key_configured: bool = False
    updated_at: datetime = Field(default_factory=now_utc)
    updated_by: str | None = None


class AIProviderConnectionCheck(BaseModel):
    kind: str
    provider: str
    model: str
    status: str
    message: str


class AIProviderConnectionTest(BaseModel):
    organization_id: str
    status: str
    message: str
    generation: AIProviderConnectionCheck
    embedding: AIProviderConnectionCheck
    checked_at: datetime = Field(default_factory=now_utc)


class DraftPublishCreate(BaseModel):
    page_urn: str | None = None
    page_name: str | None = None
    simulate_failure: bool = False
    reason: str | None = None

    @field_validator("page_urn", "page_name", "reason")
    @classmethod
    def clean_optional_publish_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class PublishResult(BaseModel):
    provider: str
    status: str
    draft_id: str
    page_urn: str
    page_name: str | None = None
    provider_post_id: str | None = None
    published_url: str | None = None
    failure_reason: str | None = None
    requested_at: datetime = Field(default_factory=now_utc)
    published_at: datetime | None = None


class PerformanceMetricsCreate(BaseModel):
    impressions: int = Field(default=0, ge=0)
    reactions: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    source: str = "manual"
    notes: str | None = None
    captured_at: datetime = Field(default_factory=now_utc)

    @field_validator("source", "notes")
    @classmethod
    def clean_optional_metric_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class AnalyticsPostSummary(BaseModel):
    post_memory_id: str
    source_draft_id: str
    platform: str
    content_type: str
    excerpt: str
    performance_score: float
    metrics: dict[str, int] = Field(default_factory=dict)


class AnalyticsDashboard(BaseModel):
    organization_id: str
    posts_analyzed: int
    total_impressions: int
    total_reactions: int
    total_comments: int
    total_shares: int
    total_clicks: int
    average_performance_score: float
    top_posts: list[AnalyticsPostSummary] = Field(default_factory=list)


class ContentArtifact(BaseModel):
    id: str
    kind: str
    title: str
    platform: str | None = None
    content_type: str | None = None
    status: str
    excerpt: str
    source_count: int = 0
    risk_count: int = 0
    updated_at: datetime
    scheduled_for: datetime | None = None
    published_at: datetime | None = None


class PillarCoverage(BaseModel):
    pillar: str
    source_count: int = 0
    artifact_count: int = 0
    performance_score: float = 0.0
    recommendation: str


class TopicRepetition(BaseModel):
    topic: str
    count: int
    last_seen: datetime | None = None


class PerformanceBreakdown(BaseModel):
    key: str
    label: str
    posts: int
    average_score: float = 0.0
    impressions: int = 0
    reactions: int = 0
    clicks: int = 0


class StrategyDirection(BaseModel):
    title: str
    rationale: str
    source_basis: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class StrategyDashboard(BaseModel):
    organization_id: str
    pillar_coverage: list[PillarCoverage] = Field(default_factory=list)
    topic_repetition: list[TopicRepetition] = Field(default_factory=list)
    performance_by_platform: list[PerformanceBreakdown] = Field(default_factory=list)
    performance_by_content_type: list[PerformanceBreakdown] = Field(default_factory=list)
    suggested_directions: list[StrategyDirection] = Field(default_factory=list)


class DeletionReceipt(BaseModel):
    organization_id: str
    deleted_by: str
    deleted_at: datetime = Field(default_factory=now_utc)
    counts: dict[str, int] = Field(default_factory=dict)
    message: str


class PreferenceSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: new_id("pref"))
    organization_id: str
    kind: PreferenceSuggestionKind
    title: str
    rationale: str
    proposed_update: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    status: PreferenceSuggestionStatus = PreferenceSuggestionStatus.pending
    created_at: datetime = Field(default_factory=now_utc)
    decided_at: datetime | None = None


class PreferenceSuggestionDecision(BaseModel):
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def clean_preference_reason(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class ReviewDecisionCreate(BaseModel):
    edited_body: str | None = None
    reason: str | None = None
    override_reason: str | None = None
    labels: list[str] = Field(default_factory=list)

    @field_validator("edited_body", "reason", "override_reason")
    @classmethod
    def clean_optional_decision_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class ApprovalDecision(BaseModel):
    id: str = Field(default_factory=lambda: new_id("decision"))
    draft_id: str
    decision: Decision
    edited_body: str | None = None
    reason: str | None = None
    override_reason: str | None = None
    reviewer_id: str | None = None
    labels: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)


class PostMemory(BaseModel):
    id: str = Field(default_factory=lambda: new_id("mem"))
    organization_id: str
    platform: str
    content_type: str
    final_body: str
    source_draft_id: str
    topic_labels: list[str]
    idea_fingerprint: str
    approved_at: datetime | None = None
    exported_at: datetime | None = None
    published_at: datetime | None = None
    performance_snapshot: dict[str, Any] = Field(default_factory=dict)


class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: new_id("audit"))
    organization_id: str
    actor_id: str = "local_user"
    action: str
    entity_type: str
    entity_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class BackgroundJob(BaseModel):
    id: str = Field(default_factory=lambda: new_id("job"))
    organization_id: str
    actor_id: str = "local_user"
    kind: JobKind
    status: JobStatus = JobStatus.queued
    entity_type: str
    entity_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    queued_at: datetime = Field(default_factory=now_utc)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime = Field(default_factory=now_utc)


class BackgroundJobLog(BaseModel):
    id: str = Field(default_factory=lambda: new_id("joblog"))
    job_id: str
    organization_id: str
    message: str
    level: str = "info"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_utc)


class ModelCallLog(BaseModel):
    id: str = Field(default_factory=lambda: new_id("modelcall"))
    organization_id: str
    actor_id: str = "local_user"
    provider: str
    model: str
    prompt_version: str
    schema_name: str
    status: ModelCallStatus
    prompt_hash: str
    source_ids: list[str] = Field(default_factory=list)
    request_metadata: dict[str, Any] = Field(default_factory=dict)
    response_metadata: dict[str, Any] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
    cost_usd: float | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=now_utc)


class ReviewerPackage(BaseModel):
    draft: Draft
    brief: ContentBrief
    opportunity: ContentOpportunity
    sources: list[Source]
    source_chunks: list[SourceChunk]
    decision_history: list[ApprovalDecision] = Field(default_factory=list)
    suggested_action: str
