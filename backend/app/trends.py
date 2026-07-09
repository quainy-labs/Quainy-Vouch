from __future__ import annotations

from app.intelligence import retrieve_chunks, summarize, terms
from app.schemas import CalendarEvent, ContentOpportunity, Source, SourceChunk, TrendSignal


class TrendRelevanceGate:
    def evaluate(
        self,
        trend: TrendSignal,
        chunks: list[SourceChunk],
        events: list[CalendarEvent],
    ) -> tuple[bool, list[SourceChunk], list[str]]:
        query = " ".join([trend.title, trend.summary, *(trend.relevance_terms or [])])
        evidence = retrieve_chunks(query, chunks, limit=3)
        trend_terms = terms(query)
        event_matches = [
            event.title
            for event in events
            if trend_terms & (terms(event.title) | terms(event.description or "") | set(event.relevance_terms))
        ]
        warnings: list[str] = []
        if not evidence:
            warnings.append("Trend is not connected to approved company context.")
        if not event_matches:
            warnings.append("No company or public calendar event strengthens this trend.")
        return bool(evidence), evidence, warnings


class TrendOpportunityGenerator:
    def __init__(self, gate: TrendRelevanceGate | None = None) -> None:
        self.gate = gate or TrendRelevanceGate()

    def generate(
        self,
        organization_id: str,
        trends: list[TrendSignal],
        sources: list[Source],
        chunks: list[SourceChunk],
        events: list[CalendarEvent],
    ) -> list[ContentOpportunity]:
        source_by_id = {source.id: source for source in sources}
        opportunities: list[ContentOpportunity] = []
        for trend in trends:
            connected, evidence, warnings = self.gate.evaluate(trend, chunks, events)
            if not connected:
                opportunities.append(
                    ContentOpportunity(
                        organization_id=organization_id,
                        title=f"Trend warning: {trend.title}",
                        summary=trend.summary,
                        reason_today="This trend is visible, but it should not become content until connected to approved company context.",
                        source_ids=[],
                        freshness_score=0.0,
                        relevance_score=0.0,
                        confidence_score=0.2,
                        status="warned",
                        metadata={"trend_id": trend.id, "warnings": warnings, "gate": "not_connected"},
                    )
                )
                continue
            source_ids = sorted({chunk.source_id for chunk in evidence})
            freshness = self._freshness(source_ids, source_by_id)
            opportunities.append(
                ContentOpportunity(
                    organization_id=organization_id,
                    title=f"Connect trend to company context: {trend.title}",
                    summary=summarize(evidence[0].chunk_text, 190),
                    reason_today=(
                        f"The trend '{trend.title}' is connected to approved company context through "
                        f"{len(evidence)} evidence chunk(s)."
                    ),
                    source_ids=source_ids,
                    freshness_score=freshness,
                    relevance_score=0.74,
                    confidence_score=0.72,
                    metadata={"trend_id": trend.id, "warnings": warnings, "gate": "connected"},
                )
            )
        return opportunities

    def _freshness(self, source_ids: list[str], source_by_id: dict[str, Source]) -> float:
        selected = [source_by_id[source_id] for source_id in source_ids if source_id in source_by_id]
        if not selected:
            return 0.0
        fresh = [0.85 if source.last_ingested_at else 0.45 for source in selected]
        return round(sum(fresh) / len(fresh), 3)
