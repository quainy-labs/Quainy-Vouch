from __future__ import annotations

import hashlib
import os
import re
import secrets
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from app.analytics import LocalAnalyticsImportProvider, build_performance_snapshot
from app.contracts import FormatAdapter
from app.briefs import build_brief
from app.drafts import generate_drafts
from app.format_adapters import (
    InstagramPostAdapter,
    LinkedInCompanyPostAdapter,
    RedditPostAdapter,
)
from app.intelligence import (
    content_hash,
    duplicate_check,
    idea_fingerprint,
    normalize_text,
    retrieve_chunks as lexical_retrieve_chunks,
    split_chunks,
    terms,
)
from app.opportunities import OpportunityGenerator
from app.preference_learning import PreferenceLearningEngine
from app.prompt_registry import prompt_versions
from app.providers import DeterministicModelProvider, build_embedding_provider, build_model_provider, cosine_similarity
from app.publishing import build_linkedin_publisher
from app.risk_checks import check_claims, high_risk_unsupported_claims, risk_check
from app.trends import TrendOpportunityGenerator
from app.schemas import (
    Account,
    AccountLogin,
    AIProviderConnectionTest,
    AIProviderKind,
    AIProviderSettings,
    AIProviderSettingsUpdate,
    ApprovalDecision,
    ApprovalPolicy,
    ApprovalPolicyUpdate,
    AnalyticsDashboard,
    AnalyticsPostSummary,
    AuditLog,
    BackgroundJob,
    BackgroundJobLog,
    CalendarEvent,
    CalendarEventCreate,
    CompanyProfile,
    CompanyProfileUpdate,
    ContentBrief,
    ContentArtifact,
    ContentOpportunity,
    CurrentWorkspace,
    DeletionReceipt,
    Decision,
    Draft,
    DraftPublishCreate,
    DraftStatus,
    BriefRecommendation,
    JobKind,
    JobStatus,
    KnowledgeReadiness,
    KnowledgeReadinessRecommendation,
    KnowledgeReadinessSignal,
    LinkedInIntegration,
    LinkedInIntegrationUpdate,
    ModelCallLog,
    ModelCallStatus,
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
    PreferenceSuggestionStatus,
    DraftRecommendationSet,
    OpportunityRecommendationSet,
    OpportunityRecommendation,
    PublishResult,
    ReviewDecisionCreate,
    SignupCreate,
    Source,
    SourceChunk,
    SourceCreate,
    SourceDetail,
    SourceDocument,
    SourceStatus,
    SourceUpdate,
    PerformanceBreakdown,
    PillarCoverage,
    StrategyDashboard,
    StrategyDirection,
    TopicRepetition,
    TrendSignal,
    TrendSignalCreate,
    User,
    UserCreate,
    UserRole,
    UserUpdate,
    now_utc,
)
from app.sample_data import QUAINY_SAMPLE_CONTEXT
from app.source_connectors import default_source_connectors


class NotFoundError(Exception):
    pass


class ApprovalBlockedError(Exception):
    pass


class ReviewDecisionRequiredError(Exception):
    pass


class PermissionDeniedError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class DataStore:
    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.account_password_hashes: dict[str, str] = {}
        self.account_ids_by_email: dict[str, str] = {}
        self.session_account_ids: dict[str, str] = {}
        self.primary_organization_by_account: dict[str, str] = {}
        self.onboarding_states: dict[tuple[str, str], OnboardingState] = {}
        self.organizations: dict[str, Organization] = {}
        self.users: dict[tuple[str, str], User] = {}
        self.approval_policies: dict[str, ApprovalPolicy] = {}
        self.profiles: dict[str, CompanyProfile] = {}
        self.sources: dict[str, Source] = {}
        self.source_raw_text: dict[str, str] = {}
        self.source_hashes: dict[str, str] = {}
        self.source_documents: dict[str, SourceDocument] = {}
        self.latest_document_by_source: dict[str, str] = {}
        self.chunks: dict[str, SourceChunk] = {}
        self.opportunities: dict[str, ContentOpportunity] = {}
        self.calendar_events: dict[str, CalendarEvent] = {}
        self.trend_signals: dict[str, TrendSignal] = {}
        self.briefs: dict[str, ContentBrief] = {}
        self.drafts: dict[str, Draft] = {}
        self.decisions: dict[str, ApprovalDecision] = {}
        self.memory: dict[str, PostMemory] = {}
        self.preference_suggestions: dict[str, PreferenceSuggestion] = {}
        self.linkedin_integrations: dict[str, LinkedInIntegration] = {}
        self.ai_provider_settings: dict[str, AIProviderSettings] = {}
        self.audit_logs: list[AuditLog] = []
        self.jobs: dict[str, BackgroundJob] = {}
        self.job_logs: list[BackgroundJobLog] = []
        self.model_call_logs: list[ModelCallLog] = []
        self.format_adapters: dict[tuple[str, str], FormatAdapter] = {}
        self.source_connectors = default_source_connectors()
        self.model_provider = build_model_provider()
        self.embedding_provider = build_embedding_provider()
        self.linkedin_publisher = build_linkedin_publisher()
        self.analytics_importer = LocalAnalyticsImportProvider()
        self.preference_learning = PreferenceLearningEngine()
        self.opportunity_generator = OpportunityGenerator()
        self.trend_opportunity_generator = TrendOpportunityGenerator()
        self.register_format_adapter(LinkedInCompanyPostAdapter())
        self.register_format_adapter(RedditPostAdapter())
        self.register_format_adapter(InstagramPostAdapter())

    def register_format_adapter(self, adapter: FormatAdapter) -> None:
        self.format_adapters[(adapter.platform, adapter.content_type)] = adapter

    def get_format_adapter(self, platform: str, content_type: str) -> FormatAdapter:
        key = (platform, content_type)
        if key not in self.format_adapters:
            raise NotFoundError(f"Format adapter not found for {platform}/{content_type}")
        return self.format_adapters[key]

    def _hash_password(self, password: str, salt: str | None = None) -> str:
        active_salt = salt or secrets.token_hex(16)
        iterations = 210_000
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            active_salt.encode("utf-8"),
            iterations,
        ).hex()
        return f"pbkdf2_sha256${iterations}${active_salt}${digest}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        if stored_hash.startswith("pbkdf2_sha256$"):
            _algorithm, iterations, salt, expected_digest = stored_hash.split("$", 3)
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return secrets.compare_digest(digest, expected_digest)
        salt, expected_digest = stored_hash.split(":", 1)
        digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
        return secrets.compare_digest(digest, expected_digest)

    def signup(self, payload: SignupCreate) -> tuple[str, CurrentWorkspace]:
        email = payload.email.strip().lower()
        if email in self.account_ids_by_email:
            raise PermissionDeniedError("An account with this email already exists.")
        account = Account(name=payload.name.strip(), email=email)
        self.accounts[account.id] = account
        self.account_ids_by_email[email] = account.id
        self.account_password_hashes[account.id] = self._hash_password(payload.password)
        org = self.create_organization(
            OrganizationCreate(
                name=payload.organization_name,
                website_url=payload.website_url,
                industry=payload.industry,
                description=payload.description,
                audience_summary=payload.audience_summary,
                default_timezone=payload.default_timezone,
            )
        )
        self.users.pop((org.id, "local_user"), None)
        user = User(
            id=account.id,
            organization_id=org.id,
            name=account.name,
            email=account.email,
            role=UserRole.owner,
        )
        self.users[(org.id, user.id)] = user
        self.primary_organization_by_account[account.id] = org.id
        onboarding = OnboardingState(
            organization_id=org.id,
            account_id=account.id,
            completed_steps=[
                OnboardingStep.account_created,
                OnboardingStep.organization_created,
            ],
        )
        self.onboarding_states[(org.id, account.id)] = onboarding
        token = self._create_session(account.id)
        self.log(org.id, "auth.signup", "account", account.id, {"email": account.email}, account.id)
        return token, self.current_workspace(token)

    def login(self, payload: AccountLogin) -> tuple[str, CurrentWorkspace]:
        account_id = self.account_ids_by_email.get(payload.email.strip().lower())
        if not account_id or not self._verify_password(payload.password, self.account_password_hashes[account_id]):
            raise AuthenticationError("Invalid email or password.")
        token = self._create_session(account_id)
        return token, self.current_workspace(token)

    def _create_session(self, account_id: str) -> str:
        token = f"qv_{secrets.token_urlsafe(32)}"
        self.session_account_ids[token] = account_id
        return token

    def account_for_token(self, token: str | None) -> Account:
        if not token or token not in self.session_account_ids:
            raise AuthenticationError("Authentication required.")
        account_id = self.session_account_ids[token]
        if account_id not in self.accounts:
            raise AuthenticationError("Authentication required.")
        return self.accounts[account_id]

    def current_workspace(self, token: str) -> CurrentWorkspace:
        account = self.account_for_token(token)
        organization_id = self.primary_organization_by_account.get(account.id)
        if not organization_id:
            raise NotFoundError("No organization found for this account.")
        user = self.get_user(organization_id, account.id)
        onboarding = self.get_onboarding_state(organization_id, account.id)
        return CurrentWorkspace(
            account=account,
            organization=self.get_organization(organization_id),
            user=user,
            profile=self.profiles[organization_id],
            sources=self.list_sources(organization_id),
            onboarding=onboarding,
        )

    def actor_id_for_token(self, token: str | None, organization_id: str) -> str:
        account = self.account_for_token(token)
        self.get_user(organization_id, account.id)
        return account.id

    def get_onboarding_state(self, organization_id: str, account_id: str) -> OnboardingState:
        key = (organization_id, account_id)
        if key not in self.onboarding_states:
            self.onboarding_states[key] = OnboardingState(
                organization_id=organization_id,
                account_id=account_id,
                completed_steps=[OnboardingStep.organization_created],
            )
        return self.onboarding_states[key]

    def mark_onboarding_step(
        self,
        organization_id: str,
        account_id: str,
        step: OnboardingStep,
        profile_skipped: bool | None = None,
    ) -> OnboardingState:
        state = self.get_onboarding_state(organization_id, account_id)
        completed = list(state.completed_steps)
        if step not in completed:
            completed.append(step)
        updates = {"completed_steps": completed, "updated_at": now_utc()}
        if profile_skipped is not None:
            updates["profile_skipped"] = profile_skipped
        updated = state.model_copy(update=updates)
        self.onboarding_states[(organization_id, account_id)] = updated
        self.log(organization_id, "onboarding.step_completed", "onboarding", account_id, {"step": step.value}, account_id)
        return updated

    def decide_onboarding_profile(
        self,
        organization_id: str,
        account_id: str,
        payload: OnboardingDecision,
    ) -> OnboardingState:
        step = OnboardingStep.profile_skipped if payload.skip_profile else OnboardingStep.profile_started
        return self.mark_onboarding_step(organization_id, account_id, step, profile_skipped=payload.skip_profile)

    def seed_quainy(self, root: Path) -> str:
        org = self.create_organization(
            OrganizationCreate(
                name="Quainy",
                website_url="https://quainy.com",
                industry="AI education and builder tools",
                description="A builder-first AI ecosystem helping people turn meaningful ideas into production-ready products.",
                audience_summary="Builders, students, developers, founders, and curious learners.",
                default_timezone="Asia/Kolkata",
            )
        )
        self.update_profile(
            org.id,
            CompanyProfileUpdate(
                one_liner="Quainy helps builders turn meaningful ideas into production-ready products.",
                mission="Help ambitious builders move from insight to production-ready products.",
                product_summary="Quainy Vouch turns approved company knowledge into trustworthy, source-backed public content.",
                audience="Builders, developers, founders, students, and teams learning to ship useful AI-native products.",
                voice_rules=[
                    "Serious but welcoming.",
                    "Practical, curious, and source-grounded.",
                    "Avoid hype, fear-based AI claims, and generic productivity language.",
                ],
                preferred_phrases=[
                    "production-ready products",
                    "product judgment",
                    "approved company knowledge",
                    "Build what matters. Ship what works.",
                ],
                banned_phrases=[
                    "go viral",
                    "10x your content",
                    "replace your team",
                    "fully autonomous posting",
                ],
                approved_claims=[
                    "Quainy is a builder-first AI ecosystem.",
                    "Quainy Vouch uses approved company knowledge for public content drafts.",
                ],
                forbidden_claims=[
                    "Quainy Vouch publishes automatically to LinkedIn.",
                    "Quainy guarantees engagement or revenue.",
                ],
                content_pillars=[
                    "approved company knowledge",
                    "source-backed public content",
                    "product judgment",
                    "production readiness",
                    "human approval",
                ],
            ),
        )
        source = self.create_source(
            org.id,
            SourceCreate(
                source_type="markdown",
                title="Quainy Vouch sample context",
                uri="sample://quainy-vouch-context",
                raw_text=QUAINY_SAMPLE_CONTEXT,
                approval_status=SourceStatus.approved,
            ),
        )
        self.ingest_source(source.id)
        return org.id

    def create_organization(self, payload: OrganizationCreate) -> Organization:
        org = Organization(**payload.model_dump())
        self.organizations[org.id] = org
        self.profiles[org.id] = CompanyProfile(organization_id=org.id)
        self.approval_policies[org.id] = ApprovalPolicy(organization_id=org.id)
        self.ai_provider_settings[org.id] = AIProviderSettings(organization_id=org.id)
        self.users[(org.id, "local_user")] = User(
            id="local_user",
            organization_id=org.id,
            name="Local Owner",
            email=None,
            role=UserRole.owner,
        )
        self.log(org.id, "organization.created", "organization", org.id)
        return org

    def get_approval_policy(self, organization_id: str) -> ApprovalPolicy:
        self.get_organization(organization_id)
        if organization_id not in self.approval_policies:
            self.approval_policies[organization_id] = ApprovalPolicy(organization_id=organization_id)
        return self.approval_policies[organization_id]

    def update_approval_policy(
        self,
        organization_id: str,
        payload: ApprovalPolicyUpdate,
        actor_id: str = "local_user",
    ) -> ApprovalPolicy:
        self.require_role(organization_id, actor_id, {UserRole.owner})
        policy = ApprovalPolicy(organization_id=organization_id, **payload.model_dump(), updated_at=now_utc())
        self.approval_policies[organization_id] = policy
        self.log(
            organization_id,
            "approval_policy.updated",
            "approval_policy",
            organization_id,
            policy.model_dump(mode="json"),
            actor_id,
        )
        return policy

    def get_ai_provider_settings(self, organization_id: str) -> AIProviderSettings:
        self.get_organization(organization_id)
        if organization_id not in self.ai_provider_settings:
            self.ai_provider_settings[organization_id] = AIProviderSettings(organization_id=organization_id)
        return self.ai_provider_settings[organization_id]

    def update_ai_provider_settings(
        self,
        organization_id: str,
        payload: AIProviderSettingsUpdate,
        actor_id: str = "local_user",
    ) -> AIProviderSettings:
        self.require_role(organization_id, actor_id, {UserRole.owner})
        settings = AIProviderSettings(
            organization_id=organization_id,
            **payload.model_dump(),
            generation_api_key_configured=bool(payload.generation_api_key_env_var),
            embedding_api_key_configured=bool(payload.embedding_api_key_env_var),
            updated_at=now_utc(),
            updated_by=actor_id,
        )
        self.ai_provider_settings[organization_id] = settings
        self.log(
            organization_id,
            "ai_provider_settings.updated",
            "ai_provider_settings",
            organization_id,
            {
                "generation_provider": settings.generation_provider.value,
                "generation_model": settings.generation_model,
                "embedding_provider": settings.embedding_provider.value,
                "embedding_model": settings.embedding_model,
                "local_runtime": settings.local_runtime.value,
                "enabled": settings.enabled,
                "generation_api_key_configured": settings.generation_api_key_configured,
                "embedding_api_key_configured": settings.embedding_api_key_configured,
            },
            actor_id,
        )
        return settings

    def model_provider_for_org(self, organization_id: str):
        settings = self.get_ai_provider_settings(organization_id)
        if not settings.enabled:
            return DeterministicModelProvider()
        if settings.generation_provider == AIProviderKind.deterministic:
            return self.model_provider
        api_key = None
        if settings.generation_api_key_env_var:
            api_key = os.getenv(settings.generation_api_key_env_var)
        return build_model_provider(
            settings.generation_provider.value,
            model=settings.generation_model,
            base_url=settings.generation_base_url,
            api_key=api_key,
        )

    def embedding_provider_for_org(self, organization_id: str):
        settings = self.get_ai_provider_settings(organization_id)
        if not settings.enabled or settings.embedding_provider == AIProviderKind.deterministic:
            return self.embedding_provider
        api_key = None
        if settings.embedding_api_key_env_var:
            api_key = os.getenv(settings.embedding_api_key_env_var)
        return build_embedding_provider(
            settings.embedding_provider.value,
            model=settings.embedding_model,
            base_url=settings.embedding_base_url,
            api_key=api_key,
        )

    def test_ai_provider_settings(
        self,
        organization_id: str,
        actor_id: str = "local_user",
    ) -> AIProviderConnectionTest:
        self.require_role(organization_id, actor_id, {UserRole.owner, UserRole.editor})
        settings = self.get_ai_provider_settings(organization_id)
        provider = self.model_provider_for_org(organization_id)
        provider_name = getattr(provider, "provider_name", settings.generation_provider.value)
        provider_model = getattr(provider, "model", settings.generation_model)
        if isinstance(provider, DeterministicModelProvider):
            return AIProviderConnectionTest(
                organization_id=organization_id,
                provider=provider_name,
                model=provider_model,
                status="succeeded",
                message="Deterministic structured generation is available.",
            )
        try:
            provider.generate_structured(
                "Return a compact JSON object that confirms provider connectivity.",
                "AIProviderConnectionTest",
                {
                    "type": "object",
                    "properties": {"ok": {"type": "boolean"}},
                    "required": ["ok"],
                    "additionalProperties": False,
                },
            )
        except Exception as error:
            return AIProviderConnectionTest(
                organization_id=organization_id,
                provider=provider_name,
                model=provider_model,
                status="failed",
                message=str(error),
            )
        return AIProviderConnectionTest(
            organization_id=organization_id,
            provider=provider_name,
            model=provider_model,
            status="succeeded",
            message="Provider returned a structured response.",
        )

    def list_users(self, organization_id: str) -> list[User]:
        self.get_organization(organization_id)
        return [user for (org_id, _user_id), user in self.users.items() if org_id == organization_id]

    def create_user(self, organization_id: str, payload: UserCreate, actor_id: str = "local_user") -> User:
        self.require_role(organization_id, actor_id, {UserRole.owner})
        user = User(organization_id=organization_id, **payload.model_dump())
        self.users[(organization_id, user.id)] = user
        self.log(organization_id, "user.created", "user", user.id, {"role": user.role}, actor_id)
        return user

    def update_user(self, organization_id: str, user_id: str, payload: UserUpdate, actor_id: str = "local_user") -> User:
        self.require_role(organization_id, actor_id, {UserRole.owner})
        user = self.get_user(organization_id, user_id)
        updates = payload.model_dump(exclude_unset=True)
        updated = user.model_copy(update={**updates, "updated_at": now_utc()})
        self.users[(organization_id, user_id)] = updated
        self.log(organization_id, "user.updated", "user", user_id, {"fields": sorted(updates)}, actor_id)
        return updated

    def get_user(self, organization_id: str, user_id: str) -> User:
        self.get_organization(organization_id)
        key = (organization_id, user_id)
        if key not in self.users:
            raise NotFoundError("User not found")
        return self.users[key]

    def require_role(self, organization_id: str, actor_id: str, allowed_roles: set[UserRole]) -> User:
        user = self.get_user(organization_id, actor_id)
        if user.role not in allowed_roles:
            raise PermissionDeniedError("User role is not allowed to perform this action.")
        return user

    def list_organizations(self) -> list[Organization]:
        return [organization for organization in self.organizations.values() if organization.status == "active"]

    def get_organization(self, organization_id: str) -> Organization:
        if organization_id not in self.organizations:
            raise NotFoundError("Organization not found")
        return self.organizations[organization_id]

    def update_organization(
        self,
        organization_id: str,
        payload: OrganizationUpdate,
        actor_id: str = "local_user",
    ) -> Organization:
        org = self.get_organization(organization_id)
        updates = payload.model_dump(exclude_unset=True)
        updated = org.model_copy(update={**updates, "updated_at": now_utc()})
        self.organizations[organization_id] = updated
        self.log(organization_id, "organization.updated", "organization", organization_id, {"fields": sorted(updates)}, actor_id)
        return updated

    def deactivate_organization(self, organization_id: str, actor_id: str = "local_user") -> Organization:
        self.require_role(organization_id, actor_id, {UserRole.owner})
        org = self.get_organization(organization_id)
        updated = org.model_copy(update={"status": "deactivated", "updated_at": now_utc()})
        self.organizations[organization_id] = updated
        self.log(organization_id, "organization.deactivated", "organization", organization_id, {}, actor_id)
        return updated

    def activate_organization(self, organization_id: str, actor_id: str = "local_user") -> Organization:
        self.require_role(organization_id, actor_id, {UserRole.owner})
        org = self.get_organization(organization_id)
        updated = org.model_copy(update={"status": "active", "updated_at": now_utc()})
        self.organizations[organization_id] = updated
        self.log(organization_id, "organization.activated", "organization", organization_id, {}, actor_id)
        return updated

    def delete_organization(self, organization_id: str, actor_id: str = "local_user") -> DeletionReceipt:
        self.require_role(organization_id, actor_id, {UserRole.owner})
        source_ids = [source.id for source in self.sources.values() if source.organization_id == organization_id]
        document_ids = [document.id for document in self.source_documents.values() if document.source_id in source_ids]
        chunk_ids = [chunk.id for chunk in self.chunks.values() if chunk.organization_id == organization_id]
        opportunity_ids = [item.id for item in self.opportunities.values() if item.organization_id == organization_id]
        brief_ids = [item.id for item in self.briefs.values() if item.organization_id == organization_id]
        draft_ids = [item.id for item in self.drafts.values() if item.organization_id == organization_id]
        event_ids = [item.id for item in self.calendar_events.values() if item.organization_id == organization_id]
        trend_ids = [item.id for item in self.trend_signals.values() if item.organization_id == organization_id]
        decision_ids = [item.id for item in self.decisions.values() if item.draft_id in draft_ids]
        memory_ids = [item.id for item in self.memory.values() if item.organization_id == organization_id]
        job_ids = [item.id for item in self.jobs.values() if item.organization_id == organization_id]
        model_call_ids = [item.id for item in self.model_call_logs if item.organization_id == organization_id]
        user_keys = [key for key in self.users if key[0] == organization_id]
        counts = {
            "sources": len(source_ids),
            "source_documents": len(document_ids),
            "source_chunks": len(chunk_ids),
            "opportunities": len(opportunity_ids),
            "briefs": len(brief_ids),
            "drafts": len(draft_ids),
            "calendar_events": len(event_ids),
            "trend_signals": len(trend_ids),
            "decisions": len(decision_ids),
            "memory": len(memory_ids),
            "jobs": len(job_ids),
            "model_calls": len(model_call_ids),
            "users": len(user_keys),
            "audit_logs": len([log for log in self.audit_logs if log.organization_id == organization_id]),
        }
        receipt = DeletionReceipt(
            organization_id=organization_id,
            deleted_by=actor_id,
            counts=counts,
            message="Organization data deleted from the local in-memory store.",
        )
        for collection in [
            self.organizations,
            self.profiles,
            self.sources,
            self.source_documents,
            self.chunks,
            self.opportunities,
            self.calendar_events,
            self.trend_signals,
            self.briefs,
            self.drafts,
            self.decisions,
            self.memory,
        ]:
            for entity_id, entity in list(collection.items()):
                if entity_id == organization_id or getattr(entity, "organization_id", None) == organization_id:
                    del collection[entity_id]
        for source_id in source_ids:
            self.source_raw_text.pop(source_id, None)
            self.source_hashes.pop(source_id, None)
            self.latest_document_by_source.pop(source_id, None)
        for key in user_keys:
            del self.users[key]
        self.approval_policies.pop(organization_id, None)
        self.linkedin_integrations.pop(organization_id, None)
        self.ai_provider_settings.pop(organization_id, None)
        for suggestion_id in [item.id for item in self.preference_suggestions.values() if item.organization_id == organization_id]:
            self.preference_suggestions.pop(suggestion_id, None)
        for document_id in document_ids:
            self.source_documents.pop(document_id, None)
        for job_id in job_ids:
            self.jobs.pop(job_id, None)
        self.job_logs = [log for log in self.job_logs if log.organization_id != organization_id]
        self.model_call_logs = [log for log in self.model_call_logs if log.organization_id != organization_id]
        self.audit_logs = [log for log in self.audit_logs if log.organization_id != organization_id]
        return receipt

    def update_profile(
        self,
        organization_id: str,
        payload: CompanyProfileUpdate,
        actor_id: str = "local_user",
    ) -> CompanyProfile:
        self.get_organization(organization_id)
        current = self.profiles[organization_id]
        updates = payload.model_dump(exclude_unset=True)
        profile = current.model_copy(update={**updates, "updated_at": now_utc()})
        self.profiles[organization_id] = profile
        self.log(organization_id, "profile.updated", "company_profile", organization_id, {"fields": sorted(updates)}, actor_id)
        return profile

    def get_linkedin_integration(self, organization_id: str) -> LinkedInIntegration:
        self.get_organization(organization_id)
        if organization_id not in self.linkedin_integrations:
            self.linkedin_integrations[organization_id] = LinkedInIntegration(organization_id=organization_id)
        return self.linkedin_integrations[organization_id]

    def update_linkedin_integration(
        self,
        organization_id: str,
        payload: LinkedInIntegrationUpdate,
        actor_id: str = "local_user",
    ) -> LinkedInIntegration:
        current = self.get_linkedin_integration(organization_id)
        integration = current.model_copy(update={**payload.model_dump(), "updated_at": now_utc()})
        self.linkedin_integrations[organization_id] = integration
        self.log(
            organization_id,
            "linkedin.integration_updated",
            "linkedin_integration",
            organization_id,
            {
                "selected_page_urn": integration.selected_page_urn,
                "selected_page_name": integration.selected_page_name,
                "oauth_status": integration.oauth_status,
                "publishing_enabled": integration.publishing_enabled,
                "permissions": integration.permissions,
            },
            actor_id,
        )
        return integration

    def create_source(self, organization_id: str, payload: SourceCreate, actor_id: str = "local_user") -> Source:
        self.require_role(organization_id, actor_id, {UserRole.owner, UserRole.editor})
        source = Source(
            organization_id=organization_id,
            source_type=payload.source_type,
            title=payload.title,
            uri=payload.uri,
            approval_status=payload.approval_status,
            freshness_days=payload.freshness_days,
        )
        self.sources[source.id] = source
        self.source_raw_text[source.id] = payload.raw_text
        self.log(organization_id, "source.created", "source", source.id, {"title": source.title}, actor_id)
        return source

    def update_source(self, source_id: str, payload: SourceUpdate, actor_id: str = "local_user") -> Source:
        source = self.get_source(source_id)
        self.require_role(source.organization_id, actor_id, {UserRole.owner, UserRole.editor})
        updates = payload.model_dump(exclude_unset=True)
        raw_text = updates.pop("raw_text", None)
        previous_status = source.approval_status
        updated = source.model_copy(update={**updates, "updated_at": now_utc()})
        self.sources[source.id] = updated
        if raw_text is not None:
            self.source_raw_text[source.id] = raw_text
        if "approval_status" in updates and updates["approval_status"] != previous_status:
            self.log(
                source.organization_id,
                "source.status_changed",
                "source",
                source.id,
                {"from": previous_status.value, "to": updates["approval_status"].value},
                actor_id,
            )
        else:
            self.log(source.organization_id, "source.updated", "source", source.id, {"fields": sorted(updates)}, actor_id)
        return updated

    def update_source_status(self, source_id: str, status: SourceStatus, actor_id: str = "local_user") -> Source:
        return self.update_source(source_id, SourceUpdate(approval_status=status), actor_id)

    def get_source(self, source_id: str) -> Source:
        if source_id not in self.sources:
            raise NotFoundError("Source not found")
        return self.sources[source_id]

    def get_source_detail(self, source_id: str) -> SourceDetail:
        source = self.get_source(source_id)
        chunk_count = len([chunk for chunk in self.chunks.values() if chunk.source_id == source.id])
        audit_logs = sorted(
            [log for log in self.audit_logs if log.entity_type == "source" and log.entity_id == source.id],
            key=lambda log: log.created_at,
            reverse=True,
        )
        return SourceDetail(
            source=source,
            raw_text=self.source_raw_text.get(source.id, ""),
            chunk_count=chunk_count,
            audit_logs=audit_logs,
        )

    def list_sources(self, organization_id: str) -> list[Source]:
        self.get_organization(organization_id)
        return [source for source in self.sources.values() if source.organization_id == organization_id]

    def ingest_source(self, source_id: str, actor_id: str = "local_user") -> list[SourceChunk]:
        source = self.get_source(source_id)
        self.require_role(source.organization_id, actor_id, {UserRole.owner, UserRole.editor})
        raw_text = self.source_raw_text[source.id]
        connector = self.source_connectors.get(source.source_type, self.source_connectors["manual_note"])
        extracted = connector.extract({"title": source.title, "raw_text": raw_text, "uri": source.uri})
        normalized_text = normalize_text(extracted.raw_text)
        digest = content_hash(normalized_text)
        if self.source_hashes.get(source.id) == digest:
            return [chunk for chunk in self.chunks.values() if chunk.source_id == source.id]
        for chunk_id, chunk in list(self.chunks.items()):
            if chunk.source_id == source.id:
                del self.chunks[chunk_id]
        document = SourceDocument(
            source_id=source.id,
            title=extracted.title,
            raw_text=raw_text,
            normalized_text=normalized_text,
            content_hash=digest,
            metadata=extracted.metadata,
        )
        self.source_documents[document.id] = document
        self.latest_document_by_source[source.id] = document.id
        created: list[SourceChunk] = []
        chunk_texts = split_chunks(normalized_text)
        embedding_provider = self.embedding_provider_for_org(source.organization_id)
        embeddings = embedding_provider.embed(chunk_texts)
        for index, text in enumerate(chunk_texts):
            chunk = SourceChunk(
                source_document_id=document.id,
                source_id=source.id,
                organization_id=source.organization_id,
                chunk_text=text,
                chunk_index=index,
                embedding=embeddings[index],
                metadata={"embedding_provider": embedding_provider.provider_name},
            )
            self.chunks[chunk.id] = chunk
            created.append(chunk)
        self.source_hashes[source.id] = digest
        source.last_ingested_at = now_utc()
        source.updated_at = now_utc()
        self.sources[source.id] = source
        self.log(source.organization_id, "source.ingested", "source", source.id, {"chunk_count": len(created)}, actor_id)
        return created

    def approved_chunks(self, organization_id: str) -> list[SourceChunk]:
        approved_source_ids = {
            source.id
            for source in self.sources.values()
            if source.organization_id == organization_id and source.approval_status == SourceStatus.approved
        }
        return [chunk for chunk in self.chunks.values() if chunk.organization_id == organization_id and chunk.source_id in approved_source_ids]

    def retrieve_chunks(self, organization_id: str, query: str, limit: int = 6) -> list[tuple[SourceChunk, Source, float]]:
        self.get_organization(organization_id)
        query_embedding = self.embedding_provider_for_org(organization_id).embed([query])[0]
        candidates = self.approved_chunks(organization_id)
        ranked: list[tuple[SourceChunk, Source, float]] = []
        for chunk in candidates:
            score = cosine_similarity(query_embedding, chunk.embedding)
            if score > 0:
                ranked.append((chunk, self.sources[chunk.source_id], round(score, 6)))
        ranked.sort(key=lambda item: item[2], reverse=True)
        return ranked[:limit]

    def knowledge_readiness(self, organization_id: str) -> KnowledgeReadiness:
        organization = self.get_organization(organization_id)
        profile = self.profiles[organization_id]
        sources = self.list_sources(organization_id)
        approved_sources = [source for source in sources if source.approval_status == SourceStatus.approved]
        chunks = self.approved_chunks(organization_id)
        now = now_utc()

        profile_checks = [
            bool(organization.name.strip()),
            bool(organization.website_url),
            bool(organization.industry),
            bool(organization.description),
            bool(organization.audience_summary or profile.audience),
            bool(profile.one_liner),
            bool(profile.content_pillars),
            bool(profile.voice_rules),
            bool(profile.approved_claims or profile.forbidden_claims),
        ]
        profile_score = round(sum(1 for item in profile_checks if item) / len(profile_checks), 3)

        if len(approved_sources) >= 3:
            source_score = 1.0
        elif len(approved_sources) == 2:
            source_score = 0.75
        elif len(approved_sources) == 1:
            source_score = 0.45
        else:
            source_score = 0.0

        stale_sources: list[Source] = []
        fresh_sources = 0
        for source in approved_sources:
            reference_at = source.last_ingested_at or source.updated_at
            age_days = max(0.0, (now - reference_at).total_seconds() / 86400)
            if age_days <= source.freshness_days:
                fresh_sources += 1
            else:
                stale_sources.append(source)
        freshness_score = round(fresh_sources / len(approved_sources), 3) if approved_sources else 0.0

        pillars = profile.content_pillars
        covered_pillars = 0
        for pillar in pillars:
            pillar_terms = terms(pillar)
            if pillar_terms and any(pillar_terms & terms(chunk.chunk_text) for chunk in chunks):
                covered_pillars += 1
        pillar_score = round(covered_pillars / len(pillars), 3) if pillars else 0.0

        approved_source_ids_with_chunks = {chunk.source_id for chunk in chunks}
        chunk_coverage = len(approved_source_ids_with_chunks) / len(approved_sources) if approved_sources else 0.0
        chunk_depth = min(1.0, len(chunks) / max(len(approved_sources) * 2, 1)) if approved_sources else 0.0
        retrieval_score = round((chunk_coverage * 0.65) + (chunk_depth * 0.35), 3) if approved_sources else 0.0

        signals = [
            self._readiness_signal(
                "profile",
                "Profile completeness",
                profile_score,
                f"{sum(1 for item in profile_checks if item)} of {len(profile_checks)} organization and voice fields are complete.",
            ),
            self._readiness_signal(
                "approved_sources",
                "Approved sources",
                source_score,
                f"{len(approved_sources)} approved source{'' if len(approved_sources) == 1 else 's'} are available.",
            ),
            self._readiness_signal(
                "freshness",
                "Source freshness",
                freshness_score,
                f"{fresh_sources} of {len(approved_sources)} approved source{'' if len(approved_sources) == 1 else 's'} are within their refresh window.",
            ),
            self._readiness_signal(
                "pillar_coverage",
                "Pillar coverage",
                pillar_score,
                f"{covered_pillars} of {len(pillars)} content pillar{'' if len(pillars) == 1 else 's'} have approved evidence.",
            ),
            self._readiness_signal(
                "retrieval",
                "Retrieval quality",
                retrieval_score,
                f"{len(chunks)} retrievable source chunk{'' if len(chunks) == 1 else 's'} are indexed for approved sources.",
            ),
        ]
        overall_score = round(
            profile_score * 0.22
            + source_score * 0.24
            + freshness_score * 0.18
            + pillar_score * 0.22
            + retrieval_score * 0.14,
            3,
        )
        if overall_score >= 0.9:
            status = "strong"
        elif overall_score >= 0.7:
            status = "ready"
        elif overall_score >= 0.4:
            status = "building"
        else:
            status = "blocked"

        recommendations: list[KnowledgeReadinessRecommendation] = []
        if profile_score < 0.7:
            recommendations.append(
                KnowledgeReadinessRecommendation(
                    title="Complete organization context",
                    detail="Add industry, audience, one-liner, voice rules, and claims so recommendations can match the company.",
                    action="settings",
                    priority="high",
                )
            )
        if len(approved_sources) == 0:
            recommendations.append(
                KnowledgeReadinessRecommendation(
                    title="Add the first approved source",
                    detail="Opportunities need approved company knowledge before the system can safely rank or draft them.",
                    action="sources",
                    priority="high",
                )
            )
        elif len(approved_sources) < 3:
            recommendations.append(
                KnowledgeReadinessRecommendation(
                    title="Add more source variety",
                    detail="A mix of product, proof, positioning, and policy sources improves ranking accuracy.",
                    action="sources",
                    priority="medium",
                )
            )
        if stale_sources:
            recommendations.append(
                KnowledgeReadinessRecommendation(
                    title="Refresh stale sources",
                    detail=f"{len(stale_sources)} approved source{'' if len(stale_sources) == 1 else 's'} are outside their refresh window.",
                    action="refresh_sources",
                    priority="medium",
                )
            )
        if pillars and covered_pillars < len(pillars):
            recommendations.append(
                KnowledgeReadinessRecommendation(
                    title="Cover every content pillar",
                    detail="Add approved evidence for pillars that currently have no retrievable source chunks.",
                    action="sources",
                    priority="medium",
                )
            )
        if approved_sources and retrieval_score < 0.7:
            recommendations.append(
                KnowledgeReadinessRecommendation(
                    title="Improve retrieval depth",
                    detail="Refresh or expand approved sources so each active source has indexed chunks.",
                    action="refresh_sources",
                    priority="medium",
                )
            )

        return KnowledgeReadiness(
            organization_id=organization_id,
            overall_score=overall_score,
            status=status,
            profile_completeness=profile_score,
            approved_source_count=len(approved_sources),
            stale_source_count=len(stale_sources),
            covered_pillar_count=covered_pillars,
            total_pillar_count=len(pillars),
            retrievable_chunk_count=len(chunks),
            signals=signals,
            recommendations=recommendations[:4],
        )

    def _readiness_signal(self, key: str, label: str, score: float, detail: str) -> KnowledgeReadinessSignal:
        if score >= 0.85:
            status = "strong"
        elif score >= 0.65:
            status = "ready"
        elif score > 0:
            status = "building"
        else:
            status = "blocked"
        return KnowledgeReadinessSignal(key=key, label=label, score=round(score, 3), status=status, detail=detail)

    def generate_opportunities(self, organization_id: str, actor_id: str = "local_user") -> list[ContentOpportunity]:
        profile = self.profiles[organization_id]
        sources = [source for source in self.list_sources(organization_id) if source.approval_status == SourceStatus.approved]
        chunks = self.approved_chunks(organization_id)
        fallback_opportunities = self.opportunity_generator.generate(
            profile,
            sources,
            chunks,
            self.list_memory(organization_id),
            self.list_calendar_events(organization_id),
            self.list_trend_signals(organization_id),
        )
        model_output, model_log = self.generate_structured_safely(
            organization_id,
            actor_id,
            self._opportunity_prompt(profile, sources, chunks),
            prompt_versions.version("opportunity_generation"),
            OpportunityRecommendationSet,
            [source.id for source in sources],
            {"operation": "opportunity_generation", "source_count": len(sources), "chunk_count": len(chunks)},
        )
        model_opportunities: list[ContentOpportunity] = []
        if model_output and model_log.provider != "deterministic":
            model_opportunities = self._opportunities_from_model_recommendations(
                organization_id,
                model_output,
                sources,
                chunks,
                model_log.provider,
            )
        if model_log.provider != "deterministic" and model_log.status == ModelCallStatus.succeeded:
            opportunities = model_opportunities
        else:
            opportunities = self._merge_opportunities(model_opportunities, fallback_opportunities)
        for opportunity in opportunities:
            opportunity.metadata["model_call_id"] = model_log.id
            opportunity.metadata["model_provider"] = model_log.provider
            opportunity.metadata["model_prompt_version"] = model_log.prompt_version
            if model_output and model_output.recommendations:
                opportunity.metadata["model_suggestion"] = model_output.recommendations[0].model_dump(mode="json")
            self.opportunities[opportunity.id] = opportunity
        self.log(organization_id, "opportunities.generated", "organization", organization_id, {"count": len(opportunities)}, actor_id)
        return opportunities

    def _opportunities_from_model_recommendations(
        self,
        organization_id: str,
        recommendation_set: OpportunityRecommendationSet,
        sources: list[Source],
        chunks: list[SourceChunk],
        provider_name: str,
    ) -> list[ContentOpportunity]:
        opportunities: list[ContentOpportunity] = []
        source_ids = {source.id for source in sources}
        for recommendation in recommendation_set.recommendations[:5]:
            if self._is_generic_model_recommendation(recommendation):
                continue
            query = " ".join([recommendation.title, recommendation.summary, recommendation.why_now])
            evidence = [chunk for chunk in lexical_retrieve_chunks(query, chunks, limit=8) if chunk.source_id in source_ids]
            evidence = self._prioritize_model_evidence(query, evidence, sources)[:4]
            if not evidence:
                continue
            evidence_fit, shared_terms = self._model_recommendation_evidence_fit(recommendation, evidence)
            if evidence_fit < 0.24 or len(shared_terms) < 3:
                continue
            recommendation_title = self._sanitize_model_title(recommendation.title.strip(), evidence)
            recommendation_summary = recommendation.summary.strip()
            recommendation_reason = self._sanitize_model_why_now(recommendation.why_now.strip(), evidence)
            selected_source_ids = sorted({chunk.source_id for chunk in evidence})
            freshness = self.opportunity_generator.freshness_scorer.score(sources, selected_source_ids)
            timeliness = self._model_timeliness_score(selected_source_ids, sources)
            relevance = min(0.98, max(0.55, 0.5 + len(evidence) * 0.08 + recommendation.confidence * 0.22))
            confidence = min(0.97, max(0.55, recommendation.confidence))
            focus = self._model_focus_score(recommendation)
            rank_score = round(min(1.0, relevance * 0.34 + confidence * 0.16 + freshness * 0.18 + timeliness * 0.22 + focus * 0.1), 3)
            opportunities.append(
                ContentOpportunity(
                    organization_id=organization_id,
                    title=recommendation_title,
                    summary=recommendation_summary,
                    reason_today=recommendation_reason,
                    source_ids=selected_source_ids,
                    freshness_score=freshness,
                    relevance_score=round(relevance, 3),
                    confidence_score=round(confidence, 3),
                    metadata={
                        "generation_basis": "model_recommendation",
                        "model_provider": provider_name,
                        "model_confidence": recommendation.confidence,
                        "evidence_chunk_ids": [chunk.id for chunk in evidence],
                        "rank_score": rank_score,
                        "rank_signals": {
                            "source_support": round(min(1.0, len(evidence) / 4), 3),
                            "evidence_fit": round(evidence_fit, 3),
                            "date_relevance": timeliness,
                            "trend_relevance": 0.0,
                            "audience_fit": round(relevance, 3),
                            "tone_fit": round(confidence, 3),
                            "freshness": freshness,
                            "performance_fit": 0.0,
                            "duplicate_penalty": 0.0,
                            "focus": focus,
                            "rank_score": rank_score,
                        },
                    },
                )
            )
        return sorted(opportunities, key=lambda opportunity: float(opportunity.metadata.get("rank_score", 0)), reverse=True)

    def _model_recommendation_evidence_fit(
        self,
        recommendation: OpportunityRecommendation,
        evidence: list[SourceChunk],
    ) -> tuple[float, set[str]]:
        query_text = " ".join([recommendation.title, recommendation.summary, recommendation.why_now])
        query_terms = self._meaningful_opportunity_terms(query_text)
        title_terms = self._meaningful_opportunity_terms(recommendation.title)
        evidence_terms = self._meaningful_opportunity_terms(" ".join(chunk.chunk_text for chunk in evidence))
        if not query_terms or not evidence_terms:
            return 0.0, set()
        shared_terms = query_terms & evidence_terms
        title_shared_terms = title_terms & evidence_terms
        query_fit = len(shared_terms) / max(len(query_terms), 1)
        title_fit = len(title_shared_terms) / max(len(title_terms), 1) if title_terms else 0.0
        fit = max(query_fit, (query_fit * 0.65) + (title_fit * 0.35))
        return round(min(1.0, fit), 3), shared_terms

    def _meaningful_opportunity_terms(self, text: str) -> set[str]:
        generic_terms = {
            "approved",
            "artifact",
            "brand",
            "building",
            "claim",
            "claims",
            "communication",
            "company",
            "concrete",
            "content",
            "context",
            "current",
            "draft",
            "evidence",
            "explain",
            "fresh",
            "grounded",
            "human",
            "knowledge",
            "message",
            "opportunity",
            "organization",
            "post",
            "proof",
            "public",
            "publish",
            "published",
            "reason",
            "review",
            "reviewable",
            "source",
            "sources",
            "story",
            "team",
            "timely",
            "today",
            "update",
            "use",
            "using",
            "worth",
            "work",
        }
        return {term for term in terms(text) if term not in generic_terms and len(term) >= 4}

    def _sanitize_model_title(self, title: str, evidence: list[SourceChunk]) -> str:
        cleaned = title
        evidence_text = " ".join(chunk.chunk_text for chunk in evidence).lower()
        if "launch" in cleaned.lower() and "launch" not in evidence_text:
            if any(term in evidence_text for term in ["active product", "being built", "product work"]):
                return "Share active product work from approved sources"
            return cleaned.replace("Launch", "Update").replace("launch", "update")
        return cleaned

    def _model_timeliness_score(self, source_ids: list[str], sources: list[Source]) -> float:
        selected_titles = " ".join(source.title for source in sources if source.id in source_ids).lower()
        if "published blog today" in selected_titles:
            return 1.0
        if "vouch product" in selected_titles:
            return 0.95
        if "active products" in selected_titles:
            return 0.75
        return 0.2

    def _model_focus_score(self, recommendation: OpportunityRecommendation) -> float:
        combined = " ".join([recommendation.title, recommendation.summary, recommendation.why_now]).lower()
        if "vouch" in combined:
            return 1.0
        if "product judgment" in combined or "blog" in combined:
            return 0.95
        if "meaningful problems" in combined:
            return 0.75
        return 0.25

    def _sanitize_model_why_now(self, why_now: str, evidence: list[SourceChunk]) -> str:
        evidence_text = " ".join(chunk.chunk_text for chunk in evidence).lower()
        lowered = why_now.lower()
        if (
            "http://" in lowered
            or "https://" in lowered
            or "<" in why_now
            or ">" in why_now
            or "fresh off the press" in lowered
            or "new today" in lowered
        ):
            if "published" in evidence_text or "blog" in evidence_text:
                return "Approved sources identify a timely published post worth turning into a public update."
            if any(term in evidence_text for term in ["active product", "being built", "product work"]):
                return (
                    "Approved sources identify active product work as a timely proof point "
                    "for source-grounded, human-reviewed company communication."
                )
        if lowered.strip() == now_utc().date().isoformat():
            if "published" in evidence_text or "blog" in evidence_text:
                return "Approved sources identify a timely published post worth turning into a public update."
            if any(term in evidence_text for term in ["active product", "being built", "product work"]):
                return "Approved sources identify active product work as timely public proof."
        if "launch" in lowered and not any(term in evidence_text for term in ["launch", "launched", "release", "released"]):
            if any(term in evidence_text for term in ["active product", "being built", "product work"]):
                return (
                    "Approved sources identify active product work, making it a timely proof point "
                    "for the organization's public story."
                )
            return "Approved sources identify this as active work, making it a timely public proof point."
        unsupported_timing_terms = ["milestone", "recently reached", "this week", "new labs"]
        unsupported_impact_terms = ["impact it", "impact it's", "real-world impact", "having on real-world"]
        if any(term in lowered for term in unsupported_timing_terms) and not any(
            term in evidence_text for term in ["milestone", "this week", "recently reached"]
        ):
            if any(term in evidence_text for term in ["active product", "being built", "product work"]):
                return (
                    "Approved sources identify active product work as a proof artifact for "
                    "source-grounded, human-reviewed company communication."
                )
            if "labs" in evidence_text:
                return "Approved sources identify the lab as public proof of the organization's learning approach."
            return "Approved sources identify this as active work worth turning into a public proof point."
        if any(term in lowered for term in unsupported_impact_terms):
            return "Approved sources support this as a relevant public proof point without claiming external results."
        if "shining example" in lowered or "join us" in lowered:
            if any(term in evidence_text for term in ["active product", "being built", "product work"]):
                return (
                    "Approved sources connect the active product work to product judgment, production readiness, "
                    "source grounding, and human-reviewed company communication."
                )
        return why_now

    def _is_generic_model_recommendation(self, recommendation: OpportunityRecommendation) -> bool:
        combined = " ".join([recommendation.title, recommendation.summary, recommendation.why_now]).lower()
        generic_phrases = [
            "source-backed communication opportunity",
            "approved source context is available",
            "turn approved context",
            "use approved context",
        ]
        return any(phrase in combined for phrase in generic_phrases)

    def _prioritize_model_evidence(
        self,
        query: str,
        evidence: list[SourceChunk],
        sources: list[Source],
    ) -> list[SourceChunk]:
        source_by_id = {source.id: source for source in sources}
        query_terms = terms(query) - {"quainy", "source", "context", "public", "content"}

        def evidence_key(chunk: SourceChunk) -> tuple[float, int]:
            source = source_by_id.get(chunk.source_id)
            source_terms = terms(source.title if source else "") - {"quainy", "source", "context", "public", "content"}
            title_overlap = len(query_terms & source_terms) / max(len(source_terms), 1)
            chunk_overlap = len(query_terms & terms(chunk.chunk_text)) / max(len(query_terms), 1)
            return (title_overlap * 2.0 + chunk_overlap, -chunk.chunk_index)

        return sorted(evidence, key=evidence_key, reverse=True)

    def _merge_opportunities(
        self,
        primary: list[ContentOpportunity],
        fallback: list[ContentOpportunity],
        limit: int = 12,
    ) -> list[ContentOpportunity]:
        merged: list[ContentOpportunity] = []
        seen: set[str] = set()
        for opportunity in [*primary, *fallback]:
            key_terms = terms(opportunity.title)
            key = " ".join(sorted(key_terms)) or opportunity.title.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(opportunity)
            if len(merged) >= limit:
                break
        return merged

    def create_calendar_event(
        self,
        organization_id: str,
        payload: CalendarEventCreate,
        actor_id: str = "local_user",
    ) -> CalendarEvent:
        self.require_role(organization_id, actor_id, {UserRole.owner, UserRole.editor})
        event = CalendarEvent(organization_id=organization_id, **payload.model_dump())
        self.calendar_events[event.id] = event
        self.log(organization_id, "calendar_event.created", "calendar_event", event.id, {"event_type": event.event_type}, actor_id)
        return event

    def list_calendar_events(self, organization_id: str) -> list[CalendarEvent]:
        self.get_organization(organization_id)
        return sorted(
            [event for event in self.calendar_events.values() if event.organization_id == organization_id],
            key=lambda event: event.event_date,
        )

    def create_trend_signal(
        self,
        organization_id: str,
        payload: TrendSignalCreate,
        actor_id: str = "local_user",
    ) -> TrendSignal:
        self.require_role(organization_id, actor_id, {UserRole.owner, UserRole.editor})
        trend = TrendSignal(organization_id=organization_id, **payload.model_dump())
        self.trend_signals[trend.id] = trend
        self.log(organization_id, "trend_signal.created", "trend_signal", trend.id, {"industry": trend.industry}, actor_id)
        return trend

    def list_trend_signals(self, organization_id: str) -> list[TrendSignal]:
        self.get_organization(organization_id)
        return sorted(
            [trend for trend in self.trend_signals.values() if trend.organization_id == organization_id],
            key=lambda trend: trend.created_at,
            reverse=True,
        )

    def generate_trend_opportunities(self, organization_id: str, actor_id: str = "local_user") -> list[ContentOpportunity]:
        self.get_organization(organization_id)
        sources = [source for source in self.list_sources(organization_id) if source.approval_status == SourceStatus.approved]
        opportunities = self.trend_opportunity_generator.generate(
            organization_id,
            self.list_trend_signals(organization_id),
            sources,
            self.approved_chunks(organization_id),
            self.list_calendar_events(organization_id),
        )
        for opportunity in opportunities:
            self.opportunities[opportunity.id] = opportunity
        self.log(organization_id, "trend_opportunities.generated", "organization", organization_id, {"count": len(opportunities)}, actor_id)
        return opportunities

    def create_brief(self, opportunity_id: str, actor_id: str = "local_user") -> ContentBrief:
        opportunity = self.get_opportunity(opportunity_id)
        profile = self.profiles[opportunity.organization_id]
        chunks = self.approved_chunks(opportunity.organization_id)
        brief = build_brief(profile, opportunity, chunks)
        model_output, model_log = self.generate_structured_safely(
            opportunity.organization_id,
            actor_id,
            self._brief_prompt(profile, opportunity, chunks),
            prompt_versions.version("brief_builder"),
            BriefRecommendation,
            opportunity.source_ids,
            {"operation": "brief_builder", "opportunity_id": opportunity.id},
        )
        brief.builder_metadata.update(
            {
                "model_call_id": model_log.id,
                "model_provider": model_log.provider,
                "model_prompt_version": model_log.prompt_version,
            }
        )
        if model_output:
            brief.builder_metadata["model_recommendation"] = model_output.model_dump(mode="json")
        self.briefs[brief.id] = brief
        self.log(brief.organization_id, "brief.created", "brief", brief.id, actor_id=actor_id)
        return brief

    def generate_drafts(
        self,
        brief_id: str,
        platform: str = "linkedin",
        content_type: str = "company_post",
        actor_id: str = "local_user",
    ) -> list[Draft]:
        brief = self.get_brief(brief_id)
        opportunity = self.get_opportunity(brief.opportunity_id)
        adapter = self.get_format_adapter(platform, content_type)
        drafts = generate_drafts(
            self.profiles[brief.organization_id],
            brief,
            opportunity,
            self.approved_chunks(brief.organization_id),
            self.list_memory(brief.organization_id),
            adapter,
        )
        model_output, model_log = self.generate_structured_safely(
            brief.organization_id,
            actor_id,
            self._draft_prompt(self.profiles[brief.organization_id], brief, opportunity, adapter.generation_spec(brief).model_dump(mode="json")),
            prompt_versions.version("draft_generation"),
            DraftRecommendationSet,
            brief.source_ids,
            {
                "operation": "draft_generation",
                "brief_id": brief.id,
                "platform": platform,
                "content_type": content_type,
            },
        )
        for draft_index, draft in enumerate(drafts):
            draft.generation_metadata["model_provider"] = model_log.provider
            draft.generation_metadata["model"] = model_log.model
            draft.generation_metadata["model_call_id"] = model_log.id
            draft.generation_metadata["model_prompt_version"] = model_log.prompt_version
            draft.generation_metadata["embedding_provider"] = self.embedding_provider_for_org(brief.organization_id).provider_name
            if model_output and model_output.variants:
                recommendation = model_output.variants[min(draft_index, len(model_output.variants) - 1)]
                draft.generation_metadata["model_recommendation"] = recommendation.model_dump(mode="json")
                if model_log.provider != "deterministic":
                    validated = self._validated_model_draft_variant(
                        recommendation.model_dump(mode="json"),
                        adapter,
                        self.profiles[brief.organization_id],
                        brief,
                        opportunity,
                    )
                    if validated:
                        draft.hook = validated["hook"]
                        draft.body = validated["body"]
                        draft.hashtags = validated["hashtags"]
                        draft.claims = check_claims(draft.body, self.approved_chunks(draft.organization_id))
                        draft.duplicate_report = duplicate_check(draft.body, self.list_memory(draft.organization_id))
                        draft.risk_report = risk_check(draft.body, self.profiles[draft.organization_id], draft.claims, draft.duplicate_report, opportunity)
                        draft.quality_report = adapter.quality_checks(draft.body, self.profiles[brief.organization_id], brief)
                        draft.source_map = {claim.text: claim.supporting_chunk_ids for claim in draft.claims if claim.supporting_chunk_ids}
                        draft.generation_metadata["body_source"] = "model_recommendation"
                        draft.generation_metadata["model_sanitization"] = validated["notes"]
                    else:
                        draft.generation_metadata["body_source"] = "adapter_render"
                        draft.generation_metadata["model_rejection_reason"] = "Model draft was generic, ungrounded, or not valid for the requested platform format."
                else:
                    draft.generation_metadata["body_source"] = "adapter_render"
            self.drafts[draft.id] = draft
        self.log(brief.organization_id, "drafts.generated", "brief", brief.id, {"count": len(drafts)}, actor_id)
        return drafts

    def regenerate_drafts_for_draft(self, draft_id: str, actor_id: str = "local_user") -> list[Draft]:
        draft = self.get_draft(draft_id)
        drafts = self.generate_drafts(draft.content_brief_id, draft.platform, draft.content_type, actor_id)
        self.log(
            draft.organization_id,
            "draft.regenerated",
            "draft",
            draft.id,
            {"count": len(drafts), "new_draft_ids": [new_draft.id for new_draft in drafts]},
            actor_id,
        )
        return drafts

    def update_draft_body(self, draft_id: str, body: str, actor_id: str = "local_user") -> Draft:
        draft = self.get_draft(draft_id)
        brief = self.get_brief(draft.content_brief_id)
        opportunity = self.get_opportunity(brief.opportunity_id)
        adapter = self.get_format_adapter(draft.platform, draft.content_type)
        draft.body = body
        draft.claims = check_claims(body, self.approved_chunks(draft.organization_id))
        draft.duplicate_report = duplicate_check(body, self.list_memory(draft.organization_id))
        draft.risk_report = risk_check(body, self.profiles[draft.organization_id], draft.claims, draft.duplicate_report, opportunity)
        draft.quality_report = adapter.quality_checks(body, self.profiles[draft.organization_id], brief)
        draft.updated_at = now_utc()
        self.drafts[draft.id] = draft
        self.log(draft.organization_id, "draft.edited", "draft", draft.id, actor_id=actor_id)
        return draft

    def approve_draft(self, draft_id: str, payload: ReviewDecisionCreate, actor_id: str = "local_user") -> ApprovalDecision:
        draft = self.get_draft(draft_id)
        self.require_role(draft.organization_id, actor_id, {UserRole.owner, UserRole.reviewer})
        if payload.edited_body:
            draft = self.update_draft_body(draft_id, payload.edited_body, actor_id)
        policy = self.get_approval_policy(draft.organization_id)
        high_risk_claims = high_risk_unsupported_claims(draft.claims)
        if high_risk_claims and not payload.override_reason:
            raise ApprovalBlockedError("Unsupported factual claims must be resolved or explicitly overridden before approval.")
        if high_risk_claims and not policy.allow_risk_override:
            raise ApprovalBlockedError("Risk overrides are disabled for this workspace.")

        decision = ApprovalDecision(
            draft_id=draft.id,
            decision=Decision.approve,
            reviewer_id=actor_id,
            **payload.model_dump(),
        )
        self.decisions[decision.id] = decision
        if payload.override_reason:
            self.log(
                draft.organization_id,
                "draft.risk_override",
                "draft",
                draft.id,
                {
                    "reviewer_id": actor_id,
                    "override_reason": payload.override_reason,
                    "unsupported_claim_count": len(high_risk_claims),
                },
                actor_id,
            )

        approval_progress = self.approval_progress(draft.id)
        draft.approval_metadata = approval_progress
        if approval_progress["approved_reviewer_count"] < policy.required_reviewer_count:
            draft.status = DraftStatus.pending_approval
            draft.updated_at = now_utc()
            self.drafts[draft.id] = draft
            self.log(
                draft.organization_id,
                "draft.approval_recorded",
                "draft",
                draft.id,
                approval_progress,
                actor_id,
            )
            return decision

        draft.status = DraftStatus.approved
        draft.updated_at = now_utc()
        self.drafts[draft.id] = draft
        memory_id = self._memory_id_for_draft(draft)
        self.memory[memory_id] = PostMemory(
            id=memory_id,
            organization_id=draft.organization_id,
            platform=draft.platform,
            content_type=draft.content_type,
            final_body=draft.body,
            source_draft_id=draft.id,
            topic_labels=idea_fingerprint(draft.body).split()[:5],
            idea_fingerprint=idea_fingerprint(draft.body),
            approved_at=now_utc(),
        )
        self.log(draft.organization_id, "draft.approved", "draft", draft.id, approval_progress, actor_id)
        return decision

    def reject_draft(
        self,
        draft_id: str,
        payload: ReviewDecisionCreate,
        actor_id: str = "local_user",
    ) -> ApprovalDecision:
        if not payload.reason or not payload.reason.strip():
            raise ReviewDecisionRequiredError("Rejecting a draft requires a reason.")
        draft = self.get_draft(draft_id)
        if payload.edited_body:
            draft = self.update_draft_body(draft_id, payload.edited_body, actor_id)
        draft.status = DraftStatus.rejected
        draft.updated_at = now_utc()
        self.drafts[draft.id] = draft
        decision = ApprovalDecision(draft_id=draft.id, decision=Decision.reject, **payload.model_dump())
        self.decisions[decision.id] = decision
        self.log(draft.organization_id, "draft.rejected", "draft", draft.id, {"reason": payload.reason}, actor_id)
        return decision

    def export_draft(self, draft_id: str, actor_id: str = "local_user") -> ApprovalDecision:
        draft = self.get_draft(draft_id)
        memory_id = self._memory_id_for_draft(draft)
        memory = self.memory.get(memory_id)
        policy = self.get_approval_policy(draft.organization_id)
        if policy.require_approval_before_export and (memory is None or memory.approved_at is None):
            raise ApprovalBlockedError("Draft must complete required approval before export.")
        draft.status = DraftStatus.exported
        draft.exported_at = now_utc()
        draft.updated_at = now_utc()
        self.drafts[draft.id] = draft
        if memory_id not in self.memory:
            self.memory[memory_id] = PostMemory(
                id=memory_id,
                organization_id=draft.organization_id,
                platform=draft.platform,
                content_type=draft.content_type,
                final_body=draft.body,
                source_draft_id=draft.id,
                topic_labels=idea_fingerprint(draft.body).split()[:5],
                idea_fingerprint=idea_fingerprint(draft.body),
                exported_at=now_utc(),
            )
        else:
            self.memory[memory_id].exported_at = now_utc()
        decision = ApprovalDecision(draft_id=draft.id, decision=Decision.export)
        self.decisions[decision.id] = decision
        self.log(draft.organization_id, "draft.exported", "draft", draft.id, actor_id=actor_id)
        return decision

    def schedule_draft(
        self,
        draft_id: str,
        scheduled_for,
        reason: str | None = None,
        actor_id: str = "local_user",
    ) -> ApprovalDecision:
        draft = self.get_draft(draft_id)
        draft.status = DraftStatus.scheduled
        draft.scheduled_for = scheduled_for
        draft.updated_at = now_utc()
        self.drafts[draft.id] = draft
        decision = ApprovalDecision(draft_id=draft.id, decision=Decision.schedule, reason=reason)
        self.decisions[decision.id] = decision
        self.log(
            draft.organization_id,
            "draft.scheduled",
            "draft",
            draft.id,
            {"scheduled_for": scheduled_for.isoformat(), "reason": reason},
            actor_id,
        )
        return decision

    def publish_draft_to_linkedin(
        self,
        draft_id: str,
        payload: DraftPublishCreate,
        actor_id: str = "local_user",
    ) -> PublishResult:
        draft = self.get_draft(draft_id)
        if draft.platform != "linkedin" or draft.content_type != "company_post":
            raise ApprovalBlockedError("Only LinkedIn company post drafts can be published through the LinkedIn adapter.")
        memory_id = self._memory_id_for_draft(draft)
        memory = self.memory.get(memory_id)
        policy = self.get_approval_policy(draft.organization_id)
        if policy.require_approval_before_publish and (memory is None or memory.approved_at is None):
            raise ApprovalBlockedError("Draft must be approved before publishing.")

        integration = self.get_linkedin_integration(draft.organization_id)
        page_urn = payload.page_urn or integration.selected_page_urn
        page_name = payload.page_name or integration.selected_page_name
        if not page_urn:
            raise ApprovalBlockedError("Select a LinkedIn company page before publishing.")

        result = self.linkedin_publisher.publish_company_post(draft, payload, page_urn, page_name)
        draft.publish_result = result.model_dump(mode="json")
        draft.updated_at = now_utc()

        if result.status == "published":
            draft.status = DraftStatus.published
            draft.published_at = result.published_at or now_utc()
            memory.published_at = draft.published_at
            self.memory[memory_id] = memory
            decision = ApprovalDecision(draft_id=draft.id, decision=Decision.publish, reason=payload.reason)
            self.decisions[decision.id] = decision
            self.log(
                draft.organization_id,
                "draft.published",
                "draft",
                draft.id,
                {
                    "provider": result.provider,
                    "page_urn": result.page_urn,
                    "page_name": result.page_name,
                    "provider_post_id": result.provider_post_id,
                    "published_url": result.published_url,
                },
                actor_id,
            )
        else:
            self.log(
                draft.organization_id,
                "draft.publish_failed",
                "draft",
                draft.id,
                {
                    "provider": result.provider,
                    "page_urn": result.page_urn,
                    "page_name": result.page_name,
                    "failure_reason": result.failure_reason,
                },
                actor_id,
            )

        self.drafts[draft.id] = draft
        return result

    def get_opportunity(self, opportunity_id: str) -> ContentOpportunity:
        if opportunity_id not in self.opportunities:
            raise NotFoundError("Opportunity not found")
        return self.opportunities[opportunity_id]

    def get_brief(self, brief_id: str) -> ContentBrief:
        if brief_id not in self.briefs:
            raise NotFoundError("Brief not found")
        return self.briefs[brief_id]

    def get_draft(self, draft_id: str) -> Draft:
        if draft_id not in self.drafts:
            raise NotFoundError("Draft not found")
        return self.drafts[draft_id]

    def list_drafts_for_brief(self, brief_id: str) -> list[Draft]:
        self.get_brief(brief_id)
        return sorted(
            [draft for draft in self.drafts.values() if draft.content_brief_id == brief_id],
            key=lambda draft: draft.updated_at,
            reverse=True,
        )

    def list_draft_decisions(self, draft_id: str) -> list[ApprovalDecision]:
        self.get_draft(draft_id)
        return sorted(
            [decision for decision in self.decisions.values() if decision.draft_id == draft_id],
            key=lambda decision: decision.created_at,
        )

    def approval_progress(self, draft_id: str) -> dict[str, object]:
        draft = self.get_draft(draft_id)
        policy = self.get_approval_policy(draft.organization_id)
        reviewers = sorted(
            {
                decision.reviewer_id or "unknown"
                for decision in self.list_draft_decisions(draft_id)
                if decision.decision == Decision.approve
            }
        )
        remaining = max(policy.required_reviewer_count - len(reviewers), 0)
        return {
            "required_reviewer_count": policy.required_reviewer_count,
            "approved_reviewer_count": len(reviewers),
            "remaining_reviewer_count": remaining,
            "approved_reviewer_ids": reviewers,
            "complete": remaining == 0,
        }

    def list_opportunities(self, organization_id: str) -> list[ContentOpportunity]:
        return [
            opportunity
            for opportunity in self.opportunities.values()
            if opportunity.organization_id == organization_id and opportunity.status != "dismissed"
        ]

    def dismiss_opportunity(
        self,
        opportunity_id: str,
        payload: ReviewDecisionCreate | None = None,
        actor_id: str = "local_user",
    ) -> ContentOpportunity:
        opportunity = self.get_opportunity(opportunity_id)
        opportunity.status = "dismissed"
        opportunity.metadata["dismissed_at"] = now_utc().isoformat()
        opportunity.metadata["dismissed_by"] = actor_id
        if payload and payload.reason:
            opportunity.metadata["dismissal_reason"] = payload.reason
        self.opportunities[opportunity.id] = opportunity
        self.log(
            opportunity.organization_id,
            "opportunity.dismissed",
            "opportunity",
            opportunity.id,
            {"reason": payload.reason if payload else None},
            actor_id,
        )
        return opportunity

    def list_memory(self, organization_id: str) -> list[PostMemory]:
        return [post for post in self.memory.values() if post.organization_id == organization_id]

    def get_memory(self, memory_id: str) -> PostMemory:
        if memory_id not in self.memory:
            raise NotFoundError("Post memory not found")
        return self.memory[memory_id]

    def list_content_artifacts(self, organization_id: str) -> list[ContentArtifact]:
        self.get_organization(organization_id)
        artifacts: list[ContentArtifact] = []
        for opportunity in self.opportunities.values():
            if opportunity.organization_id != organization_id:
                continue
            artifacts.append(
                ContentArtifact(
                    id=opportunity.id,
                    kind="opportunity",
                    title=opportunity.title,
                    status=opportunity.status,
                    excerpt=opportunity.reason_today,
                    source_count=len(opportunity.source_ids),
                    risk_count=len(opportunity.metadata.get("warnings", [])) if isinstance(opportunity.metadata.get("warnings"), list) else 0,
                    updated_at=opportunity.created_at,
                )
            )
        for brief in self.briefs.values():
            if brief.organization_id != organization_id:
                continue
            artifacts.append(
                ContentArtifact(
                    id=brief.id,
                    kind="brief",
                    title=brief.objective,
                    status="source-backed",
                    excerpt=brief.key_message,
                    source_count=len(brief.source_ids),
                    risk_count=len(brief.risks),
                    updated_at=brief.created_at,
                )
            )
        for draft in self.drafts.values():
            if draft.organization_id != organization_id:
                continue
            artifacts.append(
                ContentArtifact(
                    id=draft.id,
                    kind="draft",
                    title=draft.hook or draft.body[:90],
                    platform=draft.platform,
                    content_type=draft.content_type,
                    status=draft.status,
                    excerpt=draft.body[:260],
                    source_count=len(draft.source_ids),
                    risk_count=len(draft.risk_report),
                    updated_at=draft.updated_at,
                    scheduled_for=draft.scheduled_for,
                    published_at=draft.published_at,
                )
            )
        for memory in self.list_memory(organization_id):
            artifacts.append(
                ContentArtifact(
                    id=memory.id,
                    kind="memory",
                    title=memory.final_body[:90],
                    platform=memory.platform,
                    content_type=memory.content_type,
                    status="published" if memory.published_at else "approved",
                    excerpt=memory.final_body[:260],
                    source_count=0,
                    risk_count=0,
                    updated_at=memory.published_at or memory.exported_at or memory.approved_at or now_utc(),
                    published_at=memory.published_at,
                )
            )
        return sorted(artifacts, key=lambda artifact: artifact.updated_at, reverse=True)

    def generate_preference_suggestions(self, organization_id: str, actor_id: str = "local_user") -> list[PreferenceSuggestion]:
        self.get_organization(organization_id)
        draft_ids = {draft.id for draft in self.drafts.values() if draft.organization_id == organization_id}
        decisions = [decision for decision in self.decisions.values() if decision.draft_id in draft_ids]
        suggestions = self.preference_learning.build_suggestions(organization_id, decisions)
        for suggestion in suggestions:
            existing = self._find_matching_preference_suggestion(suggestion)
            if existing:
                existing.evidence = suggestion.evidence
                existing.confidence = suggestion.confidence
                self.preference_suggestions[existing.id] = existing
            else:
                self.preference_suggestions[suggestion.id] = suggestion
        self.log(organization_id, "preferences.suggested", "organization", organization_id, {"count": len(suggestions)}, actor_id)
        return self.list_preference_suggestions(organization_id)

    def list_preference_suggestions(self, organization_id: str) -> list[PreferenceSuggestion]:
        self.get_organization(organization_id)
        return sorted(
            [suggestion for suggestion in self.preference_suggestions.values() if suggestion.organization_id == organization_id],
            key=lambda suggestion: suggestion.created_at,
            reverse=True,
        )

    def approve_preference_suggestion(
        self,
        suggestion_id: str,
        payload: PreferenceSuggestionDecision,
        actor_id: str = "local_user",
    ) -> PreferenceSuggestion:
        suggestion = self.get_preference_suggestion(suggestion_id)
        self.require_role(suggestion.organization_id, actor_id, {UserRole.owner, UserRole.editor})
        if suggestion.status != PreferenceSuggestionStatus.pending:
            return suggestion
        self._apply_preference_update(suggestion)
        suggestion.status = PreferenceSuggestionStatus.approved
        suggestion.decided_at = now_utc()
        self.preference_suggestions[suggestion.id] = suggestion
        self.log(
            suggestion.organization_id,
            "preference_suggestion.approved",
            "preference_suggestion",
            suggestion.id,
            {"reason": payload.reason, "proposed_update": suggestion.proposed_update},
            actor_id,
        )
        return suggestion

    def dismiss_preference_suggestion(
        self,
        suggestion_id: str,
        payload: PreferenceSuggestionDecision,
        actor_id: str = "local_user",
    ) -> PreferenceSuggestion:
        suggestion = self.get_preference_suggestion(suggestion_id)
        self.require_role(suggestion.organization_id, actor_id, {UserRole.owner, UserRole.editor})
        suggestion.status = PreferenceSuggestionStatus.dismissed
        suggestion.decided_at = now_utc()
        self.preference_suggestions[suggestion.id] = suggestion
        self.log(
            suggestion.organization_id,
            "preference_suggestion.dismissed",
            "preference_suggestion",
            suggestion.id,
            {"reason": payload.reason},
            actor_id,
        )
        return suggestion

    def get_preference_suggestion(self, suggestion_id: str) -> PreferenceSuggestion:
        if suggestion_id not in self.preference_suggestions:
            raise NotFoundError("Preference suggestion not found")
        return self.preference_suggestions[suggestion_id]

    def _apply_preference_update(self, suggestion: PreferenceSuggestion) -> None:
        profile = self.profiles[suggestion.organization_id]
        updates = suggestion.proposed_update
        if "preferred_phrases_add" in updates:
            additions = [item for item in updates["preferred_phrases_add"] if item not in profile.preferred_phrases]
            profile.preferred_phrases = [*profile.preferred_phrases, *additions]
        if "banned_phrases_add" in updates:
            additions = [item for item in updates["banned_phrases_add"] if item not in profile.banned_phrases]
            profile.banned_phrases = [*profile.banned_phrases, *additions]
        profile.updated_at = now_utc()
        self.profiles[suggestion.organization_id] = profile

    def _find_matching_preference_suggestion(self, candidate: PreferenceSuggestion) -> PreferenceSuggestion | None:
        for suggestion in self.preference_suggestions.values():
            if (
                suggestion.organization_id == candidate.organization_id
                and suggestion.kind == candidate.kind
                and suggestion.status == PreferenceSuggestionStatus.pending
                and suggestion.proposed_update == candidate.proposed_update
            ):
                return suggestion
        return None

    def record_performance_metrics(
        self,
        memory_id: str,
        payload: PerformanceMetricsCreate,
        actor_id: str = "local_user",
    ) -> PostMemory:
        if memory_id not in self.memory:
            raise NotFoundError("Post memory not found")
        memory = self.memory[memory_id]
        memory.performance_snapshot = build_performance_snapshot(payload)
        self.memory[memory_id] = memory
        self.log(
            memory.organization_id,
            "memory.performance_recorded",
            "post_memory",
            memory.id,
            {"source": memory.performance_snapshot.get("source"), "metrics": memory.performance_snapshot.get("metrics", {})},
            actor_id,
        )
        return memory

    def import_linkedin_analytics(self, organization_id: str, actor_id: str = "local_user") -> list[PostMemory]:
        self.get_organization(organization_id)
        imported: list[PostMemory] = []
        for memory in self.list_memory(organization_id):
            if memory.platform != "linkedin" or memory.published_at is None:
                continue
            memory.performance_snapshot = self.analytics_importer.import_snapshot(memory)
            self.memory[memory.id] = memory
            imported.append(memory)
        self.log(
            organization_id,
            "analytics.imported",
            "organization",
            organization_id,
            {"provider": self.analytics_importer.provider_name, "count": len(imported)},
            actor_id,
        )
        return imported

    def analytics_dashboard(self, organization_id: str) -> AnalyticsDashboard:
        self.get_organization(organization_id)
        posts = [memory for memory in self.list_memory(organization_id) if memory.performance_snapshot]
        totals = {"impressions": 0, "reactions": 0, "comments": 0, "shares": 0, "clicks": 0}
        summaries: list[AnalyticsPostSummary] = []
        for memory in posts:
            metrics = memory.performance_snapshot.get("metrics", {})
            if not isinstance(metrics, dict):
                metrics = {}
            clean_metrics = {key: int(metrics.get(key, 0) or 0) for key in totals}
            for key, value in clean_metrics.items():
                totals[key] += value
            score = float(memory.performance_snapshot.get("performance_score", 0.0) or 0.0)
            summaries.append(
                AnalyticsPostSummary(
                    post_memory_id=memory.id,
                    source_draft_id=memory.source_draft_id,
                    platform=memory.platform,
                    content_type=memory.content_type,
                    excerpt=memory.final_body[:140],
                    performance_score=score,
                    metrics=clean_metrics,
                )
            )
        summaries = sorted(summaries, key=lambda item: item.performance_score, reverse=True)
        average = round(sum(item.performance_score for item in summaries) / len(summaries), 3) if summaries else 0.0
        return AnalyticsDashboard(
            organization_id=organization_id,
            posts_analyzed=len(summaries),
            total_impressions=totals["impressions"],
            total_reactions=totals["reactions"],
            total_comments=totals["comments"],
            total_shares=totals["shares"],
            total_clicks=totals["clicks"],
            average_performance_score=average,
            top_posts=summaries[:5],
        )

    def strategy_dashboard(self, organization_id: str) -> StrategyDashboard:
        self.get_organization(organization_id)
        profile = self.profiles[organization_id]
        sources = [source for source in self.list_sources(organization_id) if source.approval_status == SourceStatus.approved]
        source_chunks = self.approved_chunks(organization_id)
        memory = self.list_memory(organization_id)
        drafts = [draft for draft in self.drafts.values() if draft.organization_id == organization_id]
        pillars = profile.content_pillars or ["approved company knowledge", "source-backed communication", "human review"]

        pillar_coverage: list[PillarCoverage] = []
        for pillar in pillars:
            pillar_terms = terms(pillar)
            source_count = sum(1 for chunk in source_chunks if pillar_terms & terms(chunk.chunk_text))
            artifact_matches = [
                item
                for item in [*memory, *drafts]
                if pillar_terms
                and (
                    pillar_terms & terms(getattr(item, "final_body", "") or getattr(item, "body", ""))
                    or pillar_terms & set(getattr(item, "topic_labels", []))
                )
            ]
            scored_memory = [
                post
                for post in memory
                if post.performance_snapshot and (pillar_terms & terms(post.final_body) or pillar_terms & set(post.topic_labels))
            ]
            average_score = (
                round(
                    sum(float(post.performance_snapshot.get("performance_score", 0.0) or 0.0) for post in scored_memory) / len(scored_memory),
                    3,
                )
                if scored_memory
                else 0.0
            )
            if source_count == 0:
                recommendation = "Add approved source evidence before generating more content for this pillar."
            elif not artifact_matches:
                recommendation = "Good source coverage, but this pillar needs new content."
            elif average_score > 0:
                recommendation = "Performance data exists; use it to refine the next recommendation."
            else:
                recommendation = "Content exists; add performance metrics to learn what works."
            pillar_coverage.append(
                PillarCoverage(
                    pillar=pillar,
                    source_count=source_count,
                    artifact_count=len(artifact_matches),
                    performance_score=average_score,
                    recommendation=recommendation,
                )
            )

        topic_counts: dict[str, dict[str, object]] = {}
        for post in memory:
            for topic in post.topic_labels:
                if not topic:
                    continue
                current = topic_counts.setdefault(topic, {"count": 0, "last_seen": None})
                current["count"] = int(current["count"]) + 1
                seen_at = post.published_at or post.exported_at or post.approved_at
                if seen_at and (current["last_seen"] is None or seen_at > current["last_seen"]):
                    current["last_seen"] = seen_at
        topic_repetition = sorted(
            [
                TopicRepetition(topic=topic, count=int(data["count"]), last_seen=data["last_seen"])
                for topic, data in topic_counts.items()
            ],
            key=lambda item: item.count,
            reverse=True,
        )[:8]

        def breakdown(key_fn) -> list[PerformanceBreakdown]:
            groups: dict[str, list[PostMemory]] = {}
            for post in memory:
                if post.performance_snapshot:
                    groups.setdefault(key_fn(post), []).append(post)
            rows: list[PerformanceBreakdown] = []
            for key, posts in sorted(groups.items()):
                metrics_total = {"impressions": 0, "reactions": 0, "clicks": 0}
                scores: list[float] = []
                for post in posts:
                    metrics = post.performance_snapshot.get("metrics", {})
                    if not isinstance(metrics, dict):
                        metrics = {}
                    metrics_total["impressions"] += int(metrics.get("impressions", 0) or 0)
                    metrics_total["reactions"] += int(metrics.get("reactions", 0) or 0)
                    metrics_total["clicks"] += int(metrics.get("clicks", 0) or 0)
                    scores.append(float(post.performance_snapshot.get("performance_score", 0.0) or 0.0))
                rows.append(
                    PerformanceBreakdown(
                        key=key,
                        label=key.replace("_", " ").title(),
                        posts=len(posts),
                        average_score=round(sum(scores) / len(scores), 3) if scores else 0.0,
                        impressions=metrics_total["impressions"],
                        reactions=metrics_total["reactions"],
                        clicks=metrics_total["clicks"],
                    )
                )
            return sorted(rows, key=lambda row: row.average_score, reverse=True)

        suggested_directions: list[StrategyDirection] = []
        uncovered = [pillar for pillar in pillar_coverage if pillar.source_count > 0 and pillar.artifact_count == 0]
        weak_source = [pillar for pillar in pillar_coverage if pillar.source_count == 0]
        repeated_topics = [topic for topic in topic_repetition if topic.count >= 2]
        if uncovered:
            pillar = uncovered[0]
            suggested_directions.append(
                StrategyDirection(
                    title=f"Create content for {pillar.pillar}",
                    rationale="Approved source coverage exists, but no durable content artifact has been created yet.",
                    source_basis=[source.title for source in sources[:3]],
                    confidence=0.78,
                )
            )
        if weak_source:
            pillar = weak_source[0]
            suggested_directions.append(
                StrategyDirection(
                    title=f"Strengthen source coverage for {pillar.pillar}",
                    rationale="This pillar is in the profile but lacks approved source evidence.",
                    source_basis=[],
                    confidence=0.68,
                )
            )
        if repeated_topics:
            topic = repeated_topics[0]
            suggested_directions.append(
                StrategyDirection(
                    title=f"Vary repeated topic: {topic.topic}",
                    rationale=f"This topic appears {topic.count} times in approved memory; use a different angle before repeating it again.",
                    source_basis=[source.title for source in sources[:2]],
                    confidence=0.64,
                )
            )
        if not suggested_directions:
            suggested_directions.append(
                StrategyDirection(
                    title="Generate a fresh source-backed recommendation",
                    rationale="Current strategy signals are balanced; the next best move is to generate a new opportunity from approved context.",
                    source_basis=[source.title for source in sources[:3]],
                    confidence=0.58,
                )
            )

        return StrategyDashboard(
            organization_id=organization_id,
            pillar_coverage=pillar_coverage,
            topic_repetition=topic_repetition,
            performance_by_platform=breakdown(lambda post: post.platform),
            performance_by_content_type=breakdown(lambda post: post.content_type),
            suggested_directions=suggested_directions,
        )

    def list_calendar(self, organization_id: str) -> list[Draft]:
        self.get_organization(organization_id)
        queue_statuses = {DraftStatus.approved, DraftStatus.scheduled, DraftStatus.exported, DraftStatus.published}
        return sorted(
            [draft for draft in self.drafts.values() if draft.organization_id == organization_id and draft.status in queue_statuses],
            key=lambda draft: (draft.scheduled_for is None, draft.scheduled_for or draft.updated_at),
        )

    def _opportunity_prompt(
        self,
        profile: CompanyProfile,
        sources: list[Source],
        chunks: list[SourceChunk],
    ) -> str:
        evidence = "\n".join(f"- {chunk.source_id}: {chunk.chunk_text[:360]}" for chunk in chunks[:8])
        pillars = ", ".join(profile.content_pillars[:8]) or "approved company context"
        return (
            "Generate source-grounded public communication opportunities as JSON. Use only the approved evidence. "
            "Avoid unsupported claims. Prefer concrete events, launches, product work, published posts, labs, repos, "
            "or current milestones over abstract philosophy. If a recent blog, product, release, or public proof artifact "
            "appears in evidence, suggest a timely opportunity about that specific thing. "
            "When evidence includes a named product, recent blog, release, lab, repo, or public proof artifact, prioritize those recommendations first. "
            "Titles must be specific and public-facing, never template phrases like 'share a practical point of view'.\n"
            f"Today: {now_utc().date().isoformat()}\n"
            f"Audience: {profile.audience or 'unspecified'}\n"
            f"Content pillars: {pillars}\n"
            f"Approved sources: {', '.join(source.title for source in sources[:8])}\n"
            f"Evidence:\n{evidence}"
        )

    def _validated_model_draft_variant(
        self,
        recommendation: dict[str, Any],
        adapter: FormatAdapter,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> dict[str, Any] | None:
        raw_hook = str(recommendation.get("hook") or "").strip()
        raw_body = str(recommendation.get("body") or "").strip()
        raw_hashtags = recommendation.get("hashtags") or []
        hashtags = [str(tag).strip() for tag in raw_hashtags if str(tag).strip()]
        if not raw_body:
            return None

        hook, body, hashtags, notes = self._sanitize_model_draft_for_platform(
            raw_hook,
            raw_body,
            hashtags,
            adapter.platform,
            adapter.content_type,
        )
        if self._model_draft_rejection_reasons(hook, body, hashtags, adapter, profile, brief, opportunity):
            return None
        return {"hook": hook, "body": body, "hashtags": hashtags, "notes": notes}

    def _sanitize_model_draft_for_platform(
        self,
        hook: str,
        body: str,
        hashtags: list[str],
        platform: str,
        content_type: str,
    ) -> tuple[str, str, list[str], list[str]]:
        notes: list[str] = []
        clean = re.sub(r"\r\n?", "\n", body).strip()
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        extracted_title = self._extract_labeled_value(clean, "Title")

        if platform == "reddit":
            if extracted_title:
                hook = extracted_title
                notes.append("Moved Reddit title from body into hook.")
                clean = self._remove_labeled_section(clean, "Title", ["Subreddit fit", "Post body", "Discussion question"])
            clean = self._remove_labeled_section(clean, "Subreddit fit", ["Post body", "Discussion question"])
            clean = self._replace_labeled_heading(clean, "Post body", "")
            clean = self._replace_labeled_heading(clean, "Discussion question", "")
            clean = re.sub(r"(?m)^\s*Hashtags?:.*$", "", clean)
            hashtags = []
            notes.append("Removed Reddit planning labels and hashtags from visible copy.")
        elif platform == "linkedin":
            clean = self._replace_labeled_heading(clean, "Post body", "")
            clean = self._replace_labeled_heading(clean, "LinkedIn post", "")
            clean = self._remove_labeled_section(clean, "Subreddit fit", ["Post body", "Discussion question"])
            clean = self._replace_labeled_heading(clean, "Discussion question", "")
        elif platform == "instagram":
            if content_type == "post":
                clean = self._remove_labeled_section(clean, "Visual direction", ["Caption", "Post copy", "Hashtags"])
                clean = self._replace_labeled_heading(clean, "Post copy", "")
                clean = self._replace_labeled_heading(clean, "Caption", "")
                clean = self._replace_labeled_heading(clean, "Trust cue", "The trust comes from the proof: ")
                clean = re.sub(r"(?im)^\s*Hashtags?:.*$", "", clean)
                notes.append("Removed Instagram planning labels from visible caption.")

        clean = re.sub(r"[ \t]+\n", "\n", clean).strip()
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        hook = hook or extracted_title or self._first_meaningful_line(clean)
        return hook.strip()[:180], clean, hashtags, notes

    def _extract_labeled_value(self, body: str, label: str) -> str | None:
        match = re.search(rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+?)\s*$", body)
        return match.group(1).strip() if match else None

    def _remove_labeled_section(self, body: str, label: str, next_labels: list[str]) -> str:
        next_pattern = "|".join(re.escape(next_label) for next_label in next_labels)
        if next_pattern:
            pattern = rf"(?ims)^\s*{re.escape(label)}\s*:.*?(?=^\s*(?:{next_pattern})\s*:|\Z)"
        else:
            pattern = rf"(?ims)^\s*{re.escape(label)}\s*:.*?\Z"
        return re.sub(pattern, "", body).strip()

    def _replace_labeled_heading(self, body: str, label: str, replacement: str) -> str:
        return re.sub(rf"(?im)^[ \t]*{re.escape(label)}[ \t]*:[ \t]*", replacement, body)

    def _first_meaningful_line(self, body: str) -> str:
        for line in body.splitlines():
            clean = line.strip(" -")
            if clean and not clean.endswith(":"):
                return clean
        return "Review this source-backed draft"

    def _model_draft_rejection_reasons(
        self,
        hook: str,
        body: str,
        hashtags: list[str],
        adapter: FormatAdapter,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> list[str]:
        reasons: list[str] = []
        lowered = body.lower()
        combined = f"{hook} {body}".lower()
        if len(body.split()) < 18:
            reasons.append("too_short")
        if any(marker in lowered for marker in ["required structure", "adapter rules", "as an ai", "model-written", "insert ", "[", "]"]):
            reasons.append("prompt_or_template_leak")
        generic_markers = [
            "source-backed communication opportunity",
            "approved source context is available",
            "turn approved context into",
            "use approved context to draft",
            "generic cross-platform draft",
            "reviewable update",
        ]
        if any(marker in combined for marker in generic_markers):
            reasons.append("generic_model_text")

        evidence_chunks = [chunk for chunk in self.approved_chunks(brief.organization_id) if chunk.source_id in brief.source_ids]
        evidence_text = " ".join([*brief.supporting_points, opportunity.summary, *(chunk.chunk_text for chunk in evidence_chunks)])
        evidence_terms = terms(evidence_text) - {"source", "backed", "approved", "context", "content", "post", "draft", "review"}
        body_terms = terms(f"{hook} {body}") - {"source", "backed", "approved", "context", "content", "post", "draft", "review"}
        if evidence_terms and len(evidence_terms & body_terms) < min(3, max(2, len(evidence_terms) // 12)):
            reasons.append("not_enough_source_overlap")

        forbidden_phrases = [phrase.lower() for phrase in [*profile.banned_phrases, *profile.forbidden_claims, *brief.do_not_say] if phrase]
        if any(phrase in lowered for phrase in forbidden_phrases):
            reasons.append("forbidden_phrase")

        if adapter.platform == "reddit":
            if hashtags or "#" in body:
                reasons.append("reddit_hashtags")
            if any(marker in lowered for marker in ["visual direction:", "caption:", "linkedin", "company post"]):
                reasons.append("wrong_platform_for_reddit")
            if "?" not in body:
                reasons.append("reddit_missing_discussion_question")
            if re.search(r"(?m)^\s*\*\*.+\*\*\s*$", body):
                reasons.append("reddit_markdown_headline")
            reddit_promo_markers = [
                "build production-ready",
                "get hands-on with",
                "secure company communication made easy",
                "should we prioritize speed or reliability",
                "what's your experience",
                "what's the value of this capability-building path",
                "what truly matters",
                "turn our culture into real work",
                "as ai leverages grow",
                "ever wondered",
                "read more about",
                "start building",
                "enhances productivity",
                "ai-powered projects",
            ]
            reddit_invented_voice_markers = [
                "as i built",
                "i built my first",
                "helped me understand",
                "i recently stumbled upon",
            ]
            if any(marker in combined for marker in ["sign up", "book a demo", "buy now", "limited time", *reddit_promo_markers]):
                reasons.append("reddit_sales_tone")
            if any(marker in combined for marker in reddit_invented_voice_markers):
                reasons.append("reddit_invented_first_person")
        elif adapter.platform == "linkedin":
            if any(marker in lowered for marker in ["subreddit fit", "visual direction:", "caption:", "post copy:"]):
                reasons.append("wrong_platform_for_linkedin")
            if body.count("\n\n") < 2:
                reasons.append("linkedin_needs_short_paragraphs")
        elif adapter.platform == "instagram":
            if len(body) > 1100:
                reasons.append("instagram_too_long")
            if adapter.content_type == "post" and any(label in body for label in ["Visual direction:", "Post copy:", "Hashtags:"]):
                reasons.append("instagram_visible_planning_label")
            if adapter.content_type == "post" and "\n\n" not in body and len(body.split()) > 38:
                reasons.append("instagram_long_single_paragraph")
            normalized_key_message = re.sub(r"\W+", " ", brief.key_message).strip().lower()
            normalized_lines = {re.sub(r"\W+", " ", line).strip().lower() for line in body.splitlines()}
            if adapter.content_type == "post" and normalized_key_message and normalized_key_message in normalized_lines:
                reasons.append("instagram_restates_brief_title")
            instagram_announcement_markers = [
                "published blog today:",
                "our latest blog post",
                "latest blog post explores",
                "shows that",
                "is crucial to creating successful",
                "harness the power of ai",
            ]
            if adapter.content_type == "post" and any(marker in lowered for marker in instagram_announcement_markers):
                reasons.append("instagram_announcement_prose")
            if adapter.content_type == "post" and re.search(r"\bat\s+[\w .'-]{2,40},\s+we believe\b", body, flags=re.IGNORECASE):
                reasons.append("instagram_announcement_prose")
            instagram_source_dump_markers = [
                "real context makes better content",
                "get hands-on with",
                "culture into real work",
                "read more about",
                "start building",
                "enhances productivity",
                "ai-powered projects",
            ]
            if adapter.content_type == "post" and any(marker in combined for marker in instagram_source_dump_markers):
                reasons.append("instagram_source_dump_or_promo")
            if "subreddit fit" in lowered or "linkedin" in lowered:
                reasons.append("wrong_platform_for_instagram")

        if any("unsupported" in check.lower() for check in adapter.quality_checks(body, profile, brief)):
            reasons.append("unsupported_metric")
        return reasons

    def _brief_prompt(
        self,
        profile: CompanyProfile,
        opportunity: ContentOpportunity,
        chunks: list[SourceChunk],
    ) -> str:
        evidence = "\n".join(
            f"- {chunk.id}: {chunk.chunk_text[:360]}"
            for chunk in chunks
            if chunk.source_id in opportunity.source_ids
        )
        return (
            "Create a platform-independent source-grounded brief as JSON. "
            "Preserve reviewer caution and do not invent metrics, customers, dates, or claims.\n"
            f"Audience: {profile.audience or 'unspecified'}\n"
            f"Opportunity title: {opportunity.title}\n"
            f"Opportunity summary: {opportunity.summary}\n"
            f"Why now: {opportunity.reason_today}\n"
            f"Evidence:\n{evidence[:1800]}"
        )

    def _draft_prompt(
        self,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
        generation_spec: dict[str, Any],
    ) -> str:
        platform = str(generation_spec.get("platform", "platform"))
        content_type = str(generation_spec.get("content_type", "post"))
        metadata = generation_spec.get("metadata", {})
        evidence = "\n".join(
            f"- {chunk.chunk_text[:420]}"
            for chunk in self.approved_chunks(brief.organization_id)
            if chunk.source_id in brief.source_ids
        )
        approved_claims = " | ".join(profile.approved_claims[:8]) or "Use only claims supported by the brief and evidence."
        banned_phrases = " | ".join(profile.banned_phrases[:8]) or "No unsupported hype, metrics, or platform-inappropriate language."
        return (
            "Generate reviewable draft variants as JSON for the exact platform and content type below. "
            "The response must match DraftRecommendationSet with exactly 3 distinct variants containing hook, body, and hashtags. "
            "Use the brief, adapter rules, adapter metadata, approved source evidence, and platform style. "
            "Keep every claim source-grounded, cautious, and easy for a human reviewer to edit. The body must be the actual "
            "visible draft text for that platform, not notes about what to write. Do not include internal planning labels, "
            "instructions, placeholders, or generic cross-platform copy. Use at least one concrete detail from the evidence.\n"
            f"Platform: {platform}\n"
            f"Content type: {content_type}\n"
            f"Audience: {profile.audience or brief.audience}\n"
            f"Company one-liner: {profile.one_liner or profile.product_summary or 'unspecified'}\n"
            f"Brief key message: {brief.key_message}\n"
            f"Supporting points: {' | '.join(brief.supporting_points[:6])}\n"
            f"Approved claims: {approved_claims}\n"
            f"Do not say: {' | '.join(brief.do_not_say[:8])}\n"
            f"Banned phrases: {banned_phrases}\n"
            f"Opportunity reason: {opportunity.reason_today}\n"
            f"Adapter: {generation_spec.get('adapter_name')} {generation_spec.get('prompt_version')}\n"
            f"Rules: {' | '.join(generation_spec.get('rules', [])[:10])}\n"
            f"Required structure/style metadata: {metadata}\n"
            "Platform specifics:\n"
            "- LinkedIn company post: hook in the hook field; body uses 3-6 short public paragraphs, a trust-building detail, and a practical takeaway. Do not include section headings.\n"
            "- Reddit post: hook is the Reddit title; body reads like a community discussion with practical context, a source-backed detail, and one honest question. No markdown headline in the body, no hashtags, no sales tone, no invented first-person experience, no 'what's your experience' engagement bait, no corporate announcement voice, and no subreddit-fit notes.\n"
            "- Instagram post: body is the public caption only. Do not include Visual direction, Post copy, Caption, or Hashtags labels. Use short lines, a clear hook, one proof/trust sentence, and put hashtags only in the hashtags array. Do not summarize a blog post in one paragraph, do not start with the source title, and avoid phrases like 'our latest blog post explores' or 'At {brand}, we believe'.\n"
            f"Evidence:\n{evidence[:2200]}"
        )

    def create_job(
        self,
        organization_id: str,
        actor_id: str,
        kind: JobKind,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any] | None = None,
    ) -> BackgroundJob:
        self.get_organization(organization_id)
        job = BackgroundJob(
            organization_id=organization_id,
            actor_id=actor_id,
            kind=kind,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
        self.jobs[job.id] = job
        self._job_changed(job)
        self.log_job(job.id, "Job queued.", {"kind": kind.value, "entity_type": entity_type, "entity_id": entity_id})
        return job

    def get_job(self, job_id: str) -> BackgroundJob:
        if job_id not in self.jobs:
            raise NotFoundError("Job not found")
        return self.jobs[job_id]

    def list_jobs(self, organization_id: str) -> list[BackgroundJob]:
        self.get_organization(organization_id)
        return sorted(
            [job for job in self.jobs.values() if job.organization_id == organization_id],
            key=lambda job: job.updated_at,
            reverse=True,
        )

    def list_job_logs(self, job_id: str) -> list[BackgroundJobLog]:
        self.get_job(job_id)
        return sorted([log for log in self.job_logs if log.job_id == job_id], key=lambda log: log.created_at)

    def list_model_call_logs(self, organization_id: str) -> list[ModelCallLog]:
        self.get_organization(organization_id)
        return sorted(
            [log for log in self.model_call_logs if log.organization_id == organization_id],
            key=lambda log: log.created_at,
            reverse=True,
        )

    def generate_structured_safely(
        self,
        organization_id: str,
        actor_id: str,
        prompt: str,
        prompt_version: str,
        schema_model: type[BaseModel],
        source_ids: list[str] | None = None,
        request_metadata: dict[str, Any] | None = None,
    ) -> tuple[BaseModel | None, ModelCallLog]:
        schema_name = schema_model.__name__
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        provider = self.model_provider_for_org(organization_id)
        try:
            result = provider.generate_structured(prompt, schema_name, schema_model.model_json_schema())
            validated = schema_model.model_validate(result.output)
            log = ModelCallLog(
                organization_id=organization_id,
                actor_id=actor_id,
                provider=result.provider,
                model=result.model,
                prompt_version=prompt_version,
                schema_name=schema_name,
                status=ModelCallStatus.succeeded,
                prompt_hash=prompt_hash,
                source_ids=source_ids or [],
                request_metadata=request_metadata or {},
                response_metadata=result.raw_metadata,
                token_usage=result.token_usage,
                cost_usd=result.cost_usd,
            )
            self.model_call_logs.append(log)
            self._model_call_logged(log)
            return validated, log
        except (RuntimeError, ValueError, ValidationError) as error:
            log = ModelCallLog(
                organization_id=organization_id,
                actor_id=actor_id,
                provider=getattr(provider, "provider_name", "unknown"),
                model=getattr(provider, "model", "unknown"),
                prompt_version=prompt_version,
                schema_name=schema_name,
                status=ModelCallStatus.failed,
                prompt_hash=prompt_hash,
                source_ids=source_ids or [],
                request_metadata=request_metadata or {},
                error_message=str(error),
            )
            self.model_call_logs.append(log)
            self._model_call_logged(log)
            return None, log

    def log_job(
        self,
        job_id: str,
        message: str,
        metadata: dict[str, Any] | None = None,
        level: str = "info",
    ) -> BackgroundJobLog:
        job = self.get_job(job_id)
        log = BackgroundJobLog(
            job_id=job_id,
            organization_id=job.organization_id,
            message=message,
            level=level,
            metadata=metadata or {},
        )
        self.job_logs.append(log)
        self._job_log_added(log)
        return log

    def start_job(self, job_id: str) -> BackgroundJob:
        job = self.get_job(job_id)
        now = now_utc()
        job.status = JobStatus.running
        job.started_at = now
        job.finished_at = None
        job.error_message = None
        job.attempt_count += 1
        job.updated_at = now
        self.jobs[job.id] = job
        self._job_changed(job)
        self.log_job(job.id, "Job started.", {"attempt_count": job.attempt_count})
        return job

    def complete_job(self, job_id: str, result: dict[str, Any] | None = None) -> BackgroundJob:
        job = self.get_job(job_id)
        now = now_utc()
        job.status = JobStatus.succeeded
        job.result = result or {}
        job.error_message = None
        job.finished_at = now
        job.updated_at = now
        self.jobs[job.id] = job
        self._job_changed(job)
        self.log_job(job.id, "Job completed.", job.result)
        return job

    def fail_job(self, job_id: str, error: Exception) -> BackgroundJob:
        job = self.get_job(job_id)
        now = now_utc()
        job.status = JobStatus.failed
        job.error_message = str(error)
        job.finished_at = now
        job.updated_at = now
        self.jobs[job.id] = job
        self._job_changed(job)
        self.log_job(job.id, "Job failed.", {"error": str(error)}, level="error")
        return job

    def reset_job_for_retry(self, job_id: str, actor_id: str) -> BackgroundJob:
        job = self.get_job(job_id)
        if job.status != JobStatus.failed:
            raise PermissionDeniedError("Only failed jobs can be retried.")
        if job.attempt_count >= job.max_attempts:
            raise PermissionDeniedError("Job retry limit has been reached.")
        job.status = JobStatus.queued
        job.actor_id = actor_id
        job.error_message = None
        job.finished_at = None
        job.updated_at = now_utc()
        self.jobs[job.id] = job
        self._job_changed(job)
        self.log_job(job.id, "Job queued for retry.", {"attempt_count": job.attempt_count, "max_attempts": job.max_attempts})
        return job

    def run_job(
        self,
        organization_id: str,
        actor_id: str,
        kind: JobKind,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any] | None,
        work: Callable[[], Any],
        summarize: Callable[[Any], dict[str, Any]] | None = None,
    ) -> tuple[BackgroundJob, Any]:
        job = self.create_job(organization_id, actor_id, kind, entity_type, entity_id, payload)
        return self.run_existing_job(job.id, work, summarize)

    def run_existing_job(
        self,
        job_id: str,
        work: Callable[[], Any],
        summarize: Callable[[Any], dict[str, Any]] | None = None,
    ) -> tuple[BackgroundJob, Any]:
        self.start_job(job_id)
        try:
            result = work()
        except Exception as error:
            self.fail_job(job_id, error)
            raise
        job = self.complete_job(job_id, summarize(result) if summarize else {})
        return job, result

    def list_audit_logs(self, organization_id: str) -> list[AuditLog]:
        return sorted(
            [log for log in self.audit_logs if log.organization_id == organization_id],
            key=lambda log: log.created_at,
            reverse=True,
        )

    def log(
        self,
        organization_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata: dict | None = None,
        actor_id: str = "local_user",
    ) -> None:
        self.audit_logs.append(
            AuditLog(
                organization_id=organization_id,
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata=metadata or {},
            )
        )

    def _job_changed(self, job: BackgroundJob) -> None:
        return None

    def _job_log_added(self, log: BackgroundJobLog) -> None:
        return None

    def _model_call_logged(self, log: ModelCallLog) -> None:
        return None

    def _memory_id_for_draft(self, draft: Draft) -> str:
        return f"mem_{draft.id}"
