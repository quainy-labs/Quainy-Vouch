import pytest

import openai
from app.prompt_registry import prompt_versions
from app.publishing import LinkedInPublishingAdapter, build_linkedin_publisher
from app.providers import (
    DeterministicModelProvider,
    GeminiModelProvider,
    LocalHashEmbeddingProvider,
    OpenAIEmbeddingProvider,
    OpenAIModelProvider,
    build_embedding_provider,
    build_model_provider,
    resolve_secret_reference,
)


def test_prompt_registry_returns_known_versions():
    assert prompt_versions.version("brief_builder") == "brief_builder.v1"
    assert prompt_versions.version("opportunity_generation") == "opportunity_generation.v1"
    assert prompt_versions.version("draft_generation") == "draft_generation.v1"
    assert prompt_versions.version("claim_extraction") == "claim_extraction.v1"
    assert prompt_versions.version("risk_check") == "risk_check.v1"
    assert prompt_versions.version("strategy_recommendations") == "strategy_recommendations.v1"
    assert prompt_versions.version("linkedin_company_post") == "linkedin_company_post.v1"
    assert prompt_versions.version("reddit_post") == "reddit_post.v1"
    assert prompt_versions.version("instagram_post") == "instagram_post.v1"
    assert prompt_versions.version("blog_outline") == "blog_outline.v1"
    assert prompt_versions.version("newsletter_email") == "newsletter_email.v1"
    assert prompt_versions.version("instagram_caption") == "instagram_caption.v1"
    assert prompt_versions.version("instagram_carousel_outline") == "instagram_carousel_outline.v1"
    assert "brief_builder" in prompt_versions.as_dict()


def test_model_provider_factory_defaults_to_deterministic(monkeypatch):
    monkeypatch.delenv("VOUCH_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("QUAINY_MODEL_PROVIDER", raising=False)

    provider = build_model_provider()

    assert isinstance(provider, DeterministicModelProvider)
    result = provider.generate_structured("hello", "OpportunityRecommendationSet")
    assert result.provider == "deterministic"
    assert result.output["recommendations"][0]["confidence"] > 0


def test_model_provider_factory_can_select_openai_without_live_call(monkeypatch):
    monkeypatch.setenv("VOUCH_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    provider = build_model_provider()

    assert isinstance(provider, OpenAIModelProvider)
    assert provider.provider_name == "openai"


def test_model_provider_factory_can_select_openai_compatible_without_live_call():
    provider = build_model_provider(
        "openai_compatible",
        model="company-model",
        base_url="https://models.example.test/v1",
        api_key="test-key",
    )

    assert isinstance(provider, OpenAIModelProvider)
    assert provider.provider_name == "openai_compatible"
    assert provider.model == "company-model"


def test_model_provider_factory_can_select_gemini_without_live_call():
    provider = build_model_provider("gemini", model="gemini-test-model", api_key="gemini-test-key")

    assert isinstance(provider, GeminiModelProvider)
    assert provider.provider_name == "gemini"
    assert provider.model == "gemini-test-model"


def test_secret_reference_can_fall_back_to_dotenv(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("XAI_API_KEY='xai-test-key'\n", encoding="utf-8")
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setattr("app.providers.DOTENV_PATH", env_path)

    assert resolve_secret_reference("XAI_API_KEY") == "xai-test-key"


def test_openai_compatible_generation_uses_chat_response_format(monkeypatch):
    calls = []

    class Message:
        content = '{"ok": true}'

    class Choice:
        message = Message()

    class Usage:
        prompt_tokens = 3
        completion_tokens = 2
        total_tokens = 5

    class ChatCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return type(
                "ChatResponse",
                (),
                {
                    "id": "chat-response-id",
                    "choices": [Choice()],
                    "usage": Usage(),
                },
            )()

    class Chat:
        completions = ChatCompletions()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = Chat()

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    provider = build_model_provider(
        "openai_compatible",
        model="grok-4",
        base_url="https://api.x.ai/v1",
        api_key="xai-test-key",
    )

    result = provider.generate_structured(
        "Confirm connectivity.",
        "AIProviderConnectionTest",
        {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
    )

    assert result.output == {"ok": True}
    assert result.token_usage == {"input_tokens": 3, "output_tokens": 2, "total_tokens": 5}
    assert calls[0]["model"] == "grok-4"
    assert calls[0]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "AIProviderConnectionTest",
            "schema": {
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }


def test_gemini_generation_uses_native_generate_content(monkeypatch):
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return (
                '{"candidates":[{"content":{"parts":[{"text":"{\\\"ok\\\":true}"}]}}],'
                '"usageMetadata":{"promptTokenCount":3,"candidatesTokenCount":2,"totalTokenCount":5}}'
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr("app.providers.urllib.request.urlopen", fake_urlopen)
    provider = build_model_provider("gemini", model="gemini-test-model", api_key="gemini-test-key")

    result = provider.generate_structured(
        "Confirm connectivity.",
        "AIProviderConnectionTest",
        {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
    )

    request, timeout = calls[0]
    assert result.output == {"ok": True}
    assert result.token_usage == {"input_tokens": 3, "output_tokens": 2, "total_tokens": 5}
    assert timeout == 90
    assert request.full_url.startswith("https://generativelanguage.googleapis.com/v1beta/models/gemini-test-model:generateContent")
    assert b"responseMimeType" in request.data
    assert b"AIProviderConnectionTest" in request.data


def test_embedding_provider_factory_is_configurable(monkeypatch):
    monkeypatch.setenv("VOUCH_EMBEDDING_PROVIDER", "local_hash")

    provider = build_embedding_provider()

    assert isinstance(provider, LocalHashEmbeddingProvider)
    assert provider.provider_name == "local-hash"
    assert len(provider.embed(["source grounded content"])[0]) == 64


def test_embedding_provider_factory_can_select_local_openai_compatible_without_live_call():
    provider = build_embedding_provider("local", model="nomic-embed-text", base_url="http://local-runtime.test/v1")

    assert isinstance(provider, OpenAIEmbeddingProvider)
    assert provider.provider_name == "local"
    assert provider.model == "nomic-embed-text"


def test_linkedin_publishing_provider_defaults_to_local(monkeypatch):
    monkeypatch.delenv("VOUCH_LINKEDIN_PUBLISHING_PROVIDER", raising=False)
    monkeypatch.delenv("QUAINY_LINKEDIN_PUBLISHING_PROVIDER", raising=False)

    provider = build_linkedin_publisher()

    assert isinstance(provider, LinkedInPublishingAdapter)
    assert provider.provider_name == "linkedin-local"


def test_unknown_provider_names_fail_fast():
    with pytest.raises(ValueError):
        build_model_provider("unknown-model")
    with pytest.raises(ValueError):
        build_embedding_provider("unknown-embedding")
    with pytest.raises(ValueError):
        build_linkedin_publisher("unknown-publisher")
