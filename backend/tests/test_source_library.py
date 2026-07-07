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
