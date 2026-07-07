from __future__ import annotations

from pathlib import Path

from app.contracts import FormatAdapter
from app.format_adapters import LinkedInCompanyPostAdapter
from app.intelligence import (
    build_brief,
    content_hash,
    create_opportunities,
    duplicate_check,
    generate_drafts,
    idea_fingerprint,
    split_chunks,
)
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
    SourceStatus,
    SourceUpdate,
    now_utc,
)
from app.sample_data import QUAINY_SAMPLE_CONTEXT


class NotFoundError(Exception):
    pass


class DataStore:
    def __init__(self) -> None:
        self.organizations: dict[str, Organization] = {}
        self.profiles: dict[str, CompanyProfile] = {}
        self.sources: dict[str, Source] = {}
        self.source_raw_text: dict[str, str] = {}
        self.source_hashes: dict[str, str] = {}
        self.chunks: dict[str, SourceChunk] = {}
        self.opportunities: dict[str, ContentOpportunity] = {}
        self.briefs: dict[str, ContentBrief] = {}
        self.drafts: dict[str, Draft] = {}
        self.decisions: dict[str, ApprovalDecision] = {}
        self.memory: dict[str, PostMemory] = {}
        self.audit_logs: list[AuditLog] = []
        self.format_adapters: dict[tuple[str, str], FormatAdapter] = {}
        self.register_format_adapter(LinkedInCompanyPostAdapter())

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
        for collection in [
            self.organizations,
            self.profiles,
            self.sources,
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
        previous_status = source.approval_status
        updated = source.model_copy(update={**updates, "updated_at": now_utc()})
        self.sources[source.id] = updated
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
        digest = content_hash(raw_text)
        if self.source_hashes.get(source.id) == digest:
            return [chunk for chunk in self.chunks.values() if chunk.source_id == source.id]
        for chunk_id, chunk in list(self.chunks.items()):
            if chunk.source_id == source.id:
                del self.chunks[chunk_id]
        created: list[SourceChunk] = []
        for index, text in enumerate(split_chunks(raw_text)):
            chunk = SourceChunk(source_id=source.id, organization_id=source.organization_id, chunk_text=text, chunk_index=index)
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

    def generate_opportunities(self, organization_id: str) -> list[ContentOpportunity]:
        profile = self.profiles[organization_id]
        sources = [source for source in self.list_sources(organization_id) if source.approval_status == SourceStatus.approved]
        opportunities = create_opportunities(profile, sources, self.approved_chunks(organization_id))
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
            self.drafts[draft.id] = draft
        self.log(brief.organization_id, "drafts.generated", "brief", brief.id, {"count": len(drafts)})
        return drafts

    def update_draft_body(self, draft_id: str, body: str) -> Draft:
        draft = self.get_draft(draft_id)
        draft.body = body
        draft.duplicate_report = duplicate_check(body, self.list_memory(draft.organization_id))
        draft.updated_at = now_utc()
        self.drafts[draft.id] = draft
        self.log(draft.organization_id, "draft.edited", "draft", draft.id)
        return draft

    def approve_draft(self, draft_id: str, payload: ReviewDecisionCreate) -> ApprovalDecision:
        draft = self.get_draft(draft_id)
        if payload.edited_body:
            draft = self.update_draft_body(draft_id, payload.edited_body)
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
        draft = self.get_draft(draft_id)
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

    def list_opportunities(self, organization_id: str) -> list[ContentOpportunity]:
        return [opportunity for opportunity in self.opportunities.values() if opportunity.organization_id == organization_id]

    def list_memory(self, organization_id: str) -> list[PostMemory]:
        return [post for post in self.memory.values() if post.organization_id == organization_id]

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
