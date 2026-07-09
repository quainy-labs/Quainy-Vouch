from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _draft_for_learning(org_id: str) -> dict:
    client.patch(
        f"/organizations/{org_id}/profile",
        json={
            "one_liner": "Turns approved notes into preference-aware updates.",
            "content_pillars": ["preference-aware updates"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org_id}/sources",
        json={
            "source_type": "text",
            "title": "Preference source",
            "raw_text": (
                "Preference-aware updates use approved notes, reviewer edits, rejection history, and human approval. "
                "The product should suggest durable profile changes but never apply them without approval. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org_id}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    return client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]


def test_preference_learning_suggests_profile_updates_from_repeated_edits_and_requires_approval():
    org = client.post("/organizations", json={"name": "Preference Org"}).json()
    draft_one = _draft_for_learning(org["id"])
    draft_two = client.post(f"/briefs/{draft_one['content_brief_id']}/drafts").json()["drafts"][1]

    client.patch(
        f"/organizations/{org['id']}/approval-policy",
        json={"required_reviewer_count": 1},
    ).raise_for_status()
    client.post(
        f"/drafts/{draft_one['id']}/approve",
        json={"edited_body": f"{draft_one['body']}\n\nReviewer edit: use source-backed and human review language."},
    ).raise_for_status()
    client.post(
        f"/drafts/{draft_two['id']}/approve",
        json={"edited_body": f"{draft_two['body']}\n\nReviewer edit: use source-backed and human review language."},
    ).raise_for_status()

    suggestions = client.post(f"/organizations/{org['id']}/preference-suggestions/generate").json()
    profile_before = client.get(f"/organizations/{org['id']}/profile").json()
    voice_suggestion = next(item for item in suggestions if item["kind"] == "voice_phrase")
    approved = client.post(
        f"/preference-suggestions/{voice_suggestion['id']}/approve",
        json={"reason": "This phrase reflects repeated edits."},
    ).json()
    profile_after = client.get(f"/organizations/{org['id']}/profile").json()
    audit = client.get(f"/organizations/{org['id']}/audit-logs").json()

    assert "source-backed" not in profile_before["preferred_phrases"]
    assert approved["status"] == "approved"
    assert "source-backed" in profile_after["preferred_phrases"]
    assert any(item["action"] == "preference_suggestion.approved" for item in audit)


def test_preference_learning_tracks_rejected_patterns_without_auto_applying():
    org = client.post("/organizations", json={"name": "Rejected Pattern Org"}).json()
    draft_one = _draft_for_learning(org["id"])
    draft_two = client.post(f"/briefs/{draft_one['content_brief_id']}/drafts").json()["drafts"][1]

    client.post(f"/drafts/{draft_one['id']}/reject", json={"reason": "Too generic and generic framing."}).raise_for_status()
    client.post(f"/drafts/{draft_two['id']}/reject", json={"reason": "Still too generic for our voice."}).raise_for_status()

    suggestions = client.post(f"/organizations/{org['id']}/preference-suggestions/generate").json()
    rejected_suggestion = next(item for item in suggestions if item["kind"] == "rejected_pattern")
    profile_before = client.get(f"/organizations/{org['id']}/profile").json()
    dismissed = client.post(
        f"/preference-suggestions/{rejected_suggestion['id']}/dismiss",
        json={"reason": "We need more examples before changing the profile."},
    ).json()
    profile_after = client.get(f"/organizations/{org['id']}/profile").json()

    assert "generic" in rejected_suggestion["proposed_update"]["banned_phrases_add"]
    assert "generic" not in profile_before["banned_phrases"]
    assert dismissed["status"] == "dismissed"
    assert profile_after["banned_phrases"] == profile_before["banned_phrases"]
