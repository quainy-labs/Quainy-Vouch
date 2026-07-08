from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.opportunities import FreshnessScorer, RelevanceScorer
from app.schemas import CompanyProfile, PostMemory, Source, SourceChunk


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
