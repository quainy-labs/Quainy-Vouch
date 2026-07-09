from __future__ import annotations

from datetime import datetime, timezone

from app.intelligence import retrieve_chunks, summarize, terms
from app.schemas import CompanyProfile, ContentOpportunity, PostMemory, Source, SourceChunk


class FreshnessScorer:
    def score(self, sources: list[Source], source_ids: list[str]) -> float:
        selected = [source for source in sources if source.id in source_ids]
        if not selected:
            return 0.0
        scores = [self._score_source(source) for source in selected]
        return round(sum(scores) / len(scores), 3)

    def _score_source(self, source: Source) -> float:
        if not source.last_ingested_at:
            return 0.45
        now = datetime.now(timezone.utc)
        age_days = max((now - source.last_ingested_at).days, 0)
        freshness_days = max(source.freshness_days, 1)
        return max(0.1, round(1 - (age_days / freshness_days), 3))


class RelevanceScorer:
    def score(
        self,
        pillar: str,
        evidence: list[SourceChunk],
        profile: CompanyProfile,
        memory: list[PostMemory],
    ) -> tuple[float, float]:
        if not evidence:
            return 0.0, 0.0

        pillar_terms = terms(pillar)
        audience_terms = terms(profile.audience or "")
        evidence_terms = set().union(*(terms(chunk.chunk_text) for chunk in evidence))
        pillar_overlap = len(pillar_terms & evidence_terms) / max(len(pillar_terms), 1)
        audience_bonus = min(0.12, len(audience_terms & evidence_terms) * 0.02)
        evidence_bonus = min(0.18, len(evidence) * 0.06)
        duplicate_penalty = self._memory_penalty(pillar, memory)
        performance_bonus = self._performance_bonus(pillar, memory)

        relevance = min(0.98, max(0.0, 0.48 + pillar_overlap * 0.28 + audience_bonus + evidence_bonus + performance_bonus - duplicate_penalty))
        confidence = min(0.97, max(0.0, 0.52 + evidence_bonus + min(0.2, len(evidence_terms) / 80)))
        return round(relevance, 3), round(confidence, 3)

    def _memory_penalty(self, pillar: str, memory: list[PostMemory]) -> float:
        pillar_terms = terms(pillar)
        if not pillar_terms:
            return 0.0
        for post in memory:
            memory_terms = set(post.topic_labels) | terms(post.idea_fingerprint)
            if len(pillar_terms & memory_terms) / len(pillar_terms) >= 0.7:
                return 0.16
        return 0.0

    def _performance_bonus(self, pillar: str, memory: list[PostMemory]) -> float:
        pillar_terms = terms(pillar)
        if not pillar_terms:
            return 0.0
        best_score = 0.0
        for post in memory:
            memory_terms = set(post.topic_labels) | terms(post.idea_fingerprint)
            overlap = len(pillar_terms & memory_terms) / len(pillar_terms)
            score = float(post.performance_snapshot.get("performance_score", 0.0) or 0.0)
            if overlap >= 0.5:
                best_score = max(best_score, score)
        return min(0.04, best_score * 0.04)


class OpportunityGenerator:
    minimum_context_words = 35

    def __init__(self, freshness_scorer: FreshnessScorer | None = None, relevance_scorer: RelevanceScorer | None = None) -> None:
        self.freshness_scorer = freshness_scorer or FreshnessScorer()
        self.relevance_scorer = relevance_scorer or RelevanceScorer()

    def generate(
        self,
        profile: CompanyProfile,
        sources: list[Source],
        chunks: list[SourceChunk],
        memory: list[PostMemory] | None = None,
    ) -> list[ContentOpportunity]:
        approved_chunks = chunks[:]
        if self._context_word_count(approved_chunks) < self.minimum_context_words:
            return []

        source_by_id = {source.id: source for source in sources}
        chunks_by_source: dict[str, list[SourceChunk]] = {}
        for chunk in approved_chunks:
            chunks_by_source.setdefault(chunk.source_id, []).append(chunk)

        pillars = profile.content_pillars or ["approved context", "source-backed communication", "human approval"]
        opportunities: list[ContentOpportunity] = []
        seen_keys: set[tuple[str, tuple[str, ...]]] = set()

        recent_sources = sorted(sources, key=lambda source: source.updated_at, reverse=True)
        for source in recent_sources:
            evidence = chunks_by_source.get(source.id, [])[:3]
            if not evidence:
                continue
            source_ids = [source.id]
            topic = self._source_topic(source, evidence)
            relevance_score, confidence_score = self.relevance_scorer.score(topic, evidence, profile, memory or [])
            freshness_score = self.freshness_scorer.score(sources, source_ids)
            if relevance_score < 0.5 or confidence_score < 0.55:
                continue
            key = (topic.lower(), tuple(source_ids))
            seen_keys.add(key)
            opportunities.append(
                ContentOpportunity(
                    organization_id=profile.organization_id,
                    title=f"Turn {source.title} into a source-backed update",
                    summary=summarize(evidence[0].chunk_text, 190),
                    reason_today=self._reason_today(topic, evidence, freshness_score),
                    source_ids=source_ids,
                    freshness_score=freshness_score,
                    relevance_score=relevance_score,
                    confidence_score=confidence_score,
                    metadata={
                        "source_title": source.title,
                        "source_updated_at": source.updated_at.isoformat(),
                        "generation_basis": "approved_source",
                    },
                )
            )

        for pillar in pillars[:5]:
            evidence = retrieve_chunks(pillar, approved_chunks, limit=3)
            if not evidence:
                continue
            source_ids = sorted({chunk.source_id for chunk in evidence})
            key = (pillar.lower(), tuple(source_ids))
            if key in seen_keys or any(source_by_id.get(source_id) is None for source_id in source_ids):
                continue
            relevance_score, confidence_score = self.relevance_scorer.score(pillar, evidence, profile, memory or [])
            freshness_score = self.freshness_scorer.score(sources, source_ids)
            if relevance_score < 0.52 or confidence_score < 0.55:
                continue
            opportunities.append(
                ContentOpportunity(
                    organization_id=profile.organization_id,
                    title=self._title_from_pillar(pillar),
                    summary=summarize(evidence[0].chunk_text, 190),
                    reason_today=self._reason_today(pillar, evidence, freshness_score),
                    source_ids=source_ids,
                    freshness_score=freshness_score,
                    relevance_score=relevance_score,
                    confidence_score=confidence_score,
                    metadata={"generation_basis": "content_pillar", "pillar": pillar},
                )
            )

        return sorted(opportunities, key=self._ranking_key, reverse=True)

    def _context_word_count(self, chunks: list[SourceChunk]) -> int:
        return sum(len(chunk.chunk_text.split()) for chunk in chunks)

    def _title_from_pillar(self, pillar: str) -> str:
        title = pillar.strip().capitalize() or "Approved company knowledge"
        return f"Share the company's point of view on {title}"

    def _source_topic(self, source: Source, evidence: list[SourceChunk]) -> str:
        supporting_text = " ".join(summarize(chunk.chunk_text, 80) for chunk in evidence[:2])
        return f"{source.title} {supporting_text}".strip()

    def _ranking_key(self, opportunity: ContentOpportunity) -> tuple[float, str]:
        score = (
            opportunity.relevance_score * 0.45
            + opportunity.confidence_score * 0.25
            + opportunity.freshness_score * 0.25
            + min(len(opportunity.source_ids), 4) * 0.0125
        )
        recency = str(opportunity.metadata.get("source_updated_at") or opportunity.created_at.isoformat())
        return (round(score, 6), recency)

    def _reason_today(self, pillar: str, evidence: list[SourceChunk], freshness_score: float) -> str:
        if freshness_score >= 0.75:
            timing = "the supporting source context is fresh"
        elif freshness_score >= 0.45:
            timing = "the supporting source context is usable but should be reviewed for freshness"
        else:
            timing = "the supporting source context may be stale and needs careful review"
        return (
            f"This is worth considering because approved sources contain {len(evidence)} relevant evidence chunk(s) "
            f"for {pillar.lower()}, and {timing}."
        )
