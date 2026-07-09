from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_workspace_has_local_owner_and_owner_can_manage_users():
    org = client.post("/organizations", json={"name": "Roles Org"}).json()

    users = client.get(f"/organizations/{org['id']}/users").json()
    reviewer = client.post(
        f"/organizations/{org['id']}/users",
        json={"name": "Reviewer", "email": "reviewer@example.com", "role": "reviewer"},
    ).json()
    updated = client.patch(
        f"/organizations/{org['id']}/users/{reviewer['id']}",
        json={"role": "editor"},
    ).json()

    assert any(user["id"] == "local_user" and user["role"] == "owner" for user in users)
    assert reviewer["role"] == "reviewer"
    assert updated["role"] == "editor"


def test_only_authorized_users_can_manage_sources():
    org = client.post("/organizations", json={"name": "Source Roles Org"}).json()
    viewer = client.post(
        f"/organizations/{org['id']}/users",
        json={"name": "Viewer", "email": "viewer@example.com", "role": "viewer"},
    ).json()
    editor = client.post(
        f"/organizations/{org['id']}/users",
        json={"name": "Editor", "email": "editor@example.com", "role": "editor"},
    ).json()

    viewer_create = client.post(
        f"/organizations/{org['id']}/sources?actor_id={viewer['id']}",
        json={
            "source_type": "text",
            "title": "Viewer source",
            "raw_text": "Viewer should not be able to add approved source context. " * 4,
            "approval_status": "approved",
        },
    )
    editor_create = client.post(
        f"/organizations/{org['id']}/sources?actor_id={editor['id']}",
        json={
            "source_type": "text",
            "title": "Editor source",
            "raw_text": "Editor can add approved source context for the team workspace. " * 4,
            "approval_status": "approved",
        },
    )
    source = editor_create.json()
    viewer_update = client.patch(f"/sources/{source['id']}?actor_id={viewer['id']}", json={"approval_status": "disabled"})

    assert viewer_create.status_code == 403
    assert editor_create.status_code == 200
    assert viewer_update.status_code == 403


def test_only_reviewers_or_owners_can_approve_drafts():
    org = client.post("/organizations", json={"name": "Approval Roles Org"}).json()
    viewer = client.post(
        f"/organizations/{org['id']}/users",
        json={"name": "Viewer", "email": "viewer-approval@example.com", "role": "viewer"},
    ).json()
    reviewer = client.post(
        f"/organizations/{org['id']}/users",
        json={"name": "Reviewer", "email": "reviewer-approval@example.com", "role": "reviewer"},
    ).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved notes into reviewed updates.",
            "content_pillars": ["reviewed updates"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Approval source",
            "raw_text": (
                "Reviewed updates use approved notes, source visibility, and reviewer judgment before approval. "
                "The workflow records who can approve and keeps viewers read-only. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]

    viewer_approval = client.post(f"/drafts/{draft['id']}/approve?actor_id={viewer['id']}", json={})
    reviewer_approval = client.post(
        f"/drafts/{draft['id']}/approve?actor_id={reviewer['id']}",
        json={"reason": "Reviewer approved."},
    )
    audit = client.get(f"/organizations/{org['id']}/audit-logs").json()

    assert viewer_approval.status_code == 403
    assert reviewer_approval.status_code == 200
    assert any(
        item["action"] == "draft.approved" and item["actor_id"] == reviewer["id"]
        for item in audit
    )


def test_approval_chain_requires_distinct_reviewers_before_export_and_publish():
    org = client.post("/organizations", json={"name": "Approval Chain Org"}).json()
    reviewer_one = client.post(
        f"/organizations/{org['id']}/users",
        json={"name": "Reviewer One", "email": "reviewer-one@example.com", "role": "reviewer"},
    ).json()
    reviewer_two = client.post(
        f"/organizations/{org['id']}/users",
        json={"name": "Reviewer Two", "email": "reviewer-two@example.com", "role": "reviewer"},
    ).json()
    policy = client.patch(
        f"/organizations/{org['id']}/approval-policy",
        json={"required_reviewer_count": 2, "require_approval_before_export": True, "require_approval_before_publish": True},
    ).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved notes into multi-reviewer updates.",
            "content_pillars": ["multi-reviewer updates"],
        },
    ).raise_for_status()
    client.patch(
        f"/organizations/{org['id']}/linkedin-integration",
        json={
            "selected_page_urn": "urn:li:organization:8888",
            "selected_page_name": "Approval Chain Org",
            "oauth_status": "validated",
            "permissions": ["w_organization_social"],
            "publishing_enabled": True,
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Chain source",
            "raw_text": (
                "Multi-reviewer updates use approved notes, reviewer judgment, and approval history before export. "
                "The workflow should require enough reviewers before publishing. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]

    first = client.post(
        f"/drafts/{draft['id']}/approve?actor_id={reviewer_one['id']}",
        json={"reason": "First reviewer approval."},
    ).json()
    pending = client.get(f"/drafts/{draft['id']}").json()
    blocked_export = client.post(f"/drafts/{draft['id']}/export")
    blocked_publish = client.post(f"/drafts/{draft['id']}/publish/linkedin", json={})
    second = client.post(
        f"/drafts/{draft['id']}/approve?actor_id={reviewer_two['id']}",
        json={"reason": "Second reviewer approval."},
    ).json()
    approved = client.get(f"/drafts/{draft['id']}").json()
    exported = client.post(f"/drafts/{draft['id']}/export")
    package = client.get(f"/drafts/{draft['id']}/reviewer-package").json()

    assert policy["required_reviewer_count"] == 2
    assert first["reviewer_id"] == reviewer_one["id"]
    assert pending["status"] == "pending_approval"
    assert pending["approval_metadata"]["remaining_reviewer_count"] == 1
    assert blocked_export.status_code == 409
    assert blocked_publish.status_code == 409
    assert second["reviewer_id"] == reviewer_two["id"]
    assert approved["status"] == "approved"
    assert approved["approval_metadata"]["complete"] is True
    assert exported.status_code == 200
    assert len([item for item in package["decision_history"] if item["decision"] == "approve"]) == 2


def test_risk_override_requires_reason_and_is_audited():
    org = client.post("/organizations", json={"name": "Risk Override Org"}).json()
    reviewer = client.post(
        f"/organizations/{org['id']}/users",
        json={"name": "Risk Reviewer", "email": "risk-reviewer@example.com", "role": "reviewer"},
    ).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns reviewed notes into cautious updates.",
            "content_pillars": ["cautious updates"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Risk source",
            "raw_text": (
                "Cautious updates use approved notes, reviewer judgment, and source visibility. "
                "Reviewers can flag risky claims and decide whether an override is justified. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]
    client.patch(
        f"/drafts/{draft['id']}",
        json={"body": "The company is the market leader with 99% revenue growth."},
    ).raise_for_status()

    missing_override = client.post(f"/drafts/{draft['id']}/approve?actor_id={reviewer['id']}", json={})
    approved = client.post(
        f"/drafts/{draft['id']}/approve?actor_id={reviewer['id']}",
        json={"override_reason": "Reviewer accepts this risk for a controlled test."},
    ).json()
    audit = client.get(f"/organizations/{org['id']}/audit-logs").json()

    assert missing_override.status_code == 409
    assert approved["override_reason"] == "Reviewer accepts this risk for a controlled test."
    assert any(
        item["action"] == "draft.risk_override" and item["actor_id"] == reviewer["id"]
        for item in audit
    )
