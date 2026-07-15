from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


def env_value(name: str, legacy_name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or os.getenv(legacy_name) or default


def env_enabled(name: str, legacy_name: str) -> bool:
    return (env_value(name, legacy_name, "0") or "0").lower() in {"1", "true", "yes"}


API_BASE = (env_value("VOUCH_API_BASE", "QUAINY_API_BASE", "http://127.0.0.1:8000") or "http://127.0.0.1:8000").rstrip("/")


def request(method: str, path: str, payload: dict | None = None, token: str | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API_BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed with {error.code}: {detail}") from error


def main() -> None:
    suffix = int(time.time())
    existing_email = env_value("VOUCH_SMOKE_EMAIL", "QUAINY_SMOKE_EMAIL")
    password = env_value("VOUCH_SMOKE_PASSWORD", "QUAINY_SMOKE_PASSWORD", "docker-smoke-pass")
    existing_token = env_value("VOUCH_SMOKE_TOKEN", "QUAINY_SMOKE_TOKEN")
    if existing_token:
        token = existing_token
        workspace = request("GET", "/me", token=token)
        org_id = workspace["organization"]["id"]
        source_id = None
    elif existing_email:
        auth = request("POST", "/auth/login", {"email": existing_email, "password": password})
        token = auth["token"]
        org_id = auth["workspace"]["organization"]["id"]
        source_id = None
    else:
        auth = request(
            "POST",
            "/auth/signup",
            {
                "name": "Docker Smoke Owner",
                "email": f"docker-smoke-{suffix}@example.com",
                "password": password,
                "organization_name": f"Docker Smoke Org {suffix}",
                "industry": "Production validation",
            },
        )
        token = auth["token"]
        org_id = auth["workspace"]["organization"]["id"]
        source = request(
            "POST",
            f"/organizations/{org_id}/sources",
            {
                "source_type": "manual_note",
                "title": "Docker smoke approved context",
                "raw_text": (
                    "Docker smoke context verifies that signup, organization setup, source persistence, "
                    "document extraction, and chunk ingestion work through the live Postgres backend. "
                )
                * 4,
                "approval_status": "approved",
            },
            token,
        )
        source_id = source["id"]
    artifact_summary = None
    read_artifacts = env_enabled("VOUCH_SMOKE_READ_ARTIFACTS", "QUAINY_SMOKE_READ_ARTIFACTS")
    if env_enabled("VOUCH_SMOKE_ARTIFACTS", "QUAINY_SMOKE_ARTIFACTS"):
        opportunities = request("POST", f"/organizations/{org_id}/opportunities/generate", token=token)["opportunities"]
        if not opportunities:
            raise RuntimeError("Artifact smoke could not generate an opportunity from approved context.")
        brief = request("POST", f"/opportunities/{opportunities[0]['id']}/briefs", token=token)
        drafts = request("POST", f"/briefs/{brief['id']}/drafts", token=token)["drafts"]
        if not drafts:
            raise RuntimeError("Artifact smoke could not generate drafts.")
        request("POST", f"/drafts/{drafts[0]['id']}/approve", {"reason": "Live Postgres artifact smoke."}, token)
        artifacts = request("GET", f"/organizations/{org_id}/content-artifacts", token=token)
        artifact_summary = {
            "opportunity_id": opportunities[0]["id"],
            "brief_id": brief["id"],
            "draft_id": drafts[0]["id"],
            "artifact_count": len(artifacts),
            "artifact_kinds": sorted({item["kind"] for item in artifacts}),
        }
    elif read_artifacts:
        artifacts = request("GET", f"/organizations/{org_id}/content-artifacts", token=token)
        artifact_summary = {
            "artifact_count": len(artifacts),
            "artifact_kinds": sorted({item["kind"] for item in artifacts}),
        }
    workspace = request("GET", "/me", token=token)
    result = {
        "account_email": workspace["account"]["email"],
        "organization_id": org_id,
        "source_id": source_id,
        "source_count": len(workspace["sources"]),
        "onboarding_steps": workspace["onboarding"]["completed_steps"],
    }
    if env_enabled("VOUCH_SMOKE_PRINT_TOKEN", "QUAINY_SMOKE_PRINT_TOKEN"):
        result["token"] = token
    if artifact_summary:
        result["artifacts"] = artifact_summary
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
