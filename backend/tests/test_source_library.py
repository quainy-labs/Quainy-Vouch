from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_manual_source_detail_and_audit_logs():
    org = client.post("/organizations", json={"name": "Source Library Org"}).json()
    created = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Weekly approved update",
            "raw_text": "Quainy Vouch is adding a source library for approved company context. " * 3,
            "approval_status": "approved",
            "freshness_days": 90,
        },
    )
    created.raise_for_status()
    source = created.json()

    detail = client.get(f"/sources/{source['id']}").json()
    assert detail["source"]["title"] == "Weekly approved update"
    assert "source library" in detail["raw_text"]
    assert detail["chunk_count"] >= 1
    assert {log["action"] for log in detail["audit_logs"]} >= {"source.created", "source.ingested"}


def test_knowledge_readiness_identifies_missing_context_and_sources():
    org = client.post("/organizations", json={"name": "Readiness Empty Org"}).json()

    readiness = client.get(f"/organizations/{org['id']}/knowledge-readiness").json()

    assert readiness["status"] == "blocked"
    assert readiness["approved_source_count"] == 0
    assert readiness["retrievable_chunk_count"] == 0
    assert any(item["action"] == "sources" for item in readiness["recommendations"])


def test_knowledge_readiness_improves_with_profile_and_approved_sources():
    org = client.post(
        "/organizations",
        json={
            "name": "Readiness Strong Org",
            "website_url": "https://example.com",
            "industry": "AI governance",
            "description": "Helps teams publish source-backed AI governance communication.",
            "audience_summary": "AI founders and communications teams",
        },
    ).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved knowledge into trustworthy public stories.",
            "mission": "Make public communication source-backed.",
            "audience": "AI founders and communication leads",
            "voice_rules": ["Concrete", "Source-backed"],
            "content_pillars": ["AI governance", "source-backed communication"],
            "approved_claims": ["The team reviews claims before publishing."],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "AI governance source",
            "raw_text": "AI governance teams need source-backed communication with approval evidence. " * 6,
            "approval_status": "approved",
            "freshness_days": 180,
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Communication source",
            "raw_text": "Source-backed communication works best when claims, approvals, and evidence are visible. " * 6,
            "approval_status": "approved",
            "freshness_days": 180,
        },
    ).raise_for_status()

    readiness = client.get(f"/organizations/{org['id']}/knowledge-readiness").json()

    assert readiness["overall_score"] >= 0.65
    assert readiness["approved_source_count"] == 2
    assert readiness["covered_pillar_count"] == 2
    assert readiness["retrievable_chunk_count"] >= 2
    assert {signal["key"] for signal in readiness["signals"]} >= {"profile", "approved_sources", "pillar_coverage", "retrieval"}


def test_markdown_text_source_can_be_added_as_approved_context():
    org = client.post("/organizations", json={"name": "Markdown Upload Org"}).json()
    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "markdown",
            "title": "approved-context.md",
            "uri": "approved-context.md",
            "raw_text": "# Product Source Of Truth\n\nQuainy Vouch turns approved company knowledge into trustworthy content. " * 3,
            "approval_status": "approved",
        },
    ).json()

    sources = client.get(f"/organizations/{org['id']}/sources").json()
    assert any(item["id"] == source["id"] and item["approval_status"] == "approved" for item in sources)


def test_disabled_source_is_not_available_to_retrieval_and_status_change_is_logged():
    org = client.post("/organizations", json={"name": "Disable Source Org"}).json()
    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Initially approved source",
            "raw_text": "This approved source contains enough unique context about source governance and company memory. " * 3,
            "approval_status": "approved",
        },
    ).json()

    generated_before_disable = client.post(f"/organizations/{org['id']}/opportunities/generate").json()
    assert generated_before_disable["opportunities"]

    updated = client.patch(f"/sources/{source['id']}", json={"approval_status": "disabled"}).json()
    assert updated["approval_status"] == "disabled"

    generated_after_disable = client.post(f"/organizations/{org['id']}/opportunities/generate").json()
    assert generated_after_disable["opportunities"] == []

    detail = client.get(f"/sources/{source['id']}").json()
    assert any(log["action"] == "source.status_changed" for log in detail["audit_logs"])
