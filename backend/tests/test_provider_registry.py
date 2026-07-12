import pytest

from app.prompt_registry import prompt_versions
from app.publishing import LinkedInPublishingAdapter, build_linkedin_publisher
from app.providers import (
    DeterministicModelProvider,
    LocalHashEmbeddingProvider,
    OpenAIEmbeddingProvider,
    OpenAIModelProvider,
    build_embedding_provider,
    build_model_provider,
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
    monkeypatch.delenv("QUAINY_MODEL_PROVIDER", raising=False)

    provider = build_model_provider()

    assert isinstance(provider, DeterministicModelProvider)
    result = provider.generate_structured("hello", "OpportunityRecommendationSet")
    assert result.provider == "deterministic"
    assert result.output["recommendations"][0]["confidence"] > 0


def test_model_provider_factory_can_select_openai_without_live_call(monkeypatch):
    monkeypatch.setenv("QUAINY_MODEL_PROVIDER", "openai")
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


def test_embedding_provider_factory_is_configurable(monkeypatch):
    monkeypatch.setenv("QUAINY_EMBEDDING_PROVIDER", "local_hash")

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
