from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app, store
from app.providers import ModelProviderResult
from app.schemas import OpportunityRecommendationSet


client = TestClient(app)


class OrgSpecificProvider:
    provider_name = "org-specific"
    model = "org-model-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={
                "recommendations": [
                    {
                        "title": "Explain how approved context supports public communication",
                        "summary": "Approved org source material explains how source-backed public communication works for operators.",
                        "why_now": "The approved org source is available for review and is specific enough for a public story.",
                        "confidence": 0.86,
                    }
                ]
            },
            token_usage={"total_tokens": 5},
        )


def test_ai_provider_settings_default_to_safe_deterministic_mode():
    org = client.post("/organizations", json={"name": "Default AI Settings Org"}).json()

    response = client.get(f"/organizations/{org['id']}/ai-provider-settings")

    assert response.status_code == 200
    settings = response.json()
    assert settings["generation_provider"] == "deterministic"
    assert settings["embedding_provider"] == "deterministic"
    assert settings["generation_api_key_configured"] is False
    assert settings["embedding_api_key_configured"] is False
    assert "api_key" not in settings


def test_local_model_confidence_scales_are_normalized():
    result = OpportunityRecommendationSet.model_validate(
        {
            "recommendations": [
                {
                    "title": "Governance playbook launch",
                    "summary": "Turn the playbook into a source-backed public story.",
                    "why_now": "The playbook was just released.",
                    "confidence": 8,
                },
                {
                    "title": "Approval workflow lesson",
                    "summary": "Explain how approval records reduce unsupported claims.",
                    "why_now": "Teams are asking for practical examples.",
                    "confidence": "92%",
                },
            ]
        }
    )

    assert result.recommendations[0].confidence == 0.8
    assert result.recommendations[1].confidence == 0.92


def test_ai_provider_settings_update_uses_secret_references_not_raw_secrets():
    org = client.post("/organizations", json={"name": "Secret Reference AI Org"}).json()

    response = client.patch(
        f"/organizations/{org['id']}/ai-provider-settings",
        json={
            "generation_provider": "openai_compatible",
            "generation_model": "company-generation-model",
            "generation_base_url": "https://models.example.test/v1",
            "generation_api_key_env_var": "ACME_MODEL_KEY",
            "embedding_provider": "local",
            "embedding_model": "company-embedding-model",
            "embedding_base_url": "http://local-runtime.test/v1",
            "embedding_api_key_env_var": "ACME_EMBED_KEY",
            "local_runtime": "custom",
            "enabled": True,
        },
    )

    assert response.status_code == 200
    settings = response.json()
    assert settings["generation_api_key_env_var"] == "ACME_MODEL_KEY"
    assert settings["generation_api_key_configured"] is True
    assert settings["embedding_api_key_configured"] is True

    audit = client.get(f"/organizations/{org['id']}/audit-logs").json()
    provider_audit = [item for item in audit if item["action"] == "ai_provider_settings.updated"][-1]
    audit_text = str(provider_audit["metadata"])
    assert "ACME_MODEL_KEY" not in audit_text
    assert "ACME_EMBED_KEY" not in audit_text


def test_ai_provider_settings_validate_openai_compatible_base_url():
    org = client.post("/organizations", json={"name": "Invalid AI Settings Org"}).json()

    response = client.patch(
        f"/organizations/{org['id']}/ai-provider-settings",
        json={
            "generation_provider": "openai_compatible",
            "generation_model": "company-generation-model",
            "embedding_provider": "deterministic",
            "embedding_model": "local-hash",
        },
    )

    assert response.status_code == 422


def test_ai_provider_connection_test_succeeds_for_deterministic_provider():
    org = client.post("/organizations", json={"name": "Provider Test Org"}).json()

    response = client.post(f"/organizations/{org['id']}/ai-provider-settings/test")

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "succeeded"
    assert result["provider"] == "deterministic"


def test_org_specific_provider_metadata_is_used_for_generation(monkeypatch):
    org = client.post("/organizations", json={"name": "Org Provider Metadata Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved context into public stories.",
            "audience": "operators",
            "content_pillars": ["approved context"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Approved org source",
            "raw_text": (
                "Approved org source material explains how source-backed public communication works for operators. "
                "The source is available for review and contains specific context for a public story. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    client.patch(
        f"/organizations/{org['id']}/ai-provider-settings",
        json={
            "generation_provider": "openai",
            "generation_model": "org-model-v1",
            "generation_api_key_env_var": "ORG_MODEL_KEY",
            "embedding_provider": "deterministic",
            "embedding_model": "local-hash",
            "enabled": True,
        },
    ).raise_for_status()
    monkeypatch.setattr(store, "model_provider_for_org", lambda organization_id: OrgSpecificProvider())

    response = client.post(f"/organizations/{org['id']}/opportunities/generate")

    assert response.status_code == 200
    opportunity = response.json()["opportunities"][0]
    assert opportunity["metadata"]["model_provider"] == "org-specific"
    calls = client.get(f"/organizations/{org['id']}/model-calls").json()
    assert calls[0]["provider"] == "org-specific"
    assert calls[0]["model"] == "org-model-v1"
