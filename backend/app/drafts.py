from __future__ import annotations

from app.contracts import FormatAdapter
from app.risk_checks import check_claims, check_duplicate, risk_check
from app.schemas import CompanyProfile, ContentBrief, ContentOpportunity, Draft, PostMemory, SourceChunk


class SourceGroundedDraftGenerator:
    def generate(
        self,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
        chunks: list[SourceChunk],
        memory: list[PostMemory],
        adapter: FormatAdapter,
    ) -> list[Draft]:
        drafts: list[Draft] = []
        generation_spec = adapter.generation_spec(brief)
        evidence_chunks = [chunk for chunk in chunks if chunk.source_id in brief.source_ids]
        for variant in adapter.variants():
            rendered = adapter.render(variant, profile, brief, opportunity)
            body = rendered.body
            claims = check_claims(body, evidence_chunks)
            duplicate_report = check_duplicate(body, memory)
            risk_report = risk_check(body, profile, claims, duplicate_report, opportunity)
            quality_report = adapter.quality_checks(body, profile, brief)
            source_map = {claim.text: claim.supporting_chunk_ids for claim in claims if claim.supporting_chunk_ids}
            drafts.append(
                Draft(
                    content_brief_id=brief.id,
                    organization_id=brief.organization_id,
                    platform=adapter.platform,
                    content_type=adapter.content_type,
                    body=body,
                    hook=rendered.hook,
                    hashtags=rendered.hashtags,
                    source_ids=brief.source_ids,
                    source_map=source_map,
                    risk_report=risk_report,
                    quality_report=quality_report,
                    duplicate_report=duplicate_report,
                    claims=claims,
                    generation_metadata=generation_spec.model_dump(mode="json"),
                )
            )
        return drafts


def generate_drafts(
    profile: CompanyProfile,
    brief: ContentBrief,
    opportunity: ContentOpportunity,
    chunks: list[SourceChunk],
    memory: list[PostMemory],
    adapter: FormatAdapter,
) -> list[Draft]:
    return SourceGroundedDraftGenerator().generate(profile, brief, opportunity, chunks, memory, adapter)
