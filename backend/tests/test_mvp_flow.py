from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_seeded_quainy_flow_generates_reviewable_draft_and_memory():
    bootstrap = client.get("/bootstrap").json()
    org_id = bootstrap["organization"]["id"]

    opportunities = client.post(f"/organizations/{org_id}/opportunities/generate").json()["opportunities"]
    assert opportunities
    assert opportunities[0]["source_ids"]

    brief = client.post(f"/opportunities/{opportunities[0]['id']}/briefs").json()
    assert brief["source_ids"]

    drafts = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"]
    assert len(drafts) == 3
    first = drafts[0]
    assert first["status"] == "needs_review"
    assert first["claims"]
    assert first["risk_report"]

    package = client.get(f"/drafts/{first['id']}/reviewer-package").json()
    assert package["sources"]
    assert package["source_chunks"]

    client.post(f"/drafts/{first['id']}/approve", json={"reason": "Good enough for dogfood"}).raise_for_status()
    memory = client.get(f"/organizations/{org_id}/memory").json()
    assert any(item["source_draft_id"] == first["id"] for item in memory)


def test_disabled_sources_are_not_used_for_generation():
    org = client.post(
        "/organizations",
        json={
            "name": "Privacy Startup",
            "description": "A careful team",
            "audience_summary": "Security-sensitive founders",
        },
    ).json()
    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "title": "Disabled private note",
            "raw_text": "This team has a confidential launch metric that should not become public content. " * 3,
            "approval_status": "disabled",
        },
    ).json()
    assert source["approval_status"] == "disabled"

    generated = client.post(f"/organizations/{org['id']}/opportunities/generate").json()
    assert generated["opportunities"] == []


def test_approval_creates_duplicate_signal_for_future_drafts():
    bootstrap = client.get("/bootstrap").json()
    org_id = bootstrap["organization"]["id"]
    opportunity = client.post(f"/organizations/{org_id}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]

    client.post(f"/drafts/{draft['id']}/approve", json={}).raise_for_status()
    new_draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]

    assert new_draft["duplicate_report"]["duplicate_score"] >= 0.72
