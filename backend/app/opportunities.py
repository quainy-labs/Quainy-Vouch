from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.intelligence import retrieve_chunks, summarize, terms
from app.schemas import CalendarEvent, CompanyProfile, ContentOpportunity, PostMemory, Source, SourceChunk, TrendSignal


@dataclass(frozen=True)
class OpportunityRankingSignals:
    source_support: float
    date_relevance: float
    trend_relevance: float
    audience_fit: float
    tone_fit: float
    freshness: float
    performance_fit: float
    duplicate_penalty: float

    @property
    def rank_score(self) -> float:
        score = (
            self.source_support * 0.18
            + self.date_relevance * 0.14
            + self.trend_relevance * 0.14
            + self.audience_fit * 0.13
            + self.tone_fit * 0.09
            + self.freshness * 0.17
            + self.performance_fit * 0.09
            - self.duplicate_penalty * 0.08
        )
        return round(max(0.0, min(1.0, score)), 3)

    def as_metadata(self) -> dict[str, float]:
        return {
            "source_support": round(self.source_support, 3),
            "date_relevance": round(self.date_relevance, 3),
            "trend_relevance": round(self.trend_relevance, 3),
            "audience_fit": round(self.audience_fit, 3),
            "tone_fit": round(self.tone_fit, 3),
            "freshness": round(self.freshness, 3),
            "performance_fit": round(self.performance_fit, 3),
            "duplicate_penalty": round(self.duplicate_penalty, 3),
            "rank_score": self.rank_score,
        }


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
        calendar_events: list[CalendarEvent] | None = None,
        trend_signals: list[TrendSignal] | None = None,
    ) -> list[ContentOpportunity]:
        approved_chunks = chunks[:]
        if self._context_word_count(approved_chunks) < self.minimum_context_words:
            return []
        memory = memory or []
        calendar_events = calendar_events or []
        trend_signals = trend_signals or []

        source_by_id = {source.id: source for source in sources}
        chunks_by_source: dict[str, list[SourceChunk]] = {}
        for chunk in approved_chunks:
            chunks_by_source.setdefault(chunk.source_id, []).append(chunk)

        opportunities: list[ContentOpportunity] = []
        seen_keys: set[tuple[str, tuple[str, ...]]] = set()

        recent_sources = sorted(sources, key=lambda source: source.updated_at, reverse=True)
        for source in recent_sources:
            evidence = chunks_by_source.get(source.id, [])[:3]
            if not evidence:
                continue
            source_ids = [source.id]
            topic = self._source_topic(source, evidence)
            relevance_score, confidence_score = self.relevance_scorer.score(topic, evidence, profile, memory)
            freshness_score = self.freshness_scorer.score(sources, source_ids)
            if relevance_score < 0.5 or confidence_score < 0.55:
                continue
            rank_signals = self._ranking_signals(
                topic,
                evidence,
                profile,
                memory,
                calendar_events,
                trend_signals,
                freshness_score,
                source_ids,
            )
            key = (topic.lower(), tuple(source_ids))
            seen_keys.add(key)
            opportunities.append(
                ContentOpportunity(
                    organization_id=profile.organization_id,
                    title=self._title_from_source(source, topic, profile),
                    summary=summarize(evidence[0].chunk_text, 190),
                    reason_today=self._reason_today(topic, evidence, freshness_score, calendar_events, trend_signals),
                    source_ids=source_ids,
                    freshness_score=freshness_score,
                    relevance_score=relevance_score,
                    confidence_score=confidence_score,
                    metadata={
                        "source_title": source.title,
                        "source_updated_at": source.updated_at.isoformat(),
                        "generation_basis": "approved_source",
                        "rank_signals": rank_signals.as_metadata(),
                        "rank_score": rank_signals.rank_score,
                    },
                )
            )

        return sorted(opportunities, key=self._ranking_key, reverse=True)

    def _context_word_count(self, chunks: list[SourceChunk]) -> int:
        return sum(len(chunk.chunk_text.split()) for chunk in chunks)

    def _title_from_source(self, source: Source, topic: str, profile: CompanyProfile) -> str:
        pillar = self._best_matching_pillar(topic, profile.content_pillars)
        if pillar:
            return f"Explain what {source.title} shows about {pillar}"
        return f"Explain the useful lesson from {source.title}"

    def _best_matching_pillar(self, topic: str, pillars: list[str]) -> str | None:
        topic_terms = terms(topic)
        matches = []
        for pillar in pillars:
            pillar_terms = terms(pillar)
            if not pillar_terms:
                continue
            matches.append((len(topic_terms & pillar_terms) / len(pillar_terms), pillar))
        matches = [match for match in matches if match[0] > 0]
        return max(matches, key=lambda match: match[0])[1] if matches else None

    def _display_topic(self, topic: str) -> str:
        words = topic.strip().split()
        display_words = []
        for index, word in enumerate(words):
            lower = word.lower()
            if lower == "ai":
                display_words.append("AI")
            elif lower in {"and", "or", "of", "for", "to"} and index > 0:
                display_words.append(lower)
            else:
                display_words.append(word[:1].upper() + word[1:])
        return " ".join(display_words)

    def _source_topic(self, source: Source, evidence: list[SourceChunk]) -> str:
        supporting_text = " ".join(summarize(chunk.chunk_text, 80) for chunk in evidence[:2])
        return f"{source.title} {supporting_text}".strip()

    def _ranking_key(self, opportunity: ContentOpportunity) -> tuple[float, str]:
        score = float(opportunity.metadata.get("rank_score") or 0.0)
        if score <= 0:
            score = (
                opportunity.relevance_score * 0.45
                + opportunity.confidence_score * 0.25
                + opportunity.freshness_score * 0.25
                + min(len(opportunity.source_ids), 4) * 0.0125
            )
        recency = str(opportunity.metadata.get("source_updated_at") or opportunity.created_at.isoformat())
        return (round(score, 6), recency)

    def _ranking_signals(
        self,
        topic: str,
        evidence: list[SourceChunk],
        profile: CompanyProfile,
        memory: list[PostMemory],
        calendar_events: list[CalendarEvent],
        trend_signals: list[TrendSignal],
        freshness_score: float,
        source_ids: list[str],
    ) -> OpportunityRankingSignals:
        topic_terms = terms(topic)
        evidence_terms = set().union(*(terms(chunk.chunk_text) for chunk in evidence)) if evidence else set()
        combined_terms = topic_terms | evidence_terms

        source_support = min(1.0, (min(len(source_ids), 3) / 3 * 0.45) + (min(len(evidence), 4) / 4 * 0.55))
        date_relevance = self._calendar_relevance(combined_terms, calendar_events)
        trend_relevance = self._trend_relevance(combined_terms, trend_signals)
        audience_fit = self._term_fit(terms(profile.audience or ""), combined_terms, default=0.52)
        tone_terms = set().union(*(terms(rule) for rule in profile.voice_rules)) if profile.voice_rules else set()
        tone_fit = self._term_fit(tone_terms, combined_terms, default=0.62 if profile.voice_rules else 0.5)
        performance_fit = self._performance_fit(combined_terms, memory)
        duplicate_penalty = self._duplicate_penalty(combined_terms, memory)
        return OpportunityRankingSignals(
            source_support=source_support,
            date_relevance=date_relevance,
            trend_relevance=trend_relevance,
            audience_fit=audience_fit,
            tone_fit=tone_fit,
            freshness=freshness_score,
            performance_fit=performance_fit,
            duplicate_penalty=duplicate_penalty,
        )

    def _term_fit(self, expected_terms: set[str], available_terms: set[str], default: float) -> float:
        if not expected_terms:
            return default
        return round(min(1.0, len(expected_terms & available_terms) / max(len(expected_terms), 1) + 0.35), 3)

    def _calendar_relevance(self, query_terms: set[str], events: list[CalendarEvent]) -> float:
        if not query_terms or not events:
            return 0.0
        now = datetime.now(timezone.utc)
        best = 0.0
        for event in events:
            event_terms = terms(" ".join([event.title, event.description or "", *event.relevance_terms]))
            overlap = len(query_terms & event_terms) / max(len(query_terms), 1)
            days_away = abs((event.event_date - now).total_seconds()) / 86400
            timing = 1.0 if days_away <= 14 else max(0.0, 1 - (days_away - 14) / 45)
            event_weight = 1.0 if event.event_type.value == "company" else 0.88
            best = max(best, min(1.0, overlap * 1.45 * timing * event_weight))
        return round(best, 3)

    def _trend_relevance(self, query_terms: set[str], trends: list[TrendSignal]) -> float:
        if not query_terms or not trends:
            return 0.0
        now = datetime.now(timezone.utc)
        best = 0.0
        for trend in trends:
            trend_terms = terms(" ".join([trend.title, trend.summary, trend.industry or "", *trend.relevance_terms]))
            overlap = len(query_terms & trend_terms) / max(len(query_terms), 1)
            age_days = max((now - trend.created_at).total_seconds() / 86400, 0)
            recency = max(0.25, 1 - age_days / 45)
            best = max(best, min(1.0, overlap * 1.55 * recency))
        return round(best, 3)

    def _performance_fit(self, query_terms: set[str], memory: list[PostMemory]) -> float:
        best = 0.0
        for post in memory:
            memory_terms = set(post.topic_labels) | terms(post.idea_fingerprint) | terms(post.final_body)
            shared = len(query_terms & memory_terms)
            overlap = max(shared / max(len(query_terms), 1), shared / max(len(memory_terms), 1))
            score = float(post.performance_snapshot.get("performance_score", 0.0) or 0.0)
            if overlap >= 0.25:
                best = max(best, min(1.0, score * overlap * 1.4))
        return round(best, 3)

    def _duplicate_penalty(self, query_terms: set[str], memory: list[PostMemory]) -> float:
        best = 0.0
        for post in memory:
            memory_terms = set(post.topic_labels) | terms(post.idea_fingerprint)
            shared = len(query_terms & memory_terms)
            overlap = max(shared / max(len(query_terms), 1), shared / max(len(memory_terms), 1))
            best = max(best, overlap)
        return round(min(1.0, best), 3)

    def _reason_today(
        self,
        pillar: str,
        evidence: list[SourceChunk],
        freshness_score: float,
        calendar_events: list[CalendarEvent] | None = None,
        trend_signals: list[TrendSignal] | None = None,
    ) -> str:
        if freshness_score >= 0.75:
            timing = "the supporting source context is fresh"
        elif freshness_score >= 0.45:
            timing = "the supporting source context is usable but should be reviewed for freshness"
        else:
            timing = "the supporting source context may be stale and needs careful review"
        query_terms = terms(pillar) | set().union(*(terms(chunk.chunk_text) for chunk in evidence)) if evidence else terms(pillar)
        matched_event = self._best_event_match(query_terms, calendar_events or [])
        matched_trend = self._best_trend_match(query_terms, trend_signals or [])
        context_notes = []
        if matched_event:
            context_notes.append(f"Calendar context also points to {matched_event.title}.")
        if matched_trend:
            context_notes.append(f"Trend research also points to {matched_trend.title}.")
        return (
            f"This is worth considering because approved sources contain {len(evidence)} relevant evidence chunk(s) "
            f"for {pillar.lower()}, and {timing}. {' '.join(context_notes)}".strip()
        )

    def _best_event_match(self, query_terms: set[str], events: list[CalendarEvent]) -> CalendarEvent | None:
        matches = [(self._calendar_relevance(query_terms, [event]), event) for event in events]
        matches = [match for match in matches if match[0] >= 0.18]
        return max(matches, key=lambda match: match[0])[1] if matches else None

    def _best_trend_match(self, query_terms: set[str], trends: list[TrendSignal]) -> TrendSignal | None:
        matches = [(self._trend_relevance(query_terms, [trend]), trend) for trend in trends]
        matches = [match for match in matches if match[0] >= 0.18]
        return max(matches, key=lambda match: match[0])[1] if matches else None
