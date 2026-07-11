from fastapi.testclient import TestClient

from app.main import app, store
from app.schemas import JobKind


client = TestClient(app)


def test_source_ingestion_runs_through_tracked_job():
    org = client.post("/organizations", json={"name": "Job Source Org"}).json()
    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Job tracked source",
            "raw_text": "Background jobs should track source ingestion, logs, status, and result metadata. " * 4,
            "approval_status": "approved",
        },
    ).json()

    jobs = client.get(f"/organizations/{org['id']}/jobs").json()
    source_jobs = [job for job in jobs if job["kind"] == "source_ingest" and job["entity_id"] == source["id"]]
    detail = client.get(f"/jobs/{source_jobs[0]['id']}").json()

    assert source_jobs[0]["status"] == "succeeded"
    assert source_jobs[0]["attempt_count"] == 1
    assert source_jobs[0]["result"]["chunk_count"] > 0
    assert [log["message"] for log in detail["logs"]] == ["Job queued.", "Job started.", "Job completed."]


def test_generation_and_publish_operations_create_job_history():
    org = client.post("/organizations", json={"name": "Job Content Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns durable job records into reliable content workflows.",
            "content_pillars": ["reliable content workflows"],
        },
    ).raise_for_status()
    client.patch(
        f"/organizations/{org['id']}/linkedin-integration",
        json={
            "selected_page_urn": "urn:li:organization:5151",
            "selected_page_name": "Job Content Org",
            "oauth_status": "validated",
            "permissions": ["w_organization_social"],
            "publishing_enabled": True,
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Job content source",
            "raw_text": (
                "Reliable content workflows use durable background job history for opportunities, drafts, "
                "publishing, analytics, and recovery. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()

    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]
    client.post(f"/drafts/{draft['id']}/approve", json={"reason": "Ready for job tracked publishing."}).raise_for_status()
    client.post(f"/drafts/{draft['id']}/publish/linkedin", json={}).raise_for_status()
    client.post(f"/organizations/{org['id']}/analytics/import").raise_for_status()

    kinds = [job["kind"] for job in client.get(f"/organizations/{org['id']}/jobs").json()]

    assert "opportunity_generation" in kinds
    assert "draft_generation" in kinds
    assert "linkedin_publish" in kinds
    assert "analytics_import" in kinds


def test_failed_job_can_be_retried_with_logs_and_attempt_count():
    org = client.post("/organizations", json={"name": "Retry Job Org"}).json()
    source = client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Retry source",
            "raw_text": "Retryable jobs should preserve failure logs and then run the source again successfully. " * 4,
            "approval_status": "approved",
        },
    ).json()
    job = store.create_job(org["id"], "local_user", JobKind.source_refresh, "source", source["id"], {"source_id": source["id"]})
    store.start_job(job.id)
    store.fail_job(job.id, RuntimeError("simulated refresh failure"))

    retried = client.post(f"/jobs/{job.id}/retry").json()
    messages = [log["message"] for log in retried["logs"]]

    assert retried["job"]["status"] == "succeeded"
    assert retried["job"]["attempt_count"] == 2
    assert "Job failed." in messages
    assert messages[-1] == "Job completed."
