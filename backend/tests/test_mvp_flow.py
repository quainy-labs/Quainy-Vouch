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


def test_same_brief_generates_supported_social_posts():
    bootstrap = client.get("/bootstrap").json()
    org_id = bootstrap["organization"]["id"]
    opportunity = client.post(f"/organizations/{org_id}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()

    linkedin = client.post(f"/briefs/{brief['id']}/drafts?platform=linkedin&content_type=company_post").json()["drafts"][0]
    reddit = client.post(f"/briefs/{brief['id']}/drafts?platform=reddit&content_type=post").json()["drafts"][0]
    instagram = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=post").json()["drafts"][0]

    assert linkedin["content_brief_id"] == brief["id"]
    assert reddit["content_brief_id"] == brief["id"]
    assert instagram["content_brief_id"] == brief["id"]
    assert linkedin["platform"] == "linkedin"
    assert reddit["platform"] == "reddit"
    assert instagram["platform"] == "instagram"
    assert linkedin["content_type"] == "company_post"
    assert reddit["content_type"] == "post"
    assert instagram["content_type"] == "post"
    assert reddit["generation_metadata"]["prompt_version"] == "reddit_post.v1"
    assert "Subreddit fit:" in reddit["body"]
    assert "Discussion question:" in reddit["body"]
    assert instagram["generation_metadata"]["prompt_version"] == "instagram_post.v1"
    assert "Visual direction:" in instagram["body"]
    assert "Post copy:" in instagram["body"]
    assert "Hashtags:" in instagram["body"]

    old_blog = client.post(f"/briefs/{brief['id']}/drafts?platform=blog&content_type=outline")
    old_newsletter = client.post(f"/briefs/{brief['id']}/drafts?platform=newsletter&content_type=email")
    old_carousel = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=carousel_outline")
    assert old_blog.status_code == 404
    assert old_newsletter.status_code == 404
    assert old_carousel.status_code == 404


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


def test_linkedin_publish_requires_approved_draft_and_selected_company_page():
    org = client.post("/organizations", json={"name": "Publishing Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved context into reviewed company posts.",
            "content_pillars": ["reviewed company posts"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Publishing source",
            "raw_text": (
                "Reviewed company posts use approved context, source visibility, and human approval before publishing. "
                "Publishing should preserve approved content and record provider results. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts?platform=linkedin&content_type=company_post").json()["drafts"][0]

    blocked = client.post(
        f"/drafts/{draft['id']}/publish/linkedin",
        json={"page_urn": "urn:li:organization:1234", "page_name": "Publishing Org"},
    )
    assert blocked.status_code == 409

    integration = client.patch(
        f"/organizations/{org['id']}/linkedin-integration",
        json={
            "selected_page_urn": "urn:li:organization:1234",
            "selected_page_name": "Publishing Org",
            "oauth_status": "validated",
            "permissions": ["w_organization_social", "r_organization_social"],
            "publishing_enabled": True,
        },
    ).json()
    client.post(f"/drafts/{draft['id']}/approve", json={"reason": "Ready for company page"}).raise_for_status()
    result = client.post(f"/drafts/{draft['id']}/publish/linkedin", json={"reason": "Publish approved post"}).json()
    updated = client.get(f"/drafts/{draft['id']}").json()
    memory = client.get(f"/organizations/{org['id']}/memory").json()
    audit = client.get(f"/organizations/{org['id']}/audit-logs").json()

    assert integration["selected_page_urn"] == "urn:li:organization:1234"
    assert result["status"] == "published"
    assert result["page_urn"] == "urn:li:organization:1234"
    assert result["provider_post_id"]
    assert updated["status"] == "published"
    assert updated["published_at"]
    assert updated["publish_result"]["status"] == "published"
    assert any(item["source_draft_id"] == draft["id"] and item["published_at"] for item in memory)
    assert any(item["action"] == "draft.published" and item["entity_id"] == draft["id"] for item in audit)


def test_linkedin_publish_failure_preserves_approved_content():
    org = client.post("/organizations", json={"name": "Publish Failure Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved context into resilient publishing workflows.",
            "content_pillars": ["resilient publishing"],
        },
    ).raise_for_status()
    client.patch(
        f"/organizations/{org['id']}/linkedin-integration",
        json={
            "selected_page_urn": "urn:li:organization:5678",
            "selected_page_name": "Publish Failure Org",
            "oauth_status": "validated",
            "permissions": ["w_organization_social"],
            "publishing_enabled": True,
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Failure source",
            "raw_text": (
                "A resilient publishing workflow keeps approved content available when provider publishing fails. "
                "The reviewer can still export manually and see an auditable failure reason. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts?platform=linkedin&content_type=company_post").json()["drafts"][0]
    client.post(f"/drafts/{draft['id']}/approve", json={"reason": "Approved before provider attempt"}).raise_for_status()

    result = client.post(f"/drafts/{draft['id']}/publish/linkedin", json={"simulate_failure": True}).json()
    updated = client.get(f"/drafts/{draft['id']}").json()
    audit = client.get(f"/organizations/{org['id']}/audit-logs").json()

    assert result["status"] == "failed"
    assert result["failure_reason"]
    assert updated["status"] == "approved"
    assert updated["body"] == draft["body"]
    assert updated["publish_result"]["status"] == "failed"
    assert any(item["action"] == "draft.publish_failed" and item["entity_id"] == draft["id"] for item in audit)


def test_analytics_import_and_manual_metrics_update_post_memory_dashboard():
    org = client.post("/organizations", json={"name": "Analytics Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved context into measurable company posts.",
            "content_pillars": ["measurable company posts"],
        },
    ).raise_for_status()
    client.patch(
        f"/organizations/{org['id']}/linkedin-integration",
        json={
            "selected_page_urn": "urn:li:organization:9012",
            "selected_page_name": "Analytics Org",
            "oauth_status": "validated",
            "permissions": ["w_organization_social", "r_organization_social"],
            "publishing_enabled": True,
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Analytics source",
            "raw_text": (
                "Measurable company posts still need approved source context, reviewer approval, and careful analytics. "
                "Performance can inform learning but should not replace truth or brand rules. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts?platform=linkedin&content_type=company_post").json()["drafts"][0]
    client.post(f"/drafts/{draft['id']}/approve", json={"reason": "Ready for analytics"}).raise_for_status()
    client.post(f"/drafts/{draft['id']}/publish/linkedin", json={}).raise_for_status()

    imported = client.post(f"/organizations/{org['id']}/analytics/import").json()
    dashboard = client.get(f"/organizations/{org['id']}/analytics").json()
    memory_id = imported[0]["id"]
    manual = client.post(
        f"/memory/{memory_id}/performance",
        json={
            "impressions": 500,
            "reactions": 50,
            "comments": 10,
            "shares": 5,
            "clicks": 25,
            "source": "manual",
            "notes": "Fallback metrics entry.",
        },
    ).json()
    manual_dashboard = client.get(f"/organizations/{org['id']}/analytics").json()
    artifacts = client.get(f"/organizations/{org['id']}/content-artifacts").json()
    strategy = client.get(f"/organizations/{org['id']}/strategy").json()
    audit = client.get(f"/organizations/{org['id']}/audit-logs").json()

    assert imported[0]["performance_snapshot"]["source"] == "linkedin-analytics-local"
    assert dashboard["posts_analyzed"] == 1
    assert dashboard["top_posts"][0]["source_draft_id"] == draft["id"]
    assert manual["performance_snapshot"]["source"] == "manual"
    assert manual_dashboard["total_impressions"] == 500
    assert manual_dashboard["total_reactions"] == 50
    assert manual_dashboard["total_comments"] == 10
    assert manual_dashboard["total_shares"] == 5
    assert manual_dashboard["total_clicks"] == 25
    assert any(item["kind"] == "draft" and item["id"] == draft["id"] for item in artifacts)
    assert any(item["kind"] == "memory" and item["id"] == memory_id and item["status"] == "published" for item in artifacts)
    assert strategy["pillar_coverage"][0]["pillar"] == "measurable company posts"
    assert strategy["pillar_coverage"][0]["source_count"] > 0
    assert strategy["performance_by_platform"][0]["key"] == "linkedin"
    assert strategy["performance_by_platform"][0]["posts"] == 1
    assert strategy["performance_by_platform"][0]["impressions"] == 500
    assert strategy["performance_by_content_type"][0]["key"] == "company_post"
    assert strategy["performance_by_content_type"][0]["average_score"] > 0
    assert strategy["topic_repetition"]
    assert strategy["suggested_directions"]
    assert strategy["suggested_directions"][0]["source_basis"]
    assert any(item["action"] == "analytics.imported" for item in audit)
    assert any(item["action"] == "memory.performance_recorded" for item in audit)
