from __future__ import annotations

import hashlib
import re
from collections import Counter
from difflib import SequenceMatcher

from app.contracts import FormatAdapter
from app.schemas import ClaimCheck, CompanyProfile, ContentBrief, ContentOpportunity, Draft, PostMemory, Source, SourceChunk


STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "before",
    "being",
    "build",
    "can",
    "company",
    "content",
    "from",
    "have",
    "help",
    "into",
    "more",
    "should",
    "that",
    "their",
    "there",
    "this",
    "through",
    "what",
    "when",
    "with",
    "without",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).lower().encode("utf-8")).hexdigest()


def split_chunks(text: str, target_words: int = 95) -> list[str]:
    paragraphs = [normalize_text(part) for part in re.split(r"\n\s*\n", text) if normalize_text(part)]
    chunks: list[str] = []
    current: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if len(current) + len(words) > target_words and current:
            chunks.append(" ".join(current))
            current = []
        current.extend(words)
    if current:
        chunks.append(" ".join(current))
    return chunks


def terms(text: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())
        if term not in STOPWORDS
    }


def score_chunk(query: str, chunk: SourceChunk) -> float:
    query_terms = terms(query)
    if not query_terms:
        return 0
    chunk_terms = terms(chunk.chunk_text)
    overlap = len(query_terms & chunk_terms)
    return overlap / max(len(query_terms), 1)


def retrieve_chunks(query: str, chunks: list[SourceChunk], limit: int = 6) -> list[SourceChunk]:
    ranked = sorted(chunks, key=lambda chunk: score_chunk(query, chunk), reverse=True)
    return [chunk for chunk in ranked if score_chunk(query, chunk) > 0][:limit]


def create_opportunities(profile: CompanyProfile, sources: list[Source], chunks: list[SourceChunk]) -> list[ContentOpportunity]:
    approved_chunks = chunks[:]
    if not approved_chunks:
        return []

    pillars = profile.content_pillars or ["approved context", "product judgment", "production readiness"]
    opportunities: list[ContentOpportunity] = []
    for pillar in pillars[:5]:
        evidence = retrieve_chunks(pillar, approved_chunks, limit=3)
        if not evidence:
            continue
        source_ids = sorted({chunk.source_id for chunk in evidence})
        summary = summarize(evidence[0].chunk_text, 190)
        title = title_from_pillar(pillar)
        opportunities.append(
            ContentOpportunity(
                organization_id=profile.organization_id,
                title=title,
                summary=summary,
                reason_today=(
                    "This is worth communicating now because the approved source library contains "
                    f"specific context tied to {pillar.lower()}, and it can become public proof without broad internal access."
                ),
                source_ids=source_ids,
                freshness_score=freshness_score(sources, source_ids),
                relevance_score=min(0.95, 0.62 + (0.08 * len(evidence))),
                confidence_score=min(0.95, 0.65 + (0.06 * len(source_ids))),
            )
        )

    if not opportunities:
        first = approved_chunks[0]
        opportunities.append(
            ContentOpportunity(
                organization_id=profile.organization_id,
                title="Turn approved company context into a clear public update",
                summary=summarize(first.chunk_text, 190),
                reason_today="The approved source library has enough context to make a cautious, source-backed update.",
                source_ids=[first.source_id],
                freshness_score=freshness_score(sources, [first.source_id]),
                relevance_score=0.68,
                confidence_score=0.7,
            )
        )
    return opportunities


def build_brief(profile: CompanyProfile, opportunity: ContentOpportunity, chunks: list[SourceChunk]) -> ContentBrief:
    evidence = [chunk for chunk in chunks if chunk.source_id in opportunity.source_ids][:4]
    supporting_points = [summarize(chunk.chunk_text, 150) for chunk in evidence]
    claims = extract_claim_candidates(" ".join(supporting_points))[:5]
    risks = []
    if opportunity.confidence_score < 0.72:
        risks.append("Context is thin; keep the draft cautious and avoid broad claims.")
    return ContentBrief(
        opportunity_id=opportunity.id,
        organization_id=opportunity.organization_id,
        objective="Share a useful, source-grounded LinkedIn company update.",
        audience=profile.audience or "builders, founders, developers, and curious learners",
        key_message=opportunity.title,
        supporting_points=supporting_points,
        claims=claims,
        source_ids=opportunity.source_ids,
        risks=risks,
    )


def generate_drafts(
    profile: CompanyProfile,
    brief: ContentBrief,
    opportunity: ContentOpportunity,
    chunks: list[SourceChunk],
    memory: list[PostMemory],
    adapter: FormatAdapter,
) -> list[Draft]:
    drafts: list[Draft] = []
    for variant in adapter.variants():
        rendered = adapter.render(variant, profile, brief, opportunity)
        body = rendered.body
        claims = check_claims(body, chunks)
        duplicate_report = duplicate_check(body, memory)
        risk_report = risk_check(body, profile, claims, duplicate_report, opportunity)
        quality_report = adapter.quality_checks(body, profile)
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
                source_map=source_map,
                risk_report=risk_report,
                quality_report=quality_report,
                duplicate_report=duplicate_report,
                claims=claims,
            )
        )
    return drafts


def check_claims(body: str, chunks: list[SourceChunk]) -> list[ClaimCheck]:
    candidates = extract_claim_candidates(body)
    checks: list[ClaimCheck] = []
    for claim in candidates:
        claim_terms = terms(claim)
        supporting = [
            chunk.id
            for chunk in chunks
            if claim_terms and len(claim_terms & terms(chunk.chunk_text)) >= min(3, max(1, len(claim_terms) // 3))
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
                claim_type="company_fact" if "Quainy" in claim else "general_advice",
                confidence=0.78 if supporting else 0.46,
                support_status=status,
                supporting_chunk_ids=supporting,
                risk_reason=reason,
            )
        )
    return checks[:8]


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
    unsupported = [claim.text for claim in claims if claim.support_status == "unsupported" and claim.claim_type != "general_advice"]
    if unsupported:
        risks.append("Unsupported factual claim needs review before approval.")
    if duplicate_report.get("duplicate_score", 0) >= 0.72:
        risks.append("Possible duplicate of previously approved/exported content.")
    if opportunity.freshness_score < 0.45:
        risks.append("Sources may be stale for a timely post.")
    if not risks:
        risks.append("No blocking risk detected. Human review still required.")
    return risks


def duplicate_check(body: str, memory: list[PostMemory]) -> dict[str, object]:
    fingerprint = idea_fingerprint(body)
    matches = []
    best = 0.0
    for post in memory:
        score = max(
            SequenceMatcher(None, normalize_text(body).lower(), normalize_text(post.final_body).lower()).ratio(),
            SequenceMatcher(None, fingerprint, post.idea_fingerprint).ratio(),
        )
        best = max(best, score)
        if score >= 0.55:
            matches.append({"post_memory_id": post.id, "score": round(score, 2), "excerpt": summarize(post.final_body, 140)})
    return {"duplicate_score": round(best, 2), "similar_posts": matches[:3]}


def idea_fingerprint(text: str) -> str:
    counts = Counter(term for term in terms(text) if len(term) > 4)
    return " ".join(term for term, _count in counts.most_common(8))


def summarize(text: str, max_chars: int) -> str:
    clean = normalize_text(re.sub(r"#+\s*", "", text))
    return clean if len(clean) <= max_chars else clean[: max_chars - 1].rstrip() + "..."


def title_from_pillar(pillar: str) -> str:
    title = pillar.strip().capitalize()
    if not title:
        title = "Approved company knowledge"
    return f"Share Quainy's point of view on {title}"


def freshness_score(sources: list[Source], source_ids: list[str]) -> float:
    selected = [source for source in sources if source.id in source_ids]
    if not selected:
        return 0.0
    return 0.82


def extract_claim_candidates(text: str) -> list[str]:
    sentences = [normalize_text(sentence) for sentence in re.split(r"(?<=[.!?])\s+", text) if normalize_text(sentence)]
    return [sentence for sentence in sentences if len(sentence.split()) >= 7]


def is_factual_claim(claim: str) -> bool:
    factual_markers = ["Quainy", "is", "are", "uses", "helps", "contains", "connects", "being built"]
    return any(marker in claim for marker in factual_markers)
