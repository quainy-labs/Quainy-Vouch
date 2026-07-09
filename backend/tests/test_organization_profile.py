from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_organization_crud_and_validation():
    invalid = client.post("/organizations", json={"name": "   "})
    assert invalid.status_code == 422

    created = client.post(
        "/organizations",
        json={
            "name": "Sprint 1 Company",
            "website_url": "https://example.com",
            "industry": "AI tools",
            "description": "A test workspace",
            "audience_summary": "Founders and builders",
            "default_timezone": "Asia/Kolkata",
        },
    )
    created.raise_for_status()
    org = created.json()

    listed = client.get("/organizations").json()
    assert any(item["id"] == org["id"] for item in listed)

    updated = client.patch(
        f"/organizations/{org['id']}",
        json={"name": "Sprint 1 Company Updated", "audience_summary": "Builder teams"},
    ).json()
    assert updated["name"] == "Sprint 1 Company Updated"
    assert updated["audience_summary"] == "Builder teams"
    assert updated["industry"] == "AI tools"

    deleted = client.delete(f"/organizations/{org['id']}")
    receipt = deleted.json()
    assert deleted.status_code == 200
    assert receipt["organization_id"] == org["id"]
    assert receipt["deleted_by"] == "local_user"
    assert client.get(f"/organizations/{org['id']}").status_code == 404


def test_only_owner_can_delete_organization_data():
    org = client.post("/organizations", json={"name": "Deletion Permission Org"}).json()
    viewer = client.post(
        f"/organizations/{org['id']}/users",
        json={"name": "Viewer", "email": "delete-viewer@example.com", "role": "viewer"},
    ).json()

    denied = client.delete(f"/organizations/{org['id']}?actor_id={viewer['id']}")
    allowed = client.delete(f"/organizations/{org['id']}")

    assert denied.status_code == 403
    assert allowed.status_code == 200


def test_profile_update_preserves_omitted_fields_and_cleans_lists():
    org = client.post("/organizations", json={"name": "Profile Company"}).json()

    first_profile = client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "  Turns approved knowledge into public proof. ",
            "voice_rules": [" Clear and grounded ", "", "Clear and grounded"],
            "preferred_phrases": ["approved company knowledge"],
            "banned_phrases": ["go viral"],
            "approved_claims": ["The company uses approved sources."],
            "forbidden_claims": ["The product posts autonomously."],
            "content_pillars": ["trust", "source visibility"],
        },
    ).json()

    assert first_profile["one_liner"] == "Turns approved knowledge into public proof."
    assert first_profile["voice_rules"] == ["Clear and grounded"]
    assert first_profile["preferred_phrases"] == ["approved company knowledge"]

    second_profile = client.patch(
        f"/organizations/{org['id']}/profile",
        json={"mission": "Help teams communicate safely."},
    ).json()

    assert second_profile["mission"] == "Help teams communicate safely."
    assert second_profile["voice_rules"] == ["Clear and grounded"]
    assert second_profile["approved_claims"] == ["The company uses approved sources."]


def test_quainy_profile_acceptance_criteria_can_be_saved():
    created = client.post(
        "/organizations",
        json={
            "name": "Quainy Sprint Acceptance",
            "description": "Builder-first AI ecosystem.",
            "audience_summary": "Builders and curious learners.",
        },
    ).json()

    profile = client.patch(
        f"/organizations/{created['id']}/profile",
        json={
            "one_liner": "Quainy helps builders turn meaningful ideas into production-ready products.",
            "voice_rules": [
                "Serious but welcoming.",
                "Practical, curious, and source-grounded.",
                "Avoid hype and generic AI content.",
            ],
            "preferred_phrases": ["production-ready products", "product judgment"],
            "banned_phrases": ["go viral", "replace your team"],
            "approved_claims": ["Quainy is a builder-first AI ecosystem."],
            "forbidden_claims": ["Quainy guarantees engagement."],
            "content_pillars": ["product judgment", "production readiness", "human approval"],
        },
    ).json()

    assert "Serious but welcoming." in profile["voice_rules"]
    assert "product judgment" in profile["content_pillars"]
    assert "Quainy guarantees engagement." in profile["forbidden_claims"]
