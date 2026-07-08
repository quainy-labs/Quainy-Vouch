from __future__ import annotations

from pathlib import Path

from app.contracts import FormatAdapter
from app.briefs import build_brief
from app.drafts import generate_drafts
from app.format_adapters import (
    BlogOutlineAdapter,
    InstagramCaptionAdapter,
    InstagramCarouselOutlineAdapter,
    LinkedInCompanyPostAdapter,
    NewsletterEmailAdapter,
)
from app.intelligence import (
    content_hash,
    duplicate_check,
    idea_fingerprint,
    normalize_text,
    split_chunks,
)
from app.opportunities import OpportunityGenerator
from app.providers import build_embedding_provider, build_model_provider, cosine_similarity
from app.risk_checks import check_claims, high_risk_unsupported_claims, risk_check
from app.schemas import (
    ApprovalDecision,
    AuditLog,
    CompanyProfile,
    CompanyProfileUpdate,
    ContentBrief,
    ContentOpportunity,
    Decision,
    Draft,
    DraftStatus,
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
    PostMemory,
    ReviewDecisionCreate,
    Source,
    SourceChunk,
    SourceCreate,
    SourceDetail,
    SourceDocument,
    SourceStatus,
    SourceUpdate,
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


class DataStore:
    def __init__(self) -> None:
        self.organizations: dict[str, Organization] = {}
        self.profiles: dict[str, CompanyProfile] = {}
        self.sources: dict[str, Source] = {}
        self.source_raw_text: dict[str, str] = {}
        self.source_hashes: dict[str, str] = {}
        self.source_documents: dict[str, SourceDocument] = {}
        self.latest_document_by_source: dict[str, str] = {}
        self.chunks: dict[str, SourceChunk] = {}
        self.opportunities: dict[str, ContentOpportunity] = {}
        self.briefs: dict[str, ContentBrief] = {}
        self.drafts: dict[str, Draft] = {}
        self.decisions: dict[str, ApprovalDecision] = {}
        self.memory: dict[str, PostMemory] = {}
        self.audit_logs: list[AuditLog] = []
        self.format_adapters: dict[tuple[str, str], FormatAdapter] = {}
        self.source_connectors = default_source_connectors()
        self.model_provider = build_model_provider()
        self.embedding_provider = build_embedding_provider()
        self.opportunity_generator = OpportunityGenerator()
        self.register_format_adapter(LinkedInCompanyPostAdapter())
        self.register_format_adapter(BlogOutlineAdapter())
        self.register_format_adapter(NewsletterEmailAdapter())
        self.register_format_adapter(InstagramCaptionAdapter())
        self.register_format_adapter(InstagramCarouselOutlineAdapter())

    def register_format_adapter(self, adapter: FormatAdapter) -> None:
        self.format_adapters[(adapter.platform, adapter.content_type)] = adapter

    def get_format_adapter(self, platform: str, content_type: str) -> FormatAdapter:
        key = (platform, content_type)
        if key not in self.format_adapters:
            raise NotFoundError(f"Format adapter not found for {platform}/{content_type}")
        return self.format_adapters[key]

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
        self.log(org.id, "organization.created", "organization", org.id)
        return org

    def list_organizations(self) -> list[Organization]:
        return list(self.organizations.values())

    def get_organization(self, organization_id: str) -> Organization:
        if organization_id not in self.organizations:
            raise NotFoundError("Organization not found")
        return self.organizations[organization_id]

    def update_organization(self, organization_id: str, payload: OrganizationUpdate) -> Organization:
        org = self.get_organization(organization_id)
        updates = payload.model_dump(exclude_unset=True)
        updated = org.model_copy(update={**updates, "updated_at": now_utc()})
        self.organizations[organization_id] = updated
        self.log(organization_id, "organization.updated", "organization", organization_id, {"fields": sorted(updates)})
        return updated

    def delete_organization(self, organization_id: str) -> None:
        self.get_organization(organization_id)
        source_ids = [source.id for source in self.sources.values() if source.organization_id == organization_id]
        document_ids = [document.id for document in self.source_documents.values() if document.source_id in source_ids]
        for collection in [
            self.organizations,
            self.profiles,
            self.sources,
            self.source_documents,
            self.chunks,
            self.opportunities,
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
        for document_id in document_ids:
            self.source_documents.pop(document_id, None)
        self.audit_logs = [log for log in self.audit_logs if log.organization_id != organization_id]

    def update_profile(self, organization_id: str, payload: CompanyProfileUpdate) -> CompanyProfile:
        self.get_organization(organization_id)
        current = self.profiles[organization_id]
        updates = payload.model_dump(exclude_unset=True)
        profile = current.model_copy(update={**updates, "updated_at": now_utc()})
        self.profiles[organization_id] = profile
        self.log(organization_id, "profile.updated", "company_profile", organization_id, {"fields": sorted(updates)})
        return profile

    def create_source(self, organization_id: str, payload: SourceCreate) -> Source:
        self.get_organization(organization_id)
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
        self.log(organization_id, "source.created", "source", source.id, {"title": source.title})
        return source

    def update_source(self, source_id: str, payload: SourceUpdate) -> Source:
        source = self.get_source(source_id)
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
            )
        else:
            self.log(source.organization_id, "source.updated", "source", source.id, {"fields": sorted(updates)})
        return updated

    def update_source_status(self, source_id: str, status: SourceStatus) -> Source:
        return self.update_source(source_id, SourceUpdate(approval_status=status))

    def get_source(self, source_id: str) -> Source:
        if source_id not in self.sources:
            raise NotFoundError("Source not found")
        return self.sources[source_id]

    def get_source_detail(self, source_id: str) -> SourceDetail:
        source = self.get_source(source_id)
        chunk_count = len([chunk for chunk in self.chunks.values() if chunk.source_id == source.id])
        audit_logs = [log for log in self.audit_logs if log.entity_type == "source" and log.entity_id == source.id]
        return SourceDetail(
            source=source,
            raw_text=self.source_raw_text.get(source.id, ""),
            chunk_count=chunk_count,
            audit_logs=audit_logs,
        )

    def list_sources(self, organization_id: str) -> list[Source]:
        self.get_organization(organization_id)
        return [source for source in self.sources.values() if source.organization_id == organization_id]

    def ingest_source(self, source_id: str) -> list[SourceChunk]:
        source = self.get_source(source_id)
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
        embeddings = self.embedding_provider.embed(chunk_texts)
        for index, text in enumerate(chunk_texts):
            chunk = SourceChunk(
                source_document_id=document.id,
                source_id=source.id,
                organization_id=source.organization_id,
                chunk_text=text,
                chunk_index=index,
                embedding=embeddings[index],
                metadata={"embedding_provider": self.embedding_provider.provider_name},
            )
            self.chunks[chunk.id] = chunk
            created.append(chunk)
        self.source_hashes[source.id] = digest
        source.last_ingested_at = now_utc()
        source.updated_at = now_utc()
        self.sources[source.id] = source
        self.log(source.organization_id, "source.ingested", "source", source.id, {"chunk_count": len(created)})
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
        query_embedding = self.embedding_provider.embed([query])[0]
        candidates = self.approved_chunks(organization_id)
        ranked: list[tuple[SourceChunk, Source, float]] = []
        for chunk in candidates:
            score = cosine_similarity(query_embedding, chunk.embedding)
            if score > 0:
                ranked.append((chunk, self.sources[chunk.source_id], round(score, 6)))
        ranked.sort(key=lambda item: item[2], reverse=True)
        return ranked[:limit]

    def generate_opportunities(self, organization_id: str) -> list[ContentOpportunity]:
        profile = self.profiles[organization_id]
        sources = [source for source in self.list_sources(organization_id) if source.approval_status == SourceStatus.approved]
        opportunities = self.opportunity_generator.generate(
            profile,
            sources,
            self.approved_chunks(organization_id),
            self.list_memory(organization_id),
        )
        for opportunity in opportunities:
            self.opportunities[opportunity.id] = opportunity
        self.log(organization_id, "opportunities.generated", "organization", organization_id, {"count": len(opportunities)})
        return opportunities

    def create_brief(self, opportunity_id: str) -> ContentBrief:
        opportunity = self.get_opportunity(opportunity_id)
        brief = build_brief(self.profiles[opportunity.organization_id], opportunity, self.approved_chunks(opportunity.organization_id))
        self.briefs[brief.id] = brief
        self.log(brief.organization_id, "brief.created", "brief", brief.id)
        return brief

    def generate_drafts(self, brief_id: str, platform: str = "linkedin", content_type: str = "company_post") -> list[Draft]:
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
        for draft in drafts:
            draft.generation_metadata["model_provider"] = self.model_provider.provider_name
            draft.generation_metadata["embedding_provider"] = self.embedding_provider.provider_name
            self.drafts[draft.id] = draft
        self.log(brief.organization_id, "drafts.generated", "brief", brief.id, {"count": len(drafts)})
        return drafts

    def regenerate_drafts_for_draft(self, draft_id: str) -> list[Draft]:
        draft = self.get_draft(draft_id)
        drafts = self.generate_drafts(draft.content_brief_id, draft.platform, draft.content_type)
        self.log(
            draft.organization_id,
            "draft.regenerated",
            "draft",
            draft.id,
            {"count": len(drafts), "new_draft_ids": [new_draft.id for new_draft in drafts]},
        )
        return drafts

    def update_draft_body(self, draft_id: str, body: str) -> Draft:
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
        self.log(draft.organization_id, "draft.edited", "draft", draft.id)
        return draft

    def approve_draft(self, draft_id: str, payload: ReviewDecisionCreate) -> ApprovalDecision:
        draft = self.get_draft(draft_id)
        if payload.edited_body:
            draft = self.update_draft_body(draft_id, payload.edited_body)
        if high_risk_unsupported_claims(draft.claims):
            raise ApprovalBlockedError("Unsupported factual claims must be resolved before approval.")
        draft.status = DraftStatus.approved
        draft.updated_at = now_utc()
        self.drafts[draft.id] = draft
        decision = ApprovalDecision(draft_id=draft.id, decision=Decision.approve, **payload.model_dump())
        self.decisions[decision.id] = decision
        self.memory[self._memory_id_for_draft(draft)] = PostMemory(
            organization_id=draft.organization_id,
            platform=draft.platform,
            content_type=draft.content_type,
            final_body=draft.body,
            source_draft_id=draft.id,
            topic_labels=idea_fingerprint(draft.body).split()[:5],
            idea_fingerprint=idea_fingerprint(draft.body),
            approved_at=now_utc(),
        )
        self.log(draft.organization_id, "draft.approved", "draft", draft.id)
        return decision

    def reject_draft(self, draft_id: str, payload: ReviewDecisionCreate) -> ApprovalDecision:
        if not payload.reason or not payload.reason.strip():
            raise ReviewDecisionRequiredError("Rejecting a draft requires a reason.")
        draft = self.get_draft(draft_id)
        if payload.edited_body:
            draft = self.update_draft_body(draft_id, payload.edited_body)
        draft.status = DraftStatus.rejected
        draft.updated_at = now_utc()
        self.drafts[draft.id] = draft
        decision = ApprovalDecision(draft_id=draft.id, decision=Decision.reject, **payload.model_dump())
        self.decisions[decision.id] = decision
        self.log(draft.organization_id, "draft.rejected", "draft", draft.id, {"reason": payload.reason})
        return decision

    def export_draft(self, draft_id: str) -> ApprovalDecision:
        draft = self.get_draft(draft_id)
        draft.status = DraftStatus.exported
        draft.exported_at = now_utc()
        draft.updated_at = now_utc()
        self.drafts[draft.id] = draft
        memory_id = self._memory_id_for_draft(draft)
        if memory_id not in self.memory:
            self.memory[memory_id] = PostMemory(
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
        self.log(draft.organization_id, "draft.exported", "draft", draft.id)
        return decision

    def schedule_draft(self, draft_id: str, scheduled_for, reason: str | None = None) -> ApprovalDecision:
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
        )
        return decision

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

    def list_draft_decisions(self, draft_id: str) -> list[ApprovalDecision]:
        self.get_draft(draft_id)
        return sorted(
            [decision for decision in self.decisions.values() if decision.draft_id == draft_id],
            key=lambda decision: decision.created_at,
        )

    def list_opportunities(self, organization_id: str) -> list[ContentOpportunity]:
        return [opportunity for opportunity in self.opportunities.values() if opportunity.organization_id == organization_id]

    def list_memory(self, organization_id: str) -> list[PostMemory]:
        return [post for post in self.memory.values() if post.organization_id == organization_id]

    def list_calendar(self, organization_id: str) -> list[Draft]:
        self.get_organization(organization_id)
        queue_statuses = {DraftStatus.approved, DraftStatus.scheduled, DraftStatus.exported}
        return sorted(
            [draft for draft in self.drafts.values() if draft.organization_id == organization_id and draft.status in queue_statuses],
            key=lambda draft: (draft.scheduled_for is None, draft.scheduled_for or draft.updated_at),
        )

    def list_audit_logs(self, organization_id: str) -> list[AuditLog]:
        return [log for log in self.audit_logs if log.organization_id == organization_id]

    def log(self, organization_id: str, action: str, entity_type: str, entity_id: str, metadata: dict | None = None) -> None:
        self.audit_logs.append(
            AuditLog(
                organization_id=organization_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata=metadata or {},
            )
        )

    def _memory_id_for_draft(self, draft: Draft) -> str:
        return f"mem_{draft.id}"
