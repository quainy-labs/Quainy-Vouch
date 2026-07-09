from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_connected_trend_generates_source_backed_opportunity():
    org = client.post("/organizations", json={"name": "Trend Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved context into trend-aware updates.",
            "content_pillars": ["source-backed AI education"],
        },
    ).raise_for_status()
    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "AI education source",
            "raw_text": (
                "Source-backed AI education helps builders understand product judgment, approved context, "
                "and human review before public communication. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).json()
    event = client.post(
        f"/organizations/{org['id']}/calendar-events",
        json={
            "title": "AI Education Week",
            "event_date": datetime.now(timezone.utc).isoformat(),
            "event_type": "public",
            "description": "Public event about AI education for builders.",
            "relevance_terms": ["ai", "education", "builders"],
        },
    ).json()
    trend = client.post(
        f"/organizations/{org['id']}/trend-signals",
        json={
            "title": "AI education demand",
            "summary": "Builders are looking for source-backed AI education.",
            "industry": "AI education",
            "relevance_terms": ["ai", "education", "source-backed"],
        },
    ).json()

    generated = client.post(f"/organizations/{org['id']}/trend-opportunities/generate").json()["opportunities"]
    connected = [item for item in generated if item["metadata"]["gate"] == "connected"]

    assert event["event_type"] == "public"
    assert trend["title"] == "AI education demand"
    assert connected
    assert source["id"] in connected[0]["source_ids"]
    assert connected[0]["metadata"]["trend_id"] == trend["id"]
    assert connected[0]["relevance_score"] > 0


def test_irrelevant_trend_is_warned_not_source_backed():
    org = client.post("/organizations", json={"name": "Trend Warning Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={"content_pillars": ["source-backed communication"]},
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Communication source",
            "raw_text": (
                "Source-backed communication uses approved context, reviewer control, and human approval. "
                "The company writes about product judgment and careful public content. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    trend = client.post(
        f"/organizations/{org['id']}/trend-signals",
        json={
            "title": "Coffee bean futures",
            "summary": "Commodity traders are watching coffee bean futures.",
            "industry": "Commodities",
            "relevance_terms": ["coffee", "futures"],
        },
    ).json()

    generated = client.post(f"/organizations/{org['id']}/trend-opportunities/generate").json()["opportunities"]
    warning = [item for item in generated if item["metadata"]["trend_id"] == trend["id"]][0]

    assert warning["status"] == "warned"
    assert warning["source_ids"] == []
    assert warning["metadata"]["gate"] == "not_connected"
    assert "not connected" in warning["metadata"]["warnings"][0].lower()
