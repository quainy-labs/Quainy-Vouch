from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app, store
from app.providers import ModelProviderResult


client = TestClient(app)


class InvalidStructuredProvider:
    provider_name = "invalid-test-provider"
    model = "invalid-output-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"not": "the requested schema"},
            token_usage={"total_tokens": 3},
        )


def create_context_org(name: str) -> dict:
    org = client.post("/organizations", json={"name": name}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved context into public stories with reviewer control.",
            "audience": "founders and operators",
            "content_pillars": ["reviewer control", "approved context"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": f"{name} approved source",
            "raw_text": (
                "Approved context helps the organization create public stories with reviewer control, "
                "source visibility, cautious claims, and useful operator-facing lessons. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    return org


def test_structured_model_calls_are_logged_and_attached_to_artifacts():
    org = create_context_org("Model Call Org")

    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]
    calls = client.get(f"/organizations/{org['id']}/model-calls").json()
    schemas = {call["schema_name"] for call in calls}

    assert opportunity["metadata"]["model_call_id"]
    assert brief["builder_metadata"]["model_call_id"]
    assert draft["generation_metadata"]["model_call_id"]
    assert {"OpportunityRecommendationSet", "BriefRecommendation", "DraftRecommendationSet"}.issubset(schemas)
    assert all(call["status"] == "succeeded" for call in calls)
    assert all("prompt_hash" in call and call["prompt_hash"] for call in calls)


def test_invalid_structured_model_output_fails_safe_and_is_logged():
    org = create_context_org("Invalid Model Output Org")
    original_provider = store.model_provider
    store.model_provider = InvalidStructuredProvider()
    try:
        opportunities = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"]
        brief = client.post(f"/opportunities/{opportunities[0]['id']}/briefs").json()
        draft = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]
    finally:
        store.model_provider = original_provider

    calls = client.get(f"/organizations/{org['id']}/model-calls").json()

    assert opportunities
    assert draft["body"]
    assert any(call["status"] == "failed" and call["provider"] == "invalid-test-provider" for call in calls)
    assert all(call["prompt_hash"] for call in calls)
