from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class SourceStatus(str, Enum):
    approved = "approved"
    disabled = "disabled"
    archived = "archived"


class DraftStatus(str, Enum):
    draft = "draft"
    needs_review = "needs_review"
    approved = "approved"
    rejected = "rejected"
    exported = "exported"


class Decision(str, Enum):
    approve = "approve"
    reject = "reject"
    export = "export"
    regenerate = "regenerate"


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


class SourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    uri: str | None = None
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


class SourceChunk(BaseModel):
    id: str = Field(default_factory=lambda: new_id("chk"))
    source_id: str
    organization_id: str
    chunk_text: str
    chunk_index: int
    created_at: datetime = Field(default_factory=now_utc)


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
    source_ids: list[str]
    risks: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)


class ClaimCheck(BaseModel):
    text: str
    claim_type: str
    confidence: float
    support_status: str
    supporting_chunk_ids: list[str] = Field(default_factory=list)
    risk_reason: str | None = None


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
    source_map: dict[str, list[str]] = Field(default_factory=dict)
    risk_report: list[str] = Field(default_factory=list)
    quality_report: list[str] = Field(default_factory=list)
    duplicate_report: dict[str, Any] = Field(default_factory=dict)
    claims: list[ClaimCheck] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class DraftCreateResult(BaseModel):
    drafts: list[Draft]


class DraftUpdate(BaseModel):
    body: str


class ReviewDecisionCreate(BaseModel):
    edited_body: str | None = None
    reason: str | None = None
    labels: list[str] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    id: str = Field(default_factory=lambda: new_id("decision"))
    draft_id: str
    decision: Decision
    edited_body: str | None = None
    reason: str | None = None
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


class ReviewerPackage(BaseModel):
    draft: Draft
    brief: ContentBrief
    opportunity: ContentOpportunity
    sources: list[Source]
    source_chunks: list[SourceChunk]
    suggested_action: str
