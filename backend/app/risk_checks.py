from __future__ import annotations

from app.intelligence import duplicate_check, extract_claim_candidates, is_factual_claim, terms
from app.schemas import ClaimCheck, CompanyProfile, ContentOpportunity, PostMemory, SourceChunk


class SimpleClaimExtractor:
    def extract(self, body: str) -> list[str]:
        return extract_claim_candidates(body)


class SourceClaimGroundingChecker:
    def check(self, claims: list[str], chunks: list[SourceChunk]) -> list[ClaimCheck]:
        checks: list[ClaimCheck] = []
        for claim in claims:
            claim_terms = terms(claim)
            minimum_overlap = min(4, max(2, len(claim_terms) // 2))
            supporting = [
                chunk.id
                for chunk in chunks
                if claim_terms and len(claim_terms & terms(chunk.chunk_text)) >= minimum_overlap
            ][:3]
            factual = is_factual_claim(claim)
            if not factual:
                status = "not_factual"
                reason = None
            elif supporting:
                status = "supported"
                reason = None
            else:
                status = "unsupported"
                reason = "No approved source chunk has enough overlapping evidence for this factual claim."
            checks.append(
                ClaimCheck(
                    text=claim,
                    claim_type="company_fact" if factual else "general_advice",
                    confidence=0.78 if supporting else 0.46,
                    support_status=status,
                    supporting_chunk_ids=supporting,
                    risk_reason=reason,
                )
            )
        return checks[:8]


class QualityRiskChecker:
    generic_markers = ["game-changing", "revolutionary", "unlock growth", "supercharge", "10x"]

    def check(
        self,
        body: str,
        profile: CompanyProfile,
        claims: list[ClaimCheck],
        duplicate_report: dict[str, object],
        opportunity: ContentOpportunity,
    ) -> list[str]:
        risks: list[str] = []
        lowered = body.lower()
        for phrase in profile.banned_phrases + profile.forbidden_claims:
            if phrase and phrase.lower() in lowered:
                risks.append(f"Banned or forbidden phrase appears: {phrase}")
        unsupported = high_risk_unsupported_claims(claims)
        if unsupported:
            risks.append("Unsupported factual claim needs review before approval.")
        if duplicate_report.get("duplicate_score", 0) >= 0.72:
            risks.append("Possible duplicate of previously approved/exported content.")
        if opportunity.freshness_score < 0.45:
            risks.append("Sources may be stale for a timely post.")
        if self._looks_generic(body):
            risks.append("Draft may be too generic; add source-specific detail before approval.")
        if not risks:
            risks.append("No blocking risk detected. Human review still required.")
        return risks

    def _looks_generic(self, body: str) -> bool:
        lowered = body.lower()
        if any(marker in lowered for marker in self.generic_markers):
            return True
        return "source" not in lowered and "approved" not in lowered and "specific" not in lowered


def check_claims(body: str, chunks: list[SourceChunk]) -> list[ClaimCheck]:
    return SourceClaimGroundingChecker().check(SimpleClaimExtractor().extract(body), chunks)


def check_duplicate(body: str, memory: list[PostMemory]) -> dict[str, object]:
    return duplicate_check(body, memory)


def risk_check(
    body: str,
    profile: CompanyProfile,
    claims: list[ClaimCheck],
    duplicate_report: dict[str, object],
    opportunity: ContentOpportunity,
) -> list[str]:
    risks: list[str] = []
    lowered = body.lower()
    for phrase in profile.banned_phrases + profile.forbidden_claims:
        if phrase and phrase.lower() in lowered:
            risks.append(f"Banned or forbidden phrase appears: {phrase}")
    if high_risk_unsupported_claims(claims):
        risks.append("Unsupported factual claim needs review before approval.")
    if duplicate_report.get("duplicate_score", 0) >= 0.72:
        risks.append("Possible duplicate of previously approved/exported content.")
    if opportunity.freshness_score < 0.45:
        risks.append("Sources may be stale for a timely post.")
    if QualityRiskChecker()._looks_generic(body):
        risks.append("Draft may be too generic; add source-specific detail before approval.")
    if not risks:
        risks.append("No blocking risk detected. Human review still required.")
    return risks


def high_risk_unsupported_claims(claims: list[ClaimCheck]) -> list[ClaimCheck]:
    high_risk_markers = [
        "%",
        "percent",
        "revenue",
        "customers",
        "users",
        "growth",
        "guaranteed",
        "market leader",
        "fastest",
        "only company",
    ]
    return [
        claim
        for claim in claims
        if claim.support_status == "unsupported"
        and claim.claim_type != "general_advice"
        and any(marker in claim.text.lower() for marker in high_risk_markers)
    ]
