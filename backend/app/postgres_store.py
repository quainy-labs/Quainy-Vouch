from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from alembic import command
from alembic.config import Config
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.schemas import (
    Account,
    ApprovalDecision,
    ApprovalPolicy,
    AuditLog,
    CalendarEvent,
    CalendarEventCreate,
    ClaimCheck,
    CompanyProfile,
    ContentBrief,
    ContentOpportunity,
    Decision,
    Draft,
    DraftPublishCreate,
    LinkedInIntegration,
    LinkedInIntegrationUpdate,
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
    SignupCreate,
    Source,
    SourceChunk,
    SourceCreate,
    SourceDocument,
    SourceUpdate,
    TrendSignal,
    TrendSignalCreate,
    User,
    UserRole,
    now_utc,
)
from app.store import AuthenticationError, DataStore, NotFoundError, PermissionDeniedError


def _json(value: Any) -> Jsonb:
    return Jsonb(value)


def _enum_values(values: list[Any]) -> list[str]:
    return [getattr(value, "value", value) for value in values]


def _embedding_to_pgvector(embedding: list[float] | None) -> str | None:
    if embedding is None:
        return None
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"


def _embedding_from_pgvector(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [float(item) for item in value]
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if not text:
        return None
    return [float(item) for item in text.split(",")]


class PostgresDataStore(DataStore):
    """Postgres-backed foundation store.

    This keeps the existing domain logic intact while persisting the production
    foundation plus generated artifacts. Later Phase 2 slices can split this
    into repository classes without changing the API surface again.
    """

    def __init__(self, database_url: str, schema_path: Path) -> None:
        self.database_url = database_url
        self.schema_path = schema_path
        self._audit_persistence_ready = False
        self._suspend_audit_persist = False
        super().__init__()
        self._initialize_schema()
        self._load_persistent_state()
        self._audit_persistence_ready = True

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _initialize_schema(self) -> None:
        root = self.schema_path.parents[2]
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "backend" / "migrations"))
        config.set_main_option("sqlalchemy.url", self.database_url)
        command.upgrade(config, "head")

    def _session_hash(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _create_session(self, account_id: str) -> str:
        token = f"qv_{secrets.token_urlsafe(32)}"
        token_hash = self._session_hash(token)
        self.session_account_ids[token_hash] = account_id
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO account_sessions (token_hash, account_id, created_at)
                    VALUES (%s, %s, %s)
                    """,
                    (token_hash, account_id, now_utc()),
                )
        return token

    def account_for_token(self, token: str | None) -> Account:
        if not token:
            raise AuthenticationError("Authentication required.")
        token_hash = self._session_hash(token)
        account_id = self.session_account_ids.get(token_hash)
        if not account_id:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT account_id
                        FROM account_sessions
                        WHERE token_hash = %s
                          AND revoked_at IS NULL
                          AND (expires_at IS NULL OR expires_at > %s)
                        """,
                        (token_hash, now_utc()),
                    )
                    row = cursor.fetchone()
            if not row:
                raise AuthenticationError("Authentication required.")
            account_id = row["account_id"]
            self.session_account_ids[token_hash] = account_id
        if account_id not in self.accounts:
            self._load_accounts()
        if account_id not in self.accounts:
            raise AuthenticationError("Authentication required.")
        return self.accounts[account_id]

    def signup(self, payload: SignupCreate):
        email = payload.email.strip().lower()
        if email in self.account_ids_by_email:
            raise PermissionDeniedError("An account with this email already exists.")
        account = Account(name=payload.name.strip(), email=email)
        self.accounts[account.id] = account
        self.account_ids_by_email[email] = account.id
        self.account_password_hashes[account.id] = self._hash_password(payload.password)
        self._suspend_audit_persist = True
        try:
            org = DataStore.create_organization(
                self,
                OrganizationCreate(
                    name=payload.organization_name,
                    website_url=payload.website_url,
                    industry=payload.industry,
                    description=payload.description,
                    audience_summary=payload.audience_summary,
                    default_timezone=payload.default_timezone,
                ),
            )
        finally:
            self._suspend_audit_persist = False
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
            completed_steps=[OnboardingStep.account_created, OnboardingStep.organization_created],
        )
        self.onboarding_states[(org.id, account.id)] = onboarding
        self._persist_signup_bundle(account, org, user, onboarding)
        self._persist_audit_logs_for_org(org.id)
        token = self._create_session(account.id)
        self.log(org.id, "auth.signup", "account", account.id, {"email": account.email}, account.id)
        return token, self.current_workspace(token)

    def create_organization(self, payload: OrganizationCreate) -> Organization:
        self._suspend_audit_persist = True
        try:
            org = DataStore.create_organization(self, payload)
        finally:
            self._suspend_audit_persist = False
        self._persist_organization_bundle(org)
        self._persist_audit_logs_for_org(org.id)
        return org

    def update_organization(
        self,
        organization_id: str,
        payload: OrganizationUpdate,
        actor_id: str = "local_user",
    ) -> Organization:
        org = super().update_organization(organization_id, payload, actor_id)
        self._persist_organization(org)
        return org

    def delete_organization(self, organization_id: str, actor_id: str = "local_user"):
        receipt = super().delete_organization(organization_id, actor_id)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM organizations WHERE id = %s", (organization_id,))
        return receipt

    def create_user(self, organization_id: str, payload, actor_id: str = "local_user") -> User:
        user = super().create_user(organization_id, payload, actor_id)
        self._persist_user(user, None)
        return user

    def update_user(self, organization_id: str, user_id: str, payload, actor_id: str = "local_user") -> User:
        user = super().update_user(organization_id, user_id, payload, actor_id)
        account_id = user.id if user.id in self.accounts else None
        self._persist_user(user, account_id)
        return user

    def update_profile(self, organization_id: str, payload, actor_id: str = "local_user") -> CompanyProfile:
        profile = super().update_profile(organization_id, payload, actor_id)
        self._persist_profile(profile)
        return profile

    def update_approval_policy(self, organization_id: str, payload, actor_id: str = "local_user") -> ApprovalPolicy:
        policy = super().update_approval_policy(organization_id, payload, actor_id)
        self._persist_approval_policy(policy)
        return policy

    def mark_onboarding_step(self, organization_id: str, account_id: str, step: OnboardingStep, profile_skipped: bool | None = None):
        onboarding = super().mark_onboarding_step(organization_id, account_id, step, profile_skipped)
        self._persist_onboarding(onboarding)
        return onboarding

    def create_source(self, organization_id: str, payload: SourceCreate, actor_id: str = "local_user") -> Source:
        source = super().create_source(organization_id, payload, actor_id)
        self._persist_source(source)
        return source

    def update_source(self, source_id: str, payload: SourceUpdate, actor_id: str = "local_user") -> Source:
        source = super().update_source(source_id, payload, actor_id)
        self._persist_source(source)
        return source

    def ingest_source(self, source_id: str, actor_id: str = "local_user") -> list[SourceChunk]:
        chunks = super().ingest_source(source_id, actor_id)
        source = self.get_source(source_id)
        document_id = self.latest_document_by_source.get(source_id)
        document = self.source_documents[document_id] if document_id else None
        self._persist_source(source)
        if document:
            self._persist_document(document)
        self._replace_chunks(source_id, chunks)
        return chunks

    def update_linkedin_integration(
        self,
        organization_id: str,
        payload: LinkedInIntegrationUpdate,
        actor_id: str = "local_user",
    ) -> LinkedInIntegration:
        integration = super().update_linkedin_integration(organization_id, payload, actor_id)
        self._persist_linkedin_integration(integration)
        return integration

    def generate_opportunities(self, organization_id: str, actor_id: str = "local_user") -> list[ContentOpportunity]:
        opportunities = super().generate_opportunities(organization_id, actor_id)
        for opportunity in opportunities:
            self._persist_opportunity(opportunity)
        return opportunities

    def create_calendar_event(
        self,
        organization_id: str,
        payload: CalendarEventCreate,
        actor_id: str = "local_user",
    ) -> CalendarEvent:
        event = super().create_calendar_event(organization_id, payload, actor_id)
        self._persist_calendar_event(event, actor_id)
        return event

    def create_trend_signal(
        self,
        organization_id: str,
        payload: TrendSignalCreate,
        actor_id: str = "local_user",
    ) -> TrendSignal:
        trend = super().create_trend_signal(organization_id, payload, actor_id)
        self._persist_trend_signal(trend, actor_id)
        return trend

    def generate_trend_opportunities(self, organization_id: str, actor_id: str = "local_user") -> list[ContentOpportunity]:
        opportunities = super().generate_trend_opportunities(organization_id, actor_id)
        for opportunity in opportunities:
            self._persist_opportunity(opportunity)
        return opportunities

    def create_brief(self, opportunity_id: str, actor_id: str = "local_user") -> ContentBrief:
        brief = super().create_brief(opportunity_id, actor_id)
        self._persist_brief(brief)
        return brief

    def generate_drafts(
        self,
        brief_id: str,
        platform: str = "linkedin",
        content_type: str = "company_post",
        actor_id: str = "local_user",
    ) -> list[Draft]:
        drafts = super().generate_drafts(brief_id, platform, content_type, actor_id)
        for draft in drafts:
            self._persist_draft(draft)
        return drafts

    def regenerate_drafts_for_draft(self, draft_id: str, actor_id: str = "local_user") -> list[Draft]:
        drafts = super().regenerate_drafts_for_draft(draft_id, actor_id)
        for draft in drafts:
            self._persist_draft(draft)
        return drafts

    def update_draft_body(self, draft_id: str, body: str, actor_id: str = "local_user") -> Draft:
        draft = super().update_draft_body(draft_id, body, actor_id)
        self._persist_draft(draft)
        return draft

    def approve_draft(
        self,
        draft_id: str,
        payload: ReviewDecisionCreate,
        actor_id: str = "local_user",
    ) -> ApprovalDecision:
        decision = super().approve_draft(draft_id, payload, actor_id)
        draft = self.get_draft(draft_id)
        self._persist_draft(draft)
        self._persist_decision(decision)
        memory_id = self._memory_id_for_draft(draft)
        if memory_id in self.memory:
            self._persist_memory(self.memory[memory_id])
        return decision

    def reject_draft(
        self,
        draft_id: str,
        payload: ReviewDecisionCreate,
        actor_id: str = "local_user",
    ) -> ApprovalDecision:
        decision = super().reject_draft(draft_id, payload, actor_id)
        self._persist_draft(self.get_draft(draft_id))
        self._persist_decision(decision)
        return decision

    def export_draft(self, draft_id: str, actor_id: str = "local_user") -> ApprovalDecision:
        decision = super().export_draft(draft_id, actor_id)
        draft = self.get_draft(draft_id)
        self._persist_draft(draft)
        self._persist_decision(decision)
        memory_id = self._memory_id_for_draft(draft)
        if memory_id in self.memory:
            self._persist_memory(self.memory[memory_id])
        return decision

    def schedule_draft(
        self,
        draft_id: str,
        scheduled_for,
        reason: str | None = None,
        actor_id: str = "local_user",
    ) -> ApprovalDecision:
        decision = super().schedule_draft(draft_id, scheduled_for, reason, actor_id)
        self._persist_draft(self.get_draft(draft_id))
        self._persist_decision(decision)
        return decision

    def publish_draft_to_linkedin(
        self,
        draft_id: str,
        payload: DraftPublishCreate,
        actor_id: str = "local_user",
    ) -> PublishResult:
        result = super().publish_draft_to_linkedin(draft_id, payload, actor_id)
        draft = self.get_draft(draft_id)
        self._persist_draft(draft)
        self._persist_publish_result(result)
        memory_id = self._memory_id_for_draft(draft)
        if memory_id in self.memory:
            self._persist_memory(self.memory[memory_id])
        for decision in self.list_draft_decisions(draft_id):
            self._persist_decision(decision)
        return result

    def generate_preference_suggestions(
        self,
        organization_id: str,
        actor_id: str = "local_user",
    ) -> list[PreferenceSuggestion]:
        suggestions = super().generate_preference_suggestions(organization_id, actor_id)
        for suggestion in suggestions:
            self._persist_preference_suggestion(suggestion)
        return suggestions

    def approve_preference_suggestion(
        self,
        suggestion_id: str,
        payload: PreferenceSuggestionDecision,
        actor_id: str = "local_user",
    ) -> PreferenceSuggestion:
        suggestion = super().approve_preference_suggestion(suggestion_id, payload, actor_id)
        self._persist_preference_suggestion(suggestion)
        self._persist_profile(self.profiles[suggestion.organization_id])
        return suggestion

    def dismiss_preference_suggestion(
        self,
        suggestion_id: str,
        payload: PreferenceSuggestionDecision,
        actor_id: str = "local_user",
    ) -> PreferenceSuggestion:
        suggestion = super().dismiss_preference_suggestion(suggestion_id, payload, actor_id)
        self._persist_preference_suggestion(suggestion)
        return suggestion

    def record_performance_metrics(
        self,
        memory_id: str,
        payload: PerformanceMetricsCreate,
        actor_id: str = "local_user",
    ) -> PostMemory:
        memory = super().record_performance_metrics(memory_id, payload, actor_id)
        self._persist_memory(memory)
        return memory

    def import_linkedin_analytics(self, organization_id: str, actor_id: str = "local_user") -> list[PostMemory]:
        imported = super().import_linkedin_analytics(organization_id, actor_id)
        for memory in imported:
            self._persist_memory(memory)
        return imported

    def log(
        self,
        organization_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata: dict | None = None,
        actor_id: str = "local_user",
    ) -> None:
        audit = AuditLog(
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
        )
        self.audit_logs.append(audit)
        if self._audit_persistence_ready and not self._suspend_audit_persist:
            self._persist_audit_log(audit)

    def _load_persistent_state(self) -> None:
        self._load_accounts()
        self._load_organizations()
        self._load_profiles()
        self._load_approval_policies()
        self._load_users()
        self._load_onboarding()
        self._load_sources()
        self._load_documents()
        self._load_chunks()
        self._load_calendar_events()
        self._load_trend_signals()
        self._load_opportunities()
        self._load_briefs()
        self._load_drafts()
        self._load_claims()
        self._load_decisions()
        self._load_memory()
        self._load_preference_suggestions()
        self._load_linkedin_integrations()
        self._load_audit_logs()
        self._load_sessions()

    def _load_accounts(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM accounts").fetchall()
        for row in rows:
            account = Account(
                id=row["id"],
                name=row["name"],
                email=row["email"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            self.accounts[account.id] = account
            self.account_ids_by_email[account.email] = account.id
            self.account_password_hashes[account.id] = row["password_hash"]

    def _load_organizations(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM organizations").fetchall()
        for row in rows:
            self.organizations[row["id"]] = Organization(**dict(row))

    def _load_profiles(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM company_profiles").fetchall()
        for row in rows:
            self.profiles[row["organization_id"]] = CompanyProfile(**dict(row))

    def _load_approval_policies(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM approval_policies").fetchall()
        for row in rows:
            self.approval_policies[row["organization_id"]] = ApprovalPolicy(**dict(row))

    def _load_users(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM users").fetchall()
        for row in rows:
            user = User(
                id=row["id"],
                organization_id=row["organization_id"],
                name=row["name"],
                email=row["email"],
                role=row["role"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            self.users[(user.organization_id, user.id)] = user
            if row["account_id"]:
                self.primary_organization_by_account.setdefault(row["account_id"], user.organization_id)

    def _load_onboarding(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM onboarding_states").fetchall()
        for row in rows:
            onboarding = OnboardingState(
                organization_id=row["organization_id"],
                account_id=row["account_id"],
                completed_steps=row["completed_steps"],
                profile_skipped=row["profile_skipped"],
                completed_at=row["completed_at"],
                updated_at=row["updated_at"],
            )
            self.onboarding_states[(onboarding.organization_id, onboarding.account_id)] = onboarding

    def _load_sources(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM sources").fetchall()
        for row in rows:
            source = Source(
                id=row["id"],
                organization_id=row["organization_id"],
                source_type=row["source_type"],
                title=row["title"],
                uri=row["uri"],
                approval_status=row["approval_status"],
                freshness_days=row["freshness_days"],
                last_ingested_at=row["last_ingested_at"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            self.sources[source.id] = source
            self.source_raw_text[source.id] = row["raw_text"]

    def _load_documents(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM source_documents").fetchall()
        for row in rows:
            document = SourceDocument(
                id=row["id"],
                source_id=row["source_id"],
                title=row["title"],
                raw_text=row["raw_text"],
                normalized_text=row["normalized_text"],
                content_hash=row["content_hash"],
                metadata=row["metadata"],
                created_at=row["created_at"],
            )
            self.source_documents[document.id] = document
            self.latest_document_by_source[document.source_id] = document.id
            self.source_hashes[document.source_id] = document.content_hash

    def _load_chunks(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM source_chunks ORDER BY chunk_index").fetchall()
        for row in rows:
            chunk = SourceChunk(
                id=row["id"],
                source_document_id=row["source_document_id"],
                source_id=row["source_id"],
                organization_id=row["organization_id"],
                chunk_text=row["chunk_text"],
                chunk_index=row["chunk_index"],
                embedding=_embedding_from_pgvector(row["embedding"]),
                metadata=row["metadata"],
                created_at=row["created_at"],
            )
            self.chunks[chunk.id] = chunk

    def _load_calendar_events(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM calendar_events").fetchall()
        for row in rows:
            event_date = row.get("event_date") or row.get("starts_at")
            if not event_date:
                continue
            event = CalendarEvent(
                id=row["id"],
                organization_id=row["organization_id"],
                title=row["title"],
                event_date=event_date,
                event_type=row["event_type"],
                description=row["description"],
                relevance_terms=row["relevance_terms"],
                created_at=row["created_at"],
            )
            self.calendar_events[event.id] = event

    def _load_trend_signals(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM trend_signals").fetchall()
        for row in rows:
            trend = TrendSignal(
                id=row["id"],
                organization_id=row["organization_id"],
                title=row["title"],
                summary=row["summary"],
                industry=row.get("industry"),
                relevance_terms=row["relevance_terms"],
                source_uri=row.get("source_uri") or row.get("source_url"),
                created_at=row["created_at"],
            )
            self.trend_signals[trend.id] = trend

    def _load_opportunities(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM content_opportunities").fetchall()
        for row in rows:
            opportunity = ContentOpportunity(
                id=row["id"],
                organization_id=row["organization_id"],
                title=row["title"],
                summary=row["summary"],
                reason_today=row["reason_today"],
                source_ids=row["source_ids"],
                freshness_score=float(row["freshness_score"]),
                relevance_score=float(row["relevance_score"]),
                confidence_score=float(row["confidence_score"]),
                status=row["status"],
                metadata=row["metadata"],
                created_at=row["created_at"],
            )
            self.opportunities[opportunity.id] = opportunity

    def _load_briefs(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM content_briefs").fetchall()
        for row in rows:
            brief = ContentBrief(
                id=row["id"],
                opportunity_id=row["opportunity_id"],
                organization_id=row["organization_id"],
                objective=row["objective"],
                audience=row["audience"],
                key_message=row["key_message"],
                supporting_points=row["supporting_points"],
                claims=row["claims"],
                do_not_say=row["do_not_say"],
                source_ids=row["source_ids"],
                risks=row["risks"],
                prompt_version=row["prompt_version"],
                builder_metadata=row["builder_metadata"],
                created_at=row["created_at"],
            )
            self.briefs[brief.id] = brief

    def _load_drafts(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM drafts").fetchall()
        for row in rows:
            draft = Draft(
                id=row["id"],
                content_brief_id=row["content_brief_id"],
                organization_id=row["organization_id"],
                platform=row["platform"],
                content_type=row["content_type"],
                body=row["body"],
                hook=row["hook"] or "",
                hashtags=row["hashtags"],
                status=row["status"],
                source_ids=row["source_ids"],
                source_map=row["source_map"],
                risk_report=row["risk_report"],
                quality_report=row["quality_report"],
                duplicate_report=row["duplicate_report"],
                generation_metadata=row["generation_metadata"],
                approval_metadata=row["approval_metadata"],
                scheduled_for=row["scheduled_for"],
                exported_at=row["exported_at"],
                published_at=row["published_at"],
                publish_result=row["publish_result"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            self.drafts[draft.id] = draft

    def _load_claims(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM claims ORDER BY id").fetchall()
        for row in rows:
            draft = self.drafts.get(row["draft_id"])
            if not draft:
                continue
            draft.claims.append(
                ClaimCheck(
                    text=row["text"],
                    claim_type=row["claim_type"],
                    confidence=float(row["confidence"]),
                    support_status=row["support_status"],
                    supporting_chunk_ids=row["supporting_chunk_ids"],
                    risk_reason=row["risk_reason"],
                )
            )

    def _load_decisions(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM approval_decisions").fetchall()
        for row in rows:
            decision = ApprovalDecision(
                id=row["id"],
                draft_id=row["draft_id"],
                decision=row["decision"],
                edited_body=row["edited_body"],
                reason=row["reason"],
                override_reason=row["override_reason"],
                reviewer_id=row["reviewer_id"],
                labels=row["labels"],
                created_at=row["created_at"],
            )
            self.decisions[decision.id] = decision

    def _load_memory(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM post_memory").fetchall()
        for row in rows:
            memory = PostMemory(
                id=row["id"],
                organization_id=row["organization_id"],
                platform=row["platform"],
                content_type=row["content_type"],
                final_body=row["final_body"],
                source_draft_id=row["source_draft_id"],
                topic_labels=row["topic_labels"],
                idea_fingerprint=row["idea_fingerprint"],
                approved_at=row["approved_at"],
                exported_at=row["exported_at"],
                published_at=row["published_at"],
                performance_snapshot=row["performance_snapshot"],
            )
            self.memory[memory.id] = memory

    def _load_preference_suggestions(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM preference_suggestions").fetchall()
        for row in rows:
            suggestion = PreferenceSuggestion(
                id=row["id"],
                organization_id=row["organization_id"],
                kind=row["kind"],
                title=row["title"],
                rationale=row["rationale"],
                proposed_update=row["proposed_update"],
                evidence=row["evidence"],
                confidence=float(row["confidence"]),
                status=row["status"],
                created_at=row["created_at"],
                decided_at=row["decided_at"],
            )
            self.preference_suggestions[suggestion.id] = suggestion

    def _load_linkedin_integrations(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM linkedin_integrations").fetchall()
        for row in rows:
            integration = LinkedInIntegration(
                organization_id=row["organization_id"],
                selected_page_urn=row["selected_page_urn"],
                selected_page_name=row["selected_page_name"],
                oauth_status=row["oauth_status"],
                permissions=row["permissions"],
                publishing_enabled=row["publishing_enabled"],
                updated_at=row["updated_at"],
            )
            self.linkedin_integrations[integration.organization_id] = integration

    def _load_audit_logs(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM audit_logs ORDER BY created_at").fetchall()
        for row in rows:
            self.audit_logs.append(
                AuditLog(
                    id=row["id"],
                    organization_id=row["organization_id"],
                    actor_id=row["actor_id"] or "local_user",
                    action=row["action"],
                    entity_type=row["entity_type"],
                    entity_id=row["entity_id"],
                    metadata=row["metadata"],
                    created_at=row["created_at"],
                )
            )

    def _load_sessions(self) -> None:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT token_hash, account_id
                FROM account_sessions
                WHERE revoked_at IS NULL
                  AND (expires_at IS NULL OR expires_at > %s)
                """,
                (now_utc(),),
            ).fetchall()
        for row in rows:
            self.session_account_ids[row["token_hash"]] = row["account_id"]

    def _persist_signup_bundle(self, account: Account, org: Organization, user: User, onboarding: OnboardingState) -> None:
        with self._connect() as connection:
            self._persist_account(account, connection)
            self._persist_organization(org, connection)
            self._persist_profile(self.profiles[org.id], connection)
            self._persist_approval_policy(self.approval_policies[org.id], connection)
            self._delete_user(org.id, "local_user", connection)
            self._persist_user(user, account.id, connection)
            self._persist_onboarding(onboarding, connection)

    def _persist_organization_bundle(self, org: Organization) -> None:
        with self._connect() as connection:
            self._persist_organization(org, connection)
            self._persist_profile(self.profiles[org.id], connection)
            self._persist_approval_policy(self.approval_policies[org.id], connection)
            self._persist_user(self.users[(org.id, "local_user")], None, connection)

    def _persist_account(self, account: Account, connection=None) -> None:
        own_connection = connection is None
        connection = connection or self._connect()
        try:
            connection.execute(
                """
                INSERT INTO accounts (id, name, email, password_hash, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    email = EXCLUDED.email,
                    password_hash = EXCLUDED.password_hash,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    account.id,
                    account.name,
                    account.email,
                    self.account_password_hashes[account.id],
                    account.created_at,
                    account.updated_at,
                ),
            )
        finally:
            if own_connection:
                connection.commit()
                connection.close()

    def _persist_organization(self, org: Organization, connection=None) -> None:
        own_connection = connection is None
        connection = connection or self._connect()
        try:
            connection.execute(
                """
                INSERT INTO organizations (
                    id, name, website_url, industry, description, audience_summary,
                    default_timezone, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    website_url = EXCLUDED.website_url,
                    industry = EXCLUDED.industry,
                    description = EXCLUDED.description,
                    audience_summary = EXCLUDED.audience_summary,
                    default_timezone = EXCLUDED.default_timezone,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    org.id,
                    org.name,
                    org.website_url,
                    org.industry,
                    org.description,
                    org.audience_summary,
                    org.default_timezone,
                    org.created_at,
                    org.updated_at,
                ),
            )
        finally:
            if own_connection:
                connection.commit()
                connection.close()

    def _persist_profile(self, profile: CompanyProfile, connection=None) -> None:
        own_connection = connection is None
        connection = connection or self._connect()
        try:
            connection.execute(
                """
                INSERT INTO company_profiles (
                    organization_id, one_liner, mission, product_summary, audience,
                    voice_rules, preferred_phrases, banned_phrases, approved_claims,
                    forbidden_claims, content_pillars, sensitive_topics, examples_good,
                    examples_bad, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id) DO UPDATE SET
                    one_liner = EXCLUDED.one_liner,
                    mission = EXCLUDED.mission,
                    product_summary = EXCLUDED.product_summary,
                    audience = EXCLUDED.audience,
                    voice_rules = EXCLUDED.voice_rules,
                    preferred_phrases = EXCLUDED.preferred_phrases,
                    banned_phrases = EXCLUDED.banned_phrases,
                    approved_claims = EXCLUDED.approved_claims,
                    forbidden_claims = EXCLUDED.forbidden_claims,
                    content_pillars = EXCLUDED.content_pillars,
                    sensitive_topics = EXCLUDED.sensitive_topics,
                    examples_good = EXCLUDED.examples_good,
                    examples_bad = EXCLUDED.examples_bad,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    profile.organization_id,
                    profile.one_liner,
                    profile.mission,
                    profile.product_summary,
                    profile.audience,
                    _json(profile.voice_rules),
                    _json(profile.preferred_phrases),
                    _json(profile.banned_phrases),
                    _json(profile.approved_claims),
                    _json(profile.forbidden_claims),
                    _json(profile.content_pillars),
                    _json(profile.sensitive_topics),
                    _json(getattr(profile, "examples_good", [])),
                    _json(getattr(profile, "examples_bad", [])),
                    profile.updated_at,
                ),
            )
        finally:
            if own_connection:
                connection.commit()
                connection.close()

    def _persist_approval_policy(self, policy: ApprovalPolicy, connection=None) -> None:
        own_connection = connection is None
        connection = connection or self._connect()
        try:
            connection.execute(
                """
                INSERT INTO approval_policies (
                    organization_id, required_reviewer_count, require_approval_before_export,
                    require_approval_before_publish, allow_risk_override, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id) DO UPDATE SET
                    required_reviewer_count = EXCLUDED.required_reviewer_count,
                    require_approval_before_export = EXCLUDED.require_approval_before_export,
                    require_approval_before_publish = EXCLUDED.require_approval_before_publish,
                    allow_risk_override = EXCLUDED.allow_risk_override,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    policy.organization_id,
                    policy.required_reviewer_count,
                    policy.require_approval_before_export,
                    policy.require_approval_before_publish,
                    policy.allow_risk_override,
                    policy.updated_at,
                ),
            )
        finally:
            if own_connection:
                connection.commit()
                connection.close()

    def _persist_user(self, user: User, account_id: str | None, connection=None) -> None:
        own_connection = connection is None
        connection = connection or self._connect()
        try:
            connection.execute(
                """
                INSERT INTO users (id, organization_id, account_id, name, email, role, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id, id) DO UPDATE SET
                    account_id = EXCLUDED.account_id,
                    name = EXCLUDED.name,
                    email = EXCLUDED.email,
                    role = EXCLUDED.role,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    user.id,
                    user.organization_id,
                    account_id,
                    user.name,
                    user.email,
                    user.role.value,
                    user.created_at,
                    user.updated_at,
                ),
            )
        finally:
            if own_connection:
                connection.commit()
                connection.close()

    def _delete_user(self, organization_id: str, user_id: str, connection=None) -> None:
        own_connection = connection is None
        connection = connection or self._connect()
        try:
            connection.execute("DELETE FROM users WHERE organization_id = %s AND id = %s", (organization_id, user_id))
        finally:
            if own_connection:
                connection.commit()
                connection.close()

    def _persist_onboarding(self, onboarding: OnboardingState, connection=None) -> None:
        own_connection = connection is None
        connection = connection or self._connect()
        try:
            connection.execute(
                """
                INSERT INTO onboarding_states (
                    organization_id, account_id, completed_steps, profile_skipped,
                    completed_at, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id, account_id) DO UPDATE SET
                    completed_steps = EXCLUDED.completed_steps,
                    profile_skipped = EXCLUDED.profile_skipped,
                    completed_at = EXCLUDED.completed_at,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    onboarding.organization_id,
                    onboarding.account_id,
                    _json(_enum_values(onboarding.completed_steps)),
                    onboarding.profile_skipped,
                    onboarding.completed_at,
                    datetime.now(timezone.utc),
                    onboarding.updated_at,
                ),
            )
        finally:
            if own_connection:
                connection.commit()
                connection.close()

    def _persist_source(self, source: Source, connection=None) -> None:
        own_connection = connection is None
        connection = connection or self._connect()
        try:
            connection.execute(
                """
                INSERT INTO sources (
                    id, organization_id, source_type, title, uri, approval_status,
                    freshness_days, raw_text, last_ingested_at, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    source_type = EXCLUDED.source_type,
                    title = EXCLUDED.title,
                    uri = EXCLUDED.uri,
                    approval_status = EXCLUDED.approval_status,
                    freshness_days = EXCLUDED.freshness_days,
                    raw_text = EXCLUDED.raw_text,
                    last_ingested_at = EXCLUDED.last_ingested_at,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    source.id,
                    source.organization_id,
                    source.source_type,
                    source.title,
                    source.uri,
                    source.approval_status.value,
                    source.freshness_days,
                    self.source_raw_text.get(source.id, ""),
                    source.last_ingested_at,
                    source.created_at,
                    source.updated_at,
                ),
            )
        finally:
            if own_connection:
                connection.commit()
                connection.close()

    def _persist_document(self, document: SourceDocument, connection=None) -> None:
        own_connection = connection is None
        connection = connection or self._connect()
        try:
            connection.execute(
                """
                INSERT INTO source_documents (
                    id, source_id, title, raw_text, normalized_text, content_hash,
                    metadata, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    raw_text = EXCLUDED.raw_text,
                    normalized_text = EXCLUDED.normalized_text,
                    content_hash = EXCLUDED.content_hash,
                    metadata = EXCLUDED.metadata
                """,
                (
                    document.id,
                    document.source_id,
                    document.title,
                    document.raw_text,
                    document.normalized_text,
                    document.content_hash,
                    _json(document.metadata),
                    document.created_at,
                ),
            )
        finally:
            if own_connection:
                connection.commit()
                connection.close()

    def _replace_chunks(self, source_id: str, chunks: list[SourceChunk]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM source_chunks WHERE source_id = %s", (source_id,))
            for chunk in chunks:
                connection.execute(
                    """
                    INSERT INTO source_chunks (
                        id, source_document_id, organization_id, source_id, chunk_text,
                        chunk_index, embedding, metadata, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s, %s)
                    """,
                    (
                        chunk.id,
                        chunk.source_document_id,
                        chunk.organization_id,
                        chunk.source_id,
                        chunk.chunk_text,
                        chunk.chunk_index,
                        _embedding_to_pgvector(chunk.embedding),
                        _json(chunk.metadata),
                        chunk.created_at,
                    ),
                )

    def _persist_linkedin_integration(self, integration: LinkedInIntegration) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO linkedin_integrations (
                    organization_id, selected_page_urn, selected_page_name, oauth_status,
                    permissions, publishing_enabled, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id) DO UPDATE SET
                    selected_page_urn = EXCLUDED.selected_page_urn,
                    selected_page_name = EXCLUDED.selected_page_name,
                    oauth_status = EXCLUDED.oauth_status,
                    permissions = EXCLUDED.permissions,
                    publishing_enabled = EXCLUDED.publishing_enabled,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    integration.organization_id,
                    integration.selected_page_urn,
                    integration.selected_page_name,
                    integration.oauth_status,
                    _json(integration.permissions),
                    integration.publishing_enabled,
                    integration.updated_at,
                ),
            )

    def _persist_opportunity(self, opportunity: ContentOpportunity) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_opportunities (
                    id, organization_id, title, summary, reason_today, source_ids,
                    freshness_score, relevance_score, confidence_score, status, metadata, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    summary = EXCLUDED.summary,
                    reason_today = EXCLUDED.reason_today,
                    source_ids = EXCLUDED.source_ids,
                    freshness_score = EXCLUDED.freshness_score,
                    relevance_score = EXCLUDED.relevance_score,
                    confidence_score = EXCLUDED.confidence_score,
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata
                """,
                (
                    opportunity.id,
                    opportunity.organization_id,
                    opportunity.title,
                    opportunity.summary,
                    opportunity.reason_today,
                    _json(opportunity.source_ids),
                    opportunity.freshness_score,
                    opportunity.relevance_score,
                    opportunity.confidence_score,
                    opportunity.status,
                    _json(opportunity.metadata),
                    opportunity.created_at,
                ),
            )

    def _persist_calendar_event(self, event: CalendarEvent, actor_id: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO calendar_events (
                    id, organization_id, title, event_type, event_date, description,
                    relevance_terms, created_by, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    event_type = EXCLUDED.event_type,
                    event_date = EXCLUDED.event_date,
                    description = EXCLUDED.description,
                    relevance_terms = EXCLUDED.relevance_terms,
                    created_by = EXCLUDED.created_by
                """,
                (
                    event.id,
                    event.organization_id,
                    event.title,
                    event.event_type.value,
                    event.event_date,
                    event.description,
                    _json(event.relevance_terms),
                    actor_id,
                    event.created_at,
                ),
            )

    def _persist_trend_signal(self, trend: TrendSignal, actor_id: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO trend_signals (
                    id, organization_id, title, summary, industry, source_uri,
                    relevance_terms, created_by, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    summary = EXCLUDED.summary,
                    industry = EXCLUDED.industry,
                    source_uri = EXCLUDED.source_uri,
                    relevance_terms = EXCLUDED.relevance_terms,
                    created_by = EXCLUDED.created_by
                """,
                (
                    trend.id,
                    trend.organization_id,
                    trend.title,
                    trend.summary,
                    trend.industry,
                    trend.source_uri,
                    _json(trend.relevance_terms),
                    actor_id,
                    trend.created_at,
                ),
            )

    def _persist_brief(self, brief: ContentBrief) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_briefs (
                    id, opportunity_id, organization_id, objective, audience, key_message,
                    supporting_points, claims, do_not_say, source_ids, risks,
                    prompt_version, builder_metadata, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    objective = EXCLUDED.objective,
                    audience = EXCLUDED.audience,
                    key_message = EXCLUDED.key_message,
                    supporting_points = EXCLUDED.supporting_points,
                    claims = EXCLUDED.claims,
                    do_not_say = EXCLUDED.do_not_say,
                    source_ids = EXCLUDED.source_ids,
                    risks = EXCLUDED.risks,
                    prompt_version = EXCLUDED.prompt_version,
                    builder_metadata = EXCLUDED.builder_metadata
                """,
                (
                    brief.id,
                    brief.opportunity_id,
                    brief.organization_id,
                    brief.objective,
                    brief.audience,
                    brief.key_message,
                    _json(brief.supporting_points),
                    _json(brief.claims),
                    _json(brief.do_not_say),
                    _json(brief.source_ids),
                    _json(brief.risks),
                    brief.prompt_version,
                    _json(brief.builder_metadata),
                    brief.created_at,
                ),
            )

    def _persist_draft(self, draft: Draft) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO drafts (
                    id, content_brief_id, organization_id, platform, content_type, body, hook,
                    hashtags, status, source_ids, source_map, risk_report, quality_report,
                    duplicate_report, generation_metadata, approval_metadata, scheduled_for,
                    exported_at, published_at, publish_result, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    body = EXCLUDED.body,
                    hook = EXCLUDED.hook,
                    hashtags = EXCLUDED.hashtags,
                    status = EXCLUDED.status,
                    source_ids = EXCLUDED.source_ids,
                    source_map = EXCLUDED.source_map,
                    risk_report = EXCLUDED.risk_report,
                    quality_report = EXCLUDED.quality_report,
                    duplicate_report = EXCLUDED.duplicate_report,
                    generation_metadata = EXCLUDED.generation_metadata,
                    approval_metadata = EXCLUDED.approval_metadata,
                    scheduled_for = EXCLUDED.scheduled_for,
                    exported_at = EXCLUDED.exported_at,
                    published_at = EXCLUDED.published_at,
                    publish_result = EXCLUDED.publish_result,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    draft.id,
                    draft.content_brief_id,
                    draft.organization_id,
                    draft.platform,
                    draft.content_type,
                    draft.body,
                    draft.hook,
                    _json(draft.hashtags),
                    draft.status.value,
                    _json(draft.source_ids),
                    _json(draft.source_map),
                    _json(draft.risk_report),
                    _json(draft.quality_report),
                    _json(draft.duplicate_report),
                    _json(draft.generation_metadata),
                    _json(draft.approval_metadata),
                    draft.scheduled_for,
                    draft.exported_at,
                    draft.published_at,
                    _json(draft.publish_result),
                    draft.created_at,
                    draft.updated_at,
                ),
            )
            connection.execute("DELETE FROM claims WHERE draft_id = %s", (draft.id,))
            for index, claim in enumerate(draft.claims):
                connection.execute(
                    """
                    INSERT INTO claims (
                        id, draft_id, text, claim_type, confidence, support_status,
                        supporting_chunk_ids, risk_reason
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        f"{draft.id}:{index}",
                        draft.id,
                        claim.text,
                        claim.claim_type,
                        claim.confidence,
                        claim.support_status,
                        _json(claim.supporting_chunk_ids),
                        claim.risk_reason,
                    ),
                )

    def _persist_decision(self, decision: ApprovalDecision) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO approval_decisions (
                    id, draft_id, decision, reviewer_id, edited_body, reason,
                    override_reason, labels, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    reviewer_id = EXCLUDED.reviewer_id,
                    edited_body = EXCLUDED.edited_body,
                    reason = EXCLUDED.reason,
                    override_reason = EXCLUDED.override_reason,
                    labels = EXCLUDED.labels
                """,
                (
                    decision.id,
                    decision.draft_id,
                    decision.decision.value,
                    decision.reviewer_id,
                    decision.edited_body,
                    decision.reason,
                    decision.override_reason,
                    _json(decision.labels),
                    decision.created_at,
                ),
            )

    def _persist_memory(self, memory: PostMemory) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO post_memory (
                    id, organization_id, platform, content_type, final_body,
                    source_draft_id, topic_labels, idea_fingerprint,
                    approved_at, exported_at, published_at, performance_snapshot
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    final_body = EXCLUDED.final_body,
                    source_draft_id = EXCLUDED.source_draft_id,
                    topic_labels = EXCLUDED.topic_labels,
                    idea_fingerprint = EXCLUDED.idea_fingerprint,
                    approved_at = EXCLUDED.approved_at,
                    exported_at = EXCLUDED.exported_at,
                    published_at = EXCLUDED.published_at,
                    performance_snapshot = EXCLUDED.performance_snapshot
                """,
                (
                    memory.id,
                    memory.organization_id,
                    memory.platform,
                    memory.content_type,
                    memory.final_body,
                    memory.source_draft_id,
                    _json(memory.topic_labels),
                    memory.idea_fingerprint,
                    memory.approved_at,
                    memory.exported_at,
                    memory.published_at,
                    _json(memory.performance_snapshot),
                ),
            )

    def _persist_preference_suggestion(self, suggestion: PreferenceSuggestion) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO preference_suggestions (
                    id, organization_id, kind, title, rationale, proposed_update,
                    evidence, confidence, status, created_at, decided_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    rationale = EXCLUDED.rationale,
                    proposed_update = EXCLUDED.proposed_update,
                    evidence = EXCLUDED.evidence,
                    confidence = EXCLUDED.confidence,
                    status = EXCLUDED.status,
                    decided_at = EXCLUDED.decided_at
                """,
                (
                    suggestion.id,
                    suggestion.organization_id,
                    suggestion.kind.value,
                    suggestion.title,
                    suggestion.rationale,
                    _json(suggestion.proposed_update),
                    _json(suggestion.evidence),
                    suggestion.confidence,
                    suggestion.status.value,
                    suggestion.created_at,
                    suggestion.decided_at,
                ),
            )

    def _persist_publish_result(self, result: PublishResult) -> None:
        result_id = "pub_" + hashlib.sha256(f"{result.draft_id}:{result.requested_at.isoformat()}".encode("utf-8")).hexdigest()[:16]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO publish_results (
                    id, draft_id, provider, status, page_urn, page_name,
                    provider_post_id, published_url, failure_reason, requested_at, published_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    provider_post_id = EXCLUDED.provider_post_id,
                    published_url = EXCLUDED.published_url,
                    failure_reason = EXCLUDED.failure_reason,
                    published_at = EXCLUDED.published_at
                """,
                (
                    result_id,
                    result.draft_id,
                    result.provider,
                    result.status,
                    result.page_urn,
                    result.page_name,
                    result.provider_post_id,
                    result.published_url,
                    result.failure_reason,
                    result.requested_at,
                    result.published_at,
                ),
            )

    def _persist_audit_log(self, audit: AuditLog) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_logs (
                    id, organization_id, actor_id, action, entity_type, entity_id,
                    metadata, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    audit.id,
                    audit.organization_id,
                    audit.actor_id,
                    audit.action,
                    audit.entity_type,
                    audit.entity_id,
                    _json(audit.metadata),
                    audit.created_at,
                ),
            )

    def _persist_audit_logs_for_org(self, organization_id: str) -> None:
        for audit in self.audit_logs:
            if audit.organization_id == organization_id:
                self._persist_audit_log(audit)
