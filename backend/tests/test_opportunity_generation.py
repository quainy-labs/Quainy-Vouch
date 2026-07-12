from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.opportunities import FreshnessScorer, OpportunityGenerator, RelevanceScorer
from app.schemas import CalendarEvent, CompanyProfile, PostMemory, Source, SourceChunk, TrendSignal


client = TestClient(app)


def test_opportunity_generation_returns_source_backed_reasons_and_scores():
    org = client.post("/organizations", json={"name": "Opportunity Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "audience": "builders and founders",
            "content_pillars": ["source-backed communication", "human approval"],
        },
    ).raise_for_status()
    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Opportunity source",
            "raw_text": (
                "Source-backed communication helps builders and founders explain approved company knowledge. "
                "Human approval keeps claims safe, relevant, and grounded in source evidence. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).json()

    result = client.post(f"/organizations/{org['id']}/opportunities/generate").json()

    assert result["opportunities"]
    opportunity = result["opportunities"][0]
    assert source["id"] in opportunity["source_ids"]
    assert opportunity["reason_today"]
    assert opportunity["relevance_score"] > 0.5
    assert opportunity["freshness_score"] > 0.5
    assert opportunity["confidence_score"] > 0.5
    assert "rank_signals" in opportunity["metadata"]
    assert opportunity["metadata"]["rank_signals"]["source_support"] > 0
    assert opportunity["metadata"]["rank_signals"]["rank_score"] > 0
    assert all(item["metadata"]["generation_basis"] == "approved_source" for item in result["opportunities"])
    assert all(not item["title"].startswith("Share a practical point of view") for item in result["opportunities"])


def test_opportunity_generation_refuses_thin_context():
    org = client.post("/organizations", json={"name": "Thin Context Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={"content_pillars": ["source-backed communication"]},
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Thin source",
            "raw_text": "Short approved note with little detail.",
            "approval_status": "approved",
        },
    ).raise_for_status()

    result = client.post(f"/organizations/{org['id']}/opportunities/generate").json()

    assert result["opportunities"] == []
    assert result["message"] == "No strong opportunity found from approved context."


def test_opportunity_can_be_marked_not_relevant_and_removed_from_active_list():
    org = client.post("/organizations", json={"name": "Dismiss Opportunity Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "audience": "builders and founders",
            "content_pillars": ["source-backed communication"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Dismissible opportunity source",
            "raw_text": (
                "Source-backed communication helps builders explain approved company knowledge with human review. "
                "The source includes concrete context for a public update and should stay grounded in evidence. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]

    dismissed = client.post(
        f"/opportunities/{opportunity['id']}/dismiss",
        json={"reason": "Not relevant to current campaign."},
    ).json()
    fetched = client.get(f"/opportunities/{opportunity['id']}").json()
    active = client.get(f"/organizations/{org['id']}/opportunities").json()
    artifacts = client.get(f"/organizations/{org['id']}/content-artifacts").json()

    assert dismissed["status"] == "dismissed"
    assert fetched["id"] == opportunity["id"]
    assert fetched["status"] == "dismissed"
    assert dismissed["metadata"]["dismissal_reason"] == "Not relevant to current campaign."
    assert all(item["id"] != opportunity["id"] for item in active)
    dismissed_artifact = next(item for item in artifacts if item["id"] == opportunity["id"])
    assert dismissed_artifact["status"] == "dismissed"


def test_relevance_scorer_penalizes_recent_memory_similarity():
    scorer = RelevanceScorer()
    profile = CompanyProfile(organization_id="org_test", audience="builders")
    evidence = [
        SourceChunk(
            source_id="src_test",
            organization_id="org_test",
            chunk_text="Source-backed communication gives builders safer public proof from approved knowledge.",
            chunk_index=0,
        )
    ]

    fresh_score, _ = scorer.score("source-backed communication", evidence, profile, [])
    penalized_score, _ = scorer.score(
        "source-backed communication",
        evidence,
        profile,
        [
            PostMemory(
                organization_id="org_test",
                platform="linkedin",
                content_type="company_post",
                final_body="Previously approved source-backed communication post.",
                source_draft_id="draft_test",
                topic_labels=["source-backed", "communication"],
                idea_fingerprint="source-backed communication approved knowledge",
            )
        ],
    )

    assert penalized_score < fresh_score


def test_relevance_scorer_uses_performance_as_capped_signal():
    scorer = RelevanceScorer()
    profile = CompanyProfile(organization_id="org_test", audience="builders")
    evidence = [
        SourceChunk(
            source_id="src_test",
            organization_id="org_test",
            chunk_text="Product judgment gives builders safer public proof from approved knowledge.",
            chunk_index=0,
        )
    ]

    baseline_score, _ = scorer.score("product judgment", evidence, profile, [])
    performance_score, _ = scorer.score(
        "product judgment",
        evidence,
        profile,
        [
            PostMemory(
                organization_id="org_test",
                platform="linkedin",
                content_type="company_post",
                final_body="Previously approved product learning post.",
                source_draft_id="draft_test",
                topic_labels=["product", "learning"],
                idea_fingerprint="product learning approved knowledge",
                performance_snapshot={"performance_score": 1.0, "metrics": {"impressions": 1000}},
            )
        ],
    )

    assert performance_score > baseline_score
    assert performance_score - baseline_score <= 0.041


def test_opportunity_ranking_uses_calendar_trends_and_performance_context():
    now = datetime.now(timezone.utc)
    generator = OpportunityGenerator()
    profile = CompanyProfile(
        organization_id="org_rank",
        audience="builders and education teams",
        voice_rules=["Concrete and source-backed"],
        content_pillars=["AI education", "billing operations"],
    )
    ai_source = Source(
        id="src_ai",
        organization_id="org_rank",
        source_type="text",
        title="AI education source",
        approval_status="approved",
        last_ingested_at=now,
        updated_at=now,
    )
    billing_source = Source(
        id="src_billing",
        organization_id="org_rank",
        source_type="text",
        title="Billing operations source",
        approval_status="approved",
        last_ingested_at=now,
        updated_at=now,
    )
    chunks = [
        SourceChunk(
            source_id=ai_source.id,
            organization_id="org_rank",
            chunk_text=(
                "AI education helps builders and education teams understand approved source-backed product judgment. "
                "Teams use concrete examples, human review, and trusted evidence before public communication. "
            )
            * 3,
            chunk_index=0,
        ),
        SourceChunk(
            source_id=billing_source.id,
            organization_id="org_rank",
            chunk_text=(
                "Billing operations teams coordinate invoices, account status, payment review, and renewal workflows. "
                "The approved source explains finance handoffs and customer account hygiene. "
            )
            * 3,
            chunk_index=0,
        ),
    ]
    memory = [
        PostMemory(
            organization_id="org_rank",
            platform="linkedin",
            content_type="company_post",
            final_body="AI education post for builders with source-backed examples performed well.",
            source_draft_id="draft_rank",
            topic_labels=["ai", "education", "builders"],
            idea_fingerprint="ai education builders source-backed",
            performance_snapshot={"performance_score": 0.92},
        )
    ]
    event = CalendarEvent(
        organization_id="org_rank",
        title="AI Education Week",
        event_date=now,
        event_type="public",
        description="Public event about AI education for builders.",
        relevance_terms=["ai", "education", "builders"],
    )
    trend = TrendSignal(
        organization_id="org_rank",
        title="AI education demand",
        summary="Builders are looking for source-backed AI education.",
        industry="AI education",
        relevance_terms=["ai", "education", "source-backed"],
    )

    opportunities = generator.generate(profile, [ai_source, billing_source], chunks, memory, [event], [trend])

    assert opportunities
    assert opportunities[0].source_ids == [ai_source.id]
    signals = opportunities[0].metadata["rank_signals"]
    assert signals["date_relevance"] > 0
    assert signals["trend_relevance"] > 0
    assert signals["performance_fit"] > 0
    assert "Calendar context also points to AI Education Week." in opportunities[0].reason_today
    assert "Trend research also points to AI education demand." in opportunities[0].reason_today


def test_freshness_scorer_flags_stale_sources():
    scorer = FreshnessScorer()
    fresh = Source(
        id="src_fresh",
        organization_id="org_test",
        source_type="text",
        title="Fresh",
        approval_status="approved",
        freshness_days=30,
        last_ingested_at=datetime.now(timezone.utc),
    )
    stale = Source(
        id="src_stale",
        organization_id="org_test",
        source_type="text",
        title="Stale",
        approval_status="approved",
        freshness_days=1,
        last_ingested_at=datetime.now(timezone.utc) - timedelta(days=10),
    )

    assert scorer.score([fresh], ["src_fresh"]) > scorer.score([stale], ["src_stale"])
