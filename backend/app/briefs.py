from __future__ import annotations

from app.prompt_registry import prompt_versions
from app.schemas import CompanyProfile, ContentBrief, ContentOpportunity, SourceChunk


class PlatformIndependentBriefBuilder:
    prompt_version = prompt_versions.version("brief_builder")

    def build(
        self,
        profile: CompanyProfile,
        opportunity: ContentOpportunity,
        chunks: list[SourceChunk],
    ) -> ContentBrief:
        evidence = self._evidence_for_opportunity(opportunity, chunks)
        supporting_points = [summarize(chunk.chunk_text, 320) for chunk in evidence]
        claims = extract_claim_candidates(" ".join(supporting_points))[:5]
        risks = self._risks(profile, opportunity, supporting_points)
        do_not_say = self._do_not_say(profile)

        return ContentBrief(
            opportunity_id=opportunity.id,
            organization_id=opportunity.organization_id,
            objective="Create a source-grounded company communication brief that a format adapter can safely render.",
            audience=profile.audience or "builders, founders, developers, and curious learners",
            key_message=opportunity.title,
            supporting_points=supporting_points,
            claims=claims,
            do_not_say=do_not_say,
            source_ids=opportunity.source_ids,
            risks=risks,
            prompt_version=self.prompt_version,
            builder_metadata={
                "builder": self.__class__.__name__,
                "evidence_chunk_ids": [chunk.id for chunk in evidence],
                "opportunity_confidence_score": opportunity.confidence_score,
            },
        )

    def _risks(
        self,
        profile: CompanyProfile,
        opportunity: ContentOpportunity,
        supporting_points: list[str],
    ) -> list[str]:
        risks: list[str] = []
        if opportunity.confidence_score < 0.72:
            risks.append("Context is thin; keep wording cautious and avoid broad claims.")
        if not supporting_points:
            risks.append("No supporting approved chunks were available for this opportunity.")
        if profile.sensitive_topics:
            risks.append("Sensitive topics exist in the voice profile and require reviewer attention.")
        return risks

    def _do_not_say(self, profile: CompanyProfile) -> list[str]:
        do_not_say = [*profile.banned_phrases, *profile.forbidden_claims]
        if not do_not_say:
            do_not_say.append("Do not invent metrics, customer names, partnerships, or launch details.")
        return do_not_say

    def _evidence_for_opportunity(
        self,
        opportunity: ContentOpportunity,
        chunks: list[SourceChunk],
    ) -> list[SourceChunk]:
        selected = [chunk for chunk in chunks if chunk.source_id in opportunity.source_ids]
        preferred_ids = opportunity.metadata.get("evidence_chunk_ids")
        if not isinstance(preferred_ids, list) or not preferred_ids:
            return selected[:4]
        preferred_order = {str(chunk_id): index for index, chunk_id in enumerate(preferred_ids)}
        return sorted(
            selected,
            key=lambda chunk: (preferred_order.get(chunk.id, 10_000), chunk.source_id, chunk.chunk_index),
        )[:4]


def build_brief(profile: CompanyProfile, opportunity: ContentOpportunity, chunks: list[SourceChunk]) -> ContentBrief:
    return PlatformIndependentBriefBuilder().build(profile, opportunity, chunks)


def summarize(text: str, max_chars: int) -> str:
    from app.intelligence import normalize_text

    clean = normalize_text(text.replace("#", ""))
    if len(clean) <= max_chars:
        return clean
    window = clean[: max_chars - 1].rstrip()
    sentence_end = max(window.rfind("."), window.rfind("?"), window.rfind("!"))
    if sentence_end >= int(max_chars * 0.45):
        return window[: sentence_end + 1]
    return window.rsplit(" ", 1)[0].rstrip(" ,;:") + "."


def extract_claim_candidates(text: str) -> list[str]:
    from app.intelligence import extract_claim_candidates as extract

    return extract(text)
