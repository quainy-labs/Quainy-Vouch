from datetime import datetime, timedelta, timezone

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
    assert "LinkedIn" not in brief["objective"]

    drafts = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"]
    assert len(drafts) == 3
    first = drafts[0]
    assert first["status"] == "needs_review"
    assert first["source_ids"] == brief["source_ids"]
    assert first["claims"]
    assert first["risk_report"]
    assert first["generation_metadata"]["adapter_name"] == "linkedin_company_post"
    assert first["generation_metadata"]["prompt_version"] == "linkedin_company_post.v1"
    assert first["generation_metadata"]["model_provider"] == "deterministic"
    assert first["generation_metadata"]["embedding_provider"] == "local-hash"

    package = client.get(f"/drafts/{first['id']}/reviewer-package").json()
    assert package["sources"]
    assert package["source_chunks"]

    client.post(f"/drafts/{first['id']}/approve", json={"reason": "Good enough for dogfood"}).raise_for_status()
    memory = client.get(f"/organizations/{org_id}/memory").json()
    assert any(item["source_draft_id"] == first["id"] for item in memory)


def test_same_brief_generates_linkedin_and_blog_outline():
    bootstrap = client.get("/bootstrap").json()
    org_id = bootstrap["organization"]["id"]
    opportunity = client.post(f"/organizations/{org_id}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()

    linkedin = client.post(f"/briefs/{brief['id']}/drafts?platform=linkedin&content_type=company_post").json()["drafts"][0]
    blog = client.post(f"/briefs/{brief['id']}/drafts?platform=blog&content_type=outline").json()["drafts"][0]
    newsletter = client.post(f"/briefs/{brief['id']}/drafts?platform=newsletter&content_type=email").json()["drafts"][0]
    caption = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=caption").json()["drafts"][0]
    carousel = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=carousel_outline").json()["drafts"][0]

    assert linkedin["content_brief_id"] == brief["id"]
    assert blog["content_brief_id"] == brief["id"]
    assert newsletter["content_brief_id"] == brief["id"]
    assert caption["content_brief_id"] == brief["id"]
    assert carousel["content_brief_id"] == brief["id"]
    assert linkedin["platform"] == "linkedin"
    assert blog["platform"] == "blog"
    assert newsletter["platform"] == "newsletter"
    assert caption["platform"] == "instagram"
    assert carousel["platform"] == "instagram"
    assert blog["content_type"] == "outline"
    assert newsletter["content_type"] == "email"
    assert caption["content_type"] == "caption"
    assert carousel["content_type"] == "carousel_outline"
    assert "## Introduction" in blog["body"]
    assert "Source-backed note:" in blog["body"]
    assert blog["generation_metadata"]["prompt_version"] == "blog_outline.v1"
    assert "Subject options:" in newsletter["body"]
    assert "Takeaway:" in newsletter["body"]
    assert "Sources and links:" in newsletter["body"]
    assert newsletter["generation_metadata"]["prompt_version"] == "newsletter_email.v1"
    assert "Visual direction:" in caption["body"]
    assert "Hashtags:" in caption["body"]
    assert caption["generation_metadata"]["prompt_version"] == "instagram_caption.v1"
    assert "Slide 1:" in carousel["body"]
    assert "Slide 5:" in carousel["body"]
    assert carousel["generation_metadata"]["prompt_version"] == "instagram_carousel_outline.v1"


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
    assert new_draft["duplicate_report"]["similar_posts"]
    assert new_draft["duplicate_report"]["similar_posts"][0]["platform"] == "linkedin"


def test_draft_regeneration_uses_same_brief_and_adapter():
    org = client.post("/organizations", json={"name": "Regeneration Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved research into practical updates.",
            "preferred_phrases": ["approved research"],
            "content_pillars": ["approved research"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Research note",
            "raw_text": (
                "Approved research helps the company explain practical product decisions. "
                "The source-backed workflow gives reviewers evidence before publishing. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]

    regenerated = client.post(f"/drafts/{draft['id']}/regenerate").json()["drafts"]

    assert len(regenerated) == 3
    assert {item["content_brief_id"] for item in regenerated} == {brief["id"]}
    assert {item["platform"] for item in regenerated} == {"linkedin"}
    assert all(item["source_ids"] == brief["source_ids"] for item in regenerated)


def test_edited_draft_rechecks_risks_and_blocks_unsupported_factual_approval():
    org = client.post("/organizations", json={"name": "Risk Review Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved notes into careful updates.",
            "banned_phrases": ["guaranteed market leader"],
            "content_pillars": ["careful updates"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Careful source",
            "raw_text": (
                "Careful updates should use approved notes, reviewer judgment, and source visibility. "
                "The company explains product work without invented customer or revenue claims. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]

    edited = client.patch(
        f"/drafts/{draft['id']}",
        json={"body": "The company is a guaranteed market leader with 45% revenue growth."},
    ).json()
    approval = client.post(f"/drafts/{draft['id']}/approve", json={})

    assert any(claim["support_status"] == "unsupported" for claim in edited["claims"])
    assert any("Banned or forbidden phrase" in risk for risk in edited["risk_report"])
    assert approval.status_code == 409


def test_review_package_tracks_decisions_and_reject_requires_reason():
    org = client.post("/organizations", json={"name": "Decision History Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved notes into reviewable updates.",
            "content_pillars": ["reviewable updates"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Review note",
            "raw_text": (
                "Reviewable updates use approved notes, source visibility, and human review. "
                "The reviewer can edit, approve, reject, and regenerate before export. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]

    missing_reason = client.post(f"/drafts/{draft['id']}/reject", json={})
    rejected = client.post(
        f"/drafts/{draft['id']}/reject",
        json={"edited_body": f"{draft['body']}\n\nReviewer note added.", "reason": "Needs a sharper source-backed hook."},
    )
    package = client.get(f"/drafts/{draft['id']}/reviewer-package").json()

    assert missing_reason.status_code == 422
    assert rejected.status_code == 200
    assert package["draft"]["status"] == "rejected"
    assert "Reviewer note added." in package["draft"]["body"]
    assert package["decision_history"][0]["decision"] == "reject"
    assert package["decision_history"][0]["reason"] == "Needs a sharper source-backed hook."


def test_schedule_and_export_show_in_calendar_queue_and_memory():
    org = client.post("/organizations", json={"name": "Calendar Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved context into queued updates.",
            "content_pillars": ["queued updates"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Queue source",
            "raw_text": (
                "Queued updates help reviewers approve, schedule, and export source-backed company posts. "
                "The workflow keeps manual control before anything is copied for publishing. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    drafts = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"]
    scheduled_for = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    schedule_decision = client.post(
        f"/drafts/{drafts[0]['id']}/schedule",
        json={"scheduled_for": scheduled_for, "reason": "Target next LinkedIn slot."},
    ).json()
    client.post(f"/drafts/{drafts[1]['id']}/approve", json={}).raise_for_status()
    client.post(f"/drafts/{drafts[1]['id']}/export").raise_for_status()
    calendar = client.get(f"/organizations/{org['id']}/calendar").json()
    memory = client.get(f"/organizations/{org['id']}/memory").json()

    assert schedule_decision["decision"] == "schedule"
    assert any(item["id"] == drafts[0]["id"] and item["status"] == "scheduled" for item in calendar)
    assert any(item["id"] == drafts[1]["id"] and item["status"] == "exported" and item["exported_at"] for item in calendar)
    assert any(item["source_draft_id"] == drafts[1]["id"] for item in memory)
