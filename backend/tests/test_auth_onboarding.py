from fastapi.testclient import TestClient

from app.main import app, fixture_mode, store


client = TestClient(app)


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_fixture_mode_blocks_deterministic_seed_in_production(monkeypatch):
    monkeypatch.setenv("QUAINY_ENV", "production")
    monkeypatch.setenv("QUAINY_ENABLE_DEV_SEED", "true")

    try:
        fixture_mode()
    except RuntimeError as error:
        assert "Deterministic fixtures cannot be enabled" in str(error)
    else:
        raise AssertionError("Production mode must not allow deterministic fixtures.")


def test_fixture_mode_keeps_test_memory_seed_available(monkeypatch):
    monkeypatch.delenv("QUAINY_ENV", raising=False)
    monkeypatch.delenv("QUAINY_DATA_BACKEND", raising=False)
    monkeypatch.delenv("QUAINY_ENABLE_DEV_SEED", raising=False)
    monkeypatch.delenv("QUAINY_FIXTURE_MODE", raising=False)

    assert fixture_mode() == "sample"


def test_signup_login_and_current_workspace_start_from_user_organization():
    signup = client.post(
        "/auth/signup",
        json={
            "name": "Asha Founder",
            "email": "asha-founder@example.com",
            "password": "production-ready",
            "organization_name": "Asha Labs",
            "website_url": "https://asha.example",
            "industry": "AI operations",
            "description": "Asha Labs turns operational lessons into public company communication.",
            "audience_summary": "Operators, founders, and technical teams.",
            "default_timezone": "Asia/Kolkata",
        },
    )
    assert signup.status_code == 200
    body = signup.json()
    token = body["token"]
    workspace = body["workspace"]

    current = client.get("/me", headers=auth_header(token)).json()
    login = client.post(
        "/auth/login",
        json={"email": "ASHA-founder@example.com", "password": "production-ready"},
    ).json()

    assert workspace["account"]["email"] == "asha-founder@example.com"
    assert workspace["organization"]["name"] == "Asha Labs"
    assert workspace["user"]["role"] == "owner"
    assert workspace["user"]["id"] == workspace["account"]["id"]
    assert "local_user" not in {user["id"] for user in client.get(f"/organizations/{workspace['organization']['id']}/users").json()}
    assert current["organization"]["id"] == workspace["organization"]["id"]
    assert login["workspace"]["organization"]["id"] == workspace["organization"]["id"]


def test_signup_stores_password_as_non_reversible_hash():
    password = "never-store-this-password"
    signup = client.post(
        "/auth/signup",
        json={
            "name": "Secure Owner",
            "email": "secure-owner@example.com",
            "password": password,
            "organization_name": "Secure Org",
        },
    )
    assert signup.status_code == 200
    account_id = signup.json()["workspace"]["account"]["id"]
    stored_hash = store.account_password_hashes[account_id]

    assert stored_hash.startswith("pbkdf2_sha256$")
    assert password not in stored_hash
    assert store._verify_password(password, stored_hash) is True


def test_onboarding_can_skip_profile_and_add_source_with_auth_token():
    signup = client.post(
        "/auth/signup",
        json={
            "name": "Mira Maker",
            "email": "mira-maker@example.com",
            "password": "source-backed",
            "organization_name": "Mira Studio",
            "industry": "Design systems",
        },
    ).json()
    token = signup["token"]
    org_id = signup["workspace"]["organization"]["id"]

    skipped = client.post(
        f"/organizations/{org_id}/onboarding/profile",
        json={"skip_profile": True},
        headers=auth_header(token),
    ).json()
    source = client.post(
        f"/organizations/{org_id}/sources",
        json={
            "source_type": "manual_note",
            "title": "Approved launch notes",
            "raw_text": (
                "Mira Studio helps one-person companies turn weekly product lessons into public stories. "
                "The studio values specific evidence, calm tone, and useful launch notes. "
            )
            * 3,
            "approval_status": "approved",
        },
        headers=auth_header(token),
    ).json()
    current = client.get("/me", headers=auth_header(token)).json()

    assert skipped["profile_skipped"] is True
    assert "profile_skipped" in skipped["completed_steps"]
    assert source["title"] == "Approved launch notes"
    assert any(item["id"] == source["id"] for item in current["sources"])
    assert "source_added" in current["onboarding"]["completed_steps"]
    assert current["onboarding"]["completion_percent"] >= skipped["completion_percent"]


def test_authenticated_profile_and_content_steps_update_onboarding_progress():
    signup = client.post(
        "/auth/signup",
        json={
            "name": "Leo Lead",
            "email": "leo-lead@example.com",
            "password": "context-builds",
            "organization_name": "Signal Craft",
            "industry": "B2B software",
        },
    ).json()
    token = signup["token"]
    org_id = signup["workspace"]["organization"]["id"]
    headers = auth_header(token)

    client.patch(
        f"/organizations/{org_id}/profile",
        json={
            "one_liner": "Signal Craft turns customer support insights into source-backed product stories.",
            "audience": "B2B product leaders and support teams.",
            "content_pillars": ["support insights", "source-backed product stories"],
            "voice_rules": ["Clear, useful, and evidence-led."],
        },
        headers=headers,
    ).raise_for_status()
    client.post(
        f"/organizations/{org_id}/sources",
        json={
            "source_type": "manual_note",
            "title": "Support insight source",
            "raw_text": (
                "Support insights help Signal Craft identify repeated customer questions, product friction, "
                "and lessons worth sharing publicly with evidence and reviewer approval. "
            )
            * 5,
            "approval_status": "approved",
        },
        headers=headers,
    ).raise_for_status()

    opportunity = client.post(f"/organizations/{org_id}/opportunities/generate", headers=headers).json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs", headers=headers).json()
    draft = client.post(f"/briefs/{brief['id']}/drafts", headers=headers).json()["drafts"][0]
    current = client.get("/me", headers=headers).json()

    assert "profile_started" in current["onboarding"]["completed_steps"]
    assert "source_added" in current["onboarding"]["completed_steps"]
    assert "first_opportunity_generated" in current["onboarding"]["completed_steps"]
    assert "first_brief_created" in current["onboarding"]["completed_steps"]
    assert "first_draft_created" in current["onboarding"]["completed_steps"]
    assert draft["organization_id"] == org_id


def test_authentication_is_required_and_tokens_cannot_manage_other_org_sources():
    first = client.post(
        "/auth/signup",
        json={
            "name": "First Owner",
            "email": "first-owner@example.com",
            "password": "first-owner-pass",
            "organization_name": "First Org",
        },
    ).json()
    second = client.post(
        "/auth/signup",
        json={
            "name": "Second Owner",
            "email": "second-owner@example.com",
            "password": "second-owner-pass",
            "organization_name": "Second Org",
        },
    ).json()

    unauthenticated = client.get("/me")
    cross_org = client.post(
        f"/organizations/{second['workspace']['organization']['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Cross org source",
            "raw_text": "This source should not be accepted because the token belongs to another organization. " * 3,
            "approval_status": "approved",
        },
        headers=auth_header(first["token"]),
    )

    assert unauthenticated.status_code == 401
    assert cross_org.status_code == 404


def test_authenticated_tokens_are_enforced_on_later_workflow_mutations():
    first = client.post(
        "/auth/signup",
        json={
            "name": "Route Sweep Owner",
            "email": "route-sweep-owner@example.com",
            "password": "route-sweep-pass",
            "organization_name": "Route Sweep Org",
        },
    ).json()
    second = client.post(
        "/auth/signup",
        json={
            "name": "Other Route Owner",
            "email": "other-route-owner@example.com",
            "password": "other-route-pass",
            "organization_name": "Other Route Org",
        },
    ).json()
    org_id = first["workspace"]["organization"]["id"]
    headers = auth_header(first["token"])

    client.patch(
        f"/organizations/{org_id}/profile",
        json={
            "one_liner": "Turns source-backed route checks into safer content workflows.",
            "content_pillars": ["source-backed route checks"],
        },
        headers=headers,
    ).raise_for_status()
    client.post(
        f"/organizations/{org_id}/sources",
        json={
            "source_type": "manual_note",
            "title": "Route sweep source",
            "raw_text": (
                "Route sweep source material supports safer content workflows, reviewer checks, "
                "draft editing, publishing decisions, and evidence-backed public posts. "
            )
            * 4,
            "approval_status": "approved",
        },
        headers=headers,
    ).raise_for_status()

    opportunity = client.post(f"/organizations/{org_id}/opportunities/generate", headers=headers).json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs", headers=headers).json()
    draft = client.post(f"/briefs/{brief['id']}/drafts", headers=headers).json()["drafts"][0]

    invalid_token = client.patch(
        f"/drafts/{draft['id']}",
        json={"body": "Updated draft body should not save with a bad token."},
        headers=auth_header("not-a-real-token"),
    )
    cross_org = client.patch(
        f"/drafts/{draft['id']}",
        json={"body": "Updated draft body should not save from another organization."},
        headers=auth_header(second["token"]),
    )
    calendar_invalid_token = client.post(
        f"/organizations/{org_id}/calendar-events",
        json={
            "title": "Launch window",
            "event_date": "2026-08-01T09:00:00Z",
            "event_type": "company",
            "description": "A calendar mutation should require a valid token when supplied.",
        },
        headers=auth_header("not-a-real-token"),
    )

    assert invalid_token.status_code == 401
    assert cross_org.status_code == 404
    assert calendar_invalid_token.status_code == 401
