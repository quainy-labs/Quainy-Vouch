from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


API_BASE = os.getenv("QUAINY_LIVE_API_BASE", "http://127.0.0.1:8000")
GENERATION_MODEL = os.getenv("QUAINY_OLLAMA_GENERATION_MODEL", "llama3.2:3b")
EMBEDDING_MODEL = os.getenv("QUAINY_OLLAMA_EMBEDDING_MODEL", "embeddinggemma:latest")
OLLAMA_BASE_URL = os.getenv("QUAINY_OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")


def request_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None, token: str | None = None) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API_BASE}{path}", data=body, method=method, headers=headers)
    try:
        with urlopen(request, timeout=240) as response:
            data = response.read().decode("utf-8")
            return json.loads(data) if data else None
    except HTTPError as error:
        detail = error.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed with {error.code}: {detail}") from error


def main() -> None:
    stamp = int(time.time())
    signup = request_json(
        "/auth/signup",
        "POST",
        {
            "name": "Ollama Workflow Owner",
            "email": f"ollama-workflow-{stamp}@example.com",
            "password": "local-ollama-workflow-pass",
            "organization_name": f"Ollama Workflow Org {stamp}",
        },
    )
    token = signup["token"]
    org_id = signup["workspace"]["organization"]["id"]

    provider_settings = request_json(
        f"/organizations/{org_id}/ai-provider-settings",
        "PATCH",
        {
            "generation_provider": "local",
            "generation_model": GENERATION_MODEL,
            "generation_base_url": OLLAMA_BASE_URL,
            "generation_api_key_env_var": None,
            "embedding_provider": "local",
            "embedding_model": EMBEDDING_MODEL,
            "embedding_base_url": OLLAMA_BASE_URL,
            "embedding_api_key_env_var": None,
            "local_runtime": "ollama",
            "enabled": True,
        },
        token,
    )
    connection = request_json(f"/organizations/{org_id}/ai-provider-settings/test", "POST", token=token)

    request_json(
        f"/organizations/{org_id}/profile",
        "PATCH",
        {
            "one_liner": "Helps AI product teams turn approved operational knowledge into trustworthy public communication.",
            "mission": "Make source-backed company communication safer and more useful.",
            "product_summary": "A communication intelligence workspace for approved sources, briefs, drafts, and performance learning.",
            "audience": "AI founders, product leaders, security reviewers, and communications teams.",
            "voice_rules": ["Concrete and source-backed", "Avoid hype", "Explain tradeoffs clearly"],
            "content_pillars": ["source-backed communication", "AI governance", "product trust", "learning from performance"],
            "approved_claims": ["The organization reviews claims before publishing public content."],
            "forbidden_claims": ["The product guarantees viral reach."],
        },
        token,
    )
    source = request_json(
        f"/organizations/{org_id}/sources",
        "POST",
        {
            "source_type": "manual_note",
            "title": "AI governance playbook launch notes",
            "raw_text": (
                "The organization published an AI governance playbook for startup teams on July 11, 2026. "
                "The playbook explains how founders can document model choices, review public claims, "
                "capture human approvals, and attach evidence to communications before publishing. "
                "Early readers asked for practical examples that connect governance work to trust-building "
                "without promising compliance guarantees. The team wants public content that is useful, "
                "specific, and careful about unsupported claims. "
            )
            * 5,
            "approval_status": "approved",
        },
        token,
    )
    generated = request_json(f"/organizations/{org_id}/opportunities/generate", "POST", token=token)
    opportunity = generated["opportunities"][0]
    brief = request_json(f"/opportunities/{opportunity['id']}/briefs", "POST", token=token)
    drafts = request_json(f"/briefs/{brief['id']}/drafts", "POST", token=token)["drafts"]
    calls = request_json(f"/organizations/{org_id}/model-calls", token=token)

    report = {
        "organization_id": org_id,
        "provider": {
            "generation_model": provider_settings["generation_model"],
            "embedding_model": provider_settings["embedding_model"],
            "connection_status": connection["status"],
            "connection_message": connection["message"],
        },
        "source": {"id": source["id"], "title": source["title"]},
        "opportunity": {
            "title": opportunity["title"],
            "model_provider": opportunity["metadata"].get("model_provider"),
            "model_suggestion": opportunity["metadata"].get("model_suggestion"),
        },
        "brief": {
            "objective": brief["objective"],
            "model_recommendation": brief["builder_metadata"].get("model_recommendation"),
        },
        "draft": {
            "model_provider": drafts[0]["generation_metadata"].get("model_provider"),
            "model": drafts[0]["generation_metadata"].get("model"),
            "body_preview": drafts[0]["body"][:500],
        },
        "model_calls": [
            {
                "schema_name": call["schema_name"],
                "provider": call["provider"],
                "model": call["model"],
                "status": call["status"],
                "error_message": call["error_message"],
            }
            for call in calls
        ],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
