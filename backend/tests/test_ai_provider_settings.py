from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app import providers as providers_module
import app.main as main_module
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
            "generation_local_runtime": "none",
            "embedding_local_runtime": "vllm",
            "enabled": True,
        },
    )

    assert response.status_code == 200
    settings = response.json()
    assert settings["generation_api_key_env_var"] == "ACME_MODEL_KEY"
    assert settings["generation_local_runtime"] == "none"
    assert settings["embedding_local_runtime"] == "vllm"
    assert settings["generation_api_key_configured"] is True
    assert settings["embedding_api_key_configured"] is True

    audit = client.get(f"/organizations/{org['id']}/audit-logs").json()
    provider_audit = [item for item in audit if item["action"] == "ai_provider_settings.updated"][-1]
    audit_text = str(provider_audit["metadata"])
    assert "ACME_MODEL_KEY" not in audit_text
    assert "ACME_EMBED_KEY" not in audit_text


def test_ai_provider_generation_secret_reference_reads_dotenv(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("XAI_API_KEY=xai-test-key\n", encoding="utf-8")
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setattr(providers_module, "DOTENV_PATH", env_path)
    org = client.post("/organizations", json={"name": "Grok AI Settings Org"}).json()

    response = client.patch(
        f"/organizations/{org['id']}/ai-provider-settings",
        json={
            "generation_provider": "openai_compatible",
            "generation_model": "grok-4",
            "generation_base_url": "https://api.x.ai/v1",
            "generation_api_key_env_var": "XAI_API_KEY",
            "embedding_provider": "deterministic",
            "embedding_model": "local-hash",
            "enabled": True,
        },
    )

    assert response.status_code == 200
    provider = store.model_provider_for_org(org["id"])
    assert provider.provider_name == "openai_compatible"
    assert provider.model == "grok-4"
    assert provider.base_url == "https://api.x.ai/v1"
    assert provider.api_key == "xai-test-key"


def test_ai_provider_settings_accept_native_gemini_without_base_url(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    org = client.post("/organizations", json={"name": "Gemini AI Settings Org"}).json()

    response = client.patch(
        f"/organizations/{org['id']}/ai-provider-settings",
        json={
            "generation_provider": "gemini",
            "generation_model": "gemini-test-model",
            "embedding_provider": "deterministic",
            "embedding_model": "local-hash",
            "enabled": True,
        },
    )

    assert response.status_code == 200
    settings = response.json()
    assert settings["generation_provider"] == "gemini"
    assert settings["generation_base_url"] is None
    assert settings["generation_api_key_env_var"] == "GEMINI_API_KEY"
    assert settings["generation_api_key_configured"] is True
    provider = store.model_provider_for_org(org["id"])
    assert provider.provider_name == "gemini"
    assert provider.model == "gemini-test-model"
    assert provider.api_key == "gemini-test-key"


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
    assert result["generation"]["status"] == "succeeded"
    assert result["generation"]["provider"] == "deterministic"
    assert result["embedding"]["status"] == "succeeded"
    assert result["embedding"]["provider"] == "local-hash"


def test_publishing_oauth_start_uses_provider_configuration(monkeypatch):
    org = client.post("/organizations", json={"name": "Publishing OAuth Org"}).json()
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "linkedin-client")
    monkeypatch.setenv("LINKEDIN_REDIRECT_URI", "https://app.example.test/oauth/linkedin/callback")

    response = client.post(f"/organizations/{org['id']}/publishing-connections/linkedin/oauth/start")

    assert response.status_code == 200
    result = response.json()
    assert result["provider"] == "linkedin"
    assert "https://www.linkedin.com/oauth/v2/authorization" in result["authorization_url"]
    assert "client_id=linkedin-client" in result["authorization_url"]
    assert "redirect_uri=https%3A%2F%2Fapp.example.test%2Foauth%2Flinkedin%2Fcallback" in result["authorization_url"]


def test_instagram_oauth_start_reads_dotenv_configuration(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "INSTAGRAM_CLIENT_ID=instagram-client",
                "INSTAGRAM_CLIENT_SECRET=instagram-secret",
                "INSTAGRAM_REDIRECT_URI=https://app.example.test/oauth/instagram/callback",
                "INSTAGRAM_SCOPES=instagram_basic instagram_content_publish",
                "META_OAUTH_VERSION=v21.0",
            ]
        ),
        encoding="utf-8",
    )
    for name in (
        "INSTAGRAM_CLIENT_ID",
        "QUAINY_INSTAGRAM_CLIENT_ID",
        "INSTAGRAM_CLIENT_SECRET",
        "QUAINY_INSTAGRAM_CLIENT_SECRET",
        "INSTAGRAM_REDIRECT_URI",
        "QUAINY_INSTAGRAM_REDIRECT_URI",
        "INSTAGRAM_SCOPES",
        "QUAINY_INSTAGRAM_SCOPES",
        "META_OAUTH_VERSION",
        "QUAINY_META_OAUTH_VERSION",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(providers_module, "DOTENV_PATH", env_path)
    org = client.post("/organizations", json={"name": "Instagram OAuth Dotenv Org"}).json()

    response = client.post(f"/organizations/{org['id']}/publishing-connections/instagram/oauth/start")

    assert response.status_code == 200
    result = response.json()
    assert result["provider"] == "instagram"
    assert "https://www.facebook.com/v21.0/dialog/oauth" in result["authorization_url"]
    assert "client_id=instagram-client" in result["authorization_url"]
    assert "redirect_uri=https%3A%2F%2Fapp.example.test%2Foauth%2Finstagram%2Fcallback" in result["authorization_url"]


def test_publishing_oauth_start_requires_configuration(monkeypatch, tmp_path):
    org = client.post("/organizations", json={"name": "Missing OAuth Org"}).json()
    env_path = tmp_path / ".env"
    env_path.write_text("", encoding="utf-8")
    monkeypatch.delenv("QUAINY_REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("QUAINY_REDDIT_REDIRECT_URI", raising=False)
    monkeypatch.delenv("REDDIT_REDIRECT_URI", raising=False)
    monkeypatch.setattr(providers_module, "DOTENV_PATH", env_path)

    response = client.post(f"/organizations/{org['id']}/publishing-connections/reddit/oauth/start")

    assert response.status_code == 400


def test_publishing_oauth_callback_persists_token_without_returning_secret(monkeypatch):
    org = client.post("/organizations", json={"name": "Publishing Callback Org"}).json()
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "linkedin-client")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "linkedin-secret")
    monkeypatch.setenv("LINKEDIN_REDIRECT_URI", "https://app.example.test/oauth/linkedin/callback")

    def fake_exchange(provider, config, code):
        assert provider == "linkedin"
        assert code == "oauth-code"
        return {
            "access_token": "linkedin-access-token",
            "refresh_token": "linkedin-refresh-token",
            "expires_in": 3600,
            "scope": "openid w_organization_social",
        }

    def fake_metadata(provider, access_token):
        assert provider == "linkedin"
        assert access_token == "linkedin-access-token"
        return {
            "account": {"sub": "person-123", "name": "Ada Builder"},
            "targets": [{"id": "urn:li:organization:123", "name": "Acme Page"}],
        }

    monkeypatch.setattr(main_module, "exchange_publishing_oauth_code", fake_exchange)
    monkeypatch.setattr(main_module, "fetch_publishing_account_metadata", fake_metadata)
    start_response = client.post(
        f"/organizations/{org['id']}/publishing-connections/linkedin/oauth/start",
        headers={"Origin": "http://localhost:5173"},
    )
    state = parse_qs(urlparse(start_response.json()["authorization_url"]).query)["state"][0]

    response = client.get(
        "/publishing-connections/linkedin/oauth/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("http://localhost:5173/?")
    assert "oauth_provider=linkedin" in response.headers["location"]
    assert "oauth_status=connected" in response.headers["location"]

    saved = store.get_publishing_connection(org["id"], "linkedin")
    assert saved.access_token == "linkedin-access-token"
    assert saved.oauth_status == "validated"
    assert saved.access_token_configured is True
    assert saved.refresh_token_configured is True
    assert saved.selected_target_type == "company_page"
    assert saved.selected_target_id == "urn:li:organization:123"
    integration = client.get(f"/organizations/{org['id']}/linkedin-integration").json()
    assert integration["selected_page_urn"] == "urn:li:organization:123"
    assert integration["selected_page_name"] == "Acme Page"


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
