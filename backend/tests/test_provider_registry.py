import pytest

from app.prompt_registry import prompt_versions
from app.publishing import LinkedInPublishingAdapter, build_linkedin_publisher
from app.providers import (
    DeterministicModelProvider,
    LocalHashEmbeddingProvider,
    OpenAIModelProvider,
    build_embedding_provider,
    build_model_provider,
)


def test_prompt_registry_returns_known_versions():
    assert prompt_versions.version("brief_builder") == "brief_builder.v1"
    assert prompt_versions.version("linkedin_company_post") == "linkedin_company_post.v1"
    assert prompt_versions.version("blog_outline") == "blog_outline.v1"
    assert prompt_versions.version("newsletter_email") == "newsletter_email.v1"
    assert prompt_versions.version("instagram_caption") == "instagram_caption.v1"
    assert prompt_versions.version("instagram_carousel_outline") == "instagram_carousel_outline.v1"
    assert "brief_builder" in prompt_versions.as_dict()


def test_model_provider_factory_defaults_to_deterministic(monkeypatch):
    monkeypatch.delenv("QUAINY_MODEL_PROVIDER", raising=False)

    provider = build_model_provider()

    assert isinstance(provider, DeterministicModelProvider)
    assert provider.generate_structured("hello", "Example")["schema_name"] == "Example"


def test_model_provider_factory_can_select_openai_without_live_call(monkeypatch):
    monkeypatch.setenv("QUAINY_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    provider = build_model_provider()

    assert isinstance(provider, OpenAIModelProvider)
    assert provider.provider_name == "openai"


def test_embedding_provider_factory_is_configurable(monkeypatch):
    monkeypatch.setenv("QUAINY_EMBEDDING_PROVIDER", "local_hash")

    provider = build_embedding_provider()

    assert isinstance(provider, LocalHashEmbeddingProvider)
    assert provider.provider_name == "local-hash"
    assert len(provider.embed(["source grounded content"])[0]) == 64


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
