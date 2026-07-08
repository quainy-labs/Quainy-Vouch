from fastapi.testclient import TestClient

from app.main import app, store


client = TestClient(app)


def test_ingestion_creates_documents_chunks_hashes_and_embeddings_idempotently():
    org = client.post("/organizations", json={"name": "Ingestion Org"}).json()
    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "markdown",
            "title": "retrieval-context.md",
            "raw_text": "# Retrieval Context\n\nApproved source retrieval uses chunks, hashes, and embeddings for grounded context. " * 4,
            "approval_status": "approved",
        },
    ).json()

    first_ingest = client.post(f"/sources/{source['id']}/ingest").json()
    second_ingest = client.post(f"/sources/{source['id']}/ingest").json()

    first_chunk_ids = [chunk["id"] for chunk in first_ingest["chunks"]]
    second_chunk_ids = [chunk["id"] for chunk in second_ingest["chunks"]]

    assert first_chunk_ids == second_chunk_ids
    assert first_ingest["chunk_count"] >= 1
    assert first_ingest["chunks"][0]["source_document_id"]
    assert first_ingest["chunks"][0]["embedding"]
    assert first_ingest["chunks"][0]["metadata"]["embedding_provider"] == "local-hash"


def test_retrieval_returns_approved_chunks_with_source_ids_and_scores():
    org = client.post("/organizations", json={"name": "Retrieval Org"}).json()
    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Approved retrieval source",
            "raw_text": "Source governance and approved company memory make retrieval safe and inspectable. " * 4,
            "approval_status": "approved",
        },
    ).json()

    results = client.post(
        f"/organizations/{org['id']}/retrieval/query",
        json={"query": "approved source governance retrieval", "limit": 5},
    ).json()

    assert results
    assert results[0]["chunk"]["source_id"] == source["id"]
    assert results[0]["source"]["id"] == source["id"]
    assert results[0]["score"] > 0


def test_retrieval_filters_disabled_sources_and_other_organizations():
    org = client.post("/organizations", json={"name": "Filtered Retrieval Org"}).json()
    other_org = client.post("/organizations", json={"name": "Other Retrieval Org"}).json()
    disabled_source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Disabled retrieval source",
            "raw_text": "Private launch metric alpha beta gamma retrieval should not appear when disabled. " * 4,
            "approval_status": "disabled",
        },
    ).json()
    other_source = client.post(
        f"/organizations/{other_org['id']}/sources",
        json={
            "source_type": "text",
            "title": "Other org source",
            "raw_text": "Private launch metric alpha beta gamma retrieval belongs to another organization. " * 4,
            "approval_status": "approved",
        },
    ).json()

    results = client.post(
        f"/organizations/{org['id']}/retrieval/query",
        json={"query": "private launch metric alpha beta gamma retrieval", "limit": 10},
    ).json()

    returned_source_ids = {result["source"]["id"] for result in results}
    assert disabled_source["id"] not in returned_source_ids
    assert other_source["id"] not in returned_source_ids
    assert results == []


def test_manual_text_and_markdown_sources_are_extractable_for_retrieval():
    org = client.post("/organizations", json={"name": "Connector Coverage Org"}).json()
    manual_source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Manual source",
            "raw_text": "Manual approved context explains source visibility and reviewer confidence. " * 4,
            "approval_status": "approved",
        },
    ).json()
    markdown_source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "markdown",
            "title": "Markdown source",
            "raw_text": "## Markdown Context\n\n**Markdown approved context** explains retrieval evidence and source chunks. " * 4,
            "approval_status": "approved",
        },
    ).json()

    manual_results = client.post(
        f"/organizations/{org['id']}/retrieval/query",
        json={"query": "manual source visibility reviewer confidence", "limit": 5},
    ).json()
    markdown_results = client.post(
        f"/organizations/{org['id']}/retrieval/query",
        json={"query": "markdown retrieval evidence source chunks", "limit": 5},
    ).json()

    assert any(result["source"]["id"] == manual_source["id"] for result in manual_results)
    assert any(result["source"]["id"] == markdown_source["id"] for result in markdown_results)


def test_url_source_is_single_page_and_refresh_creates_new_document_version():
    org = client.post("/organizations", json={"name": "URL Source Org"}).json()
    invalid = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "url",
            "title": "Invalid URL",
            "uri": "ftp://example.com/page",
            "raw_text": "<html><body>Invalid page content with enough text for validation.</body></html>",
            "approval_status": "approved",
        },
    )
    assert invalid.status_code == 422

    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "url",
            "title": "Public product page",
            "uri": "https://example.com/product",
            "raw_text": (
                "<html><head><title>Ignored</title><script>private()</script></head>"
                "<body><h1>Public Product Page</h1><p>Approved website context explains source-backed public communication.</p></body></html>"
            ),
            "approval_status": "approved",
        },
    ).json()
    first_document_ids = [document.id for document in store.source_documents.values() if document.source_id == source["id"]]
    first_document = store.source_documents[first_document_ids[0]]

    assert first_document.metadata["connector"] == "url"
    assert first_document.metadata["single_page_only"] is True
    assert first_document.metadata["domain"] == "example.com"
    assert "private()" not in first_document.normalized_text
    assert "Public Product Page" in first_document.normalized_text

    client.patch(
        f"/sources/{source['id']}",
        json={
            "raw_text": (
                "<html><body><h1>Public Product Page</h1>"
                "<p>Approved website context now includes refreshed roadmap notes for reviewers.</p></body></html>"
            )
        },
    ).raise_for_status()
    client.post(f"/sources/{source['id']}/refresh").raise_for_status()
    document_ids = [document.id for document in store.source_documents.values() if document.source_id == source["id"]]

    assert len(document_ids) == 2
    assert store.latest_document_by_source[source["id"]] in document_ids


def test_github_release_source_uses_selected_public_repo_metadata_and_generates_opportunity():
    org = client.post("/organizations", json={"name": "GitHub Release Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "audience": "builders watching product releases",
            "content_pillars": ["release notes", "public changelog"],
        },
    ).raise_for_status()
    invalid = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "github_release",
            "title": "Private repo note",
            "uri": "https://gitlab.com/example/project/releases/v1.0.0",
            "raw_text": "Released: 2026-07-01\n\nPublic release notes with enough detail for validation.",
            "approval_status": "approved",
        },
    )
    assert invalid.status_code == 422

    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "github_release",
            "title": "v1.2.0 release notes",
            "uri": "https://github.com/quainy/vouch/releases/tag/v1.2.0",
            "raw_text": (
                "# v1.2.0\n\nReleased: 2026-07-01\n\n"
                "- Release notes add source-backed review workflows for builders.\n"
                "- Public changelog improves approval, export, and queue visibility.\n"
            )
            * 3,
            "approval_status": "approved",
            "freshness_days": 30,
        },
    ).json()
    document = next(document for document in store.source_documents.values() if document.source_id == source["id"])
    opportunities = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"]

    assert document.metadata["connector"] == "github_release"
    assert document.metadata["owner"] == "quainy"
    assert document.metadata["repo"] == "vouch"
    assert document.metadata["release_ref"] == "v1.2.0"
    assert document.metadata["release_date"] == "2026-07-01"
    assert document.metadata["selected_repo_only"] is True
    assert opportunities
    assert source["id"] in opportunities[0]["source_ids"]


def test_notion_selected_page_source_scope_revocation_and_audit_logs():
    org = client.post("/organizations", json={"name": "Notion Selected Page Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "audience": "reviewers using selected private context",
            "content_pillars": ["selected Notion page", "approval workflow"],
        },
    ).raise_for_status()
    invalid = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "notion_page",
            "title": "Broad workspace",
            "uri": "notion://workspace/all",
            "raw_text": "This broad workspace text should not be accepted as a selected page source.",
            "approval_status": "approved",
        },
    )
    assert invalid.status_code == 422

    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "notion_page",
            "title": "Selected launch note",
            "uri": "notion://page/abc123",
            "raw_text": (
                "# Selected Launch Note\n\n"
                "Selected Notion page context explains the approval workflow and reviewer evidence for private planning notes. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).json()
    document = next(document for document in store.source_documents.values() if document.source_id == source["id"])
    opportunities = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"]
    disabled = client.patch(f"/sources/{source['id']}", json={"approval_status": "disabled"}).json()
    after_disable = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"]
    detail = client.get(f"/sources/{source['id']}").json()

    assert document.metadata["connector"] == "notion_page"
    assert document.metadata["access_scope"] == "selected_page"
    assert document.metadata["page_id"] == "abc123"
    assert opportunities
    assert source["id"] in opportunities[0]["source_ids"]
    assert disabled["approval_status"] == "disabled"
    assert after_disable == []
    assert any(log["action"] == "source.status_changed" for log in detail["audit_logs"])
