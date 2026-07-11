from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from typing import Any

from app.intelligence import terms


@dataclass(frozen=True)
class ModelProviderResult:
    provider: str
    model: str
    output: dict[str, Any]
    token_usage: dict[str, int] = field(default_factory=dict)
    cost_usd: float | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


class LocalHashEmbeddingProvider:
    provider_name = "local-hash"

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for term in terms(text):
            digest = hashlib.sha256(term.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [round(value / magnitude, 6) for value in vector]


class OpenAIEmbeddingProvider:
    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        provider_name: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.base_url = base_url
        if provider_name:
            self.provider_name = provider_name

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key and self.provider_name != "local":
            raise RuntimeError("An API key is required for the selected embedding provider.")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("Install the optional openai package to use OpenAIEmbeddingProvider.") from error
        client_kwargs: dict[str, str] = {"api_key": self.api_key or "local-runtime"}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        client = OpenAI(**client_kwargs)
        try:
            response = client.embeddings.create(model=self.model, input=texts)
        except Exception as error:
            raise RuntimeError("Embedding provider request failed. Check provider credentials and runtime availability.") from error
        return [list(item.embedding) for item in response.data]


class DeterministicModelProvider:
    provider_name = "deterministic"
    model = "deterministic-structured-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output=_deterministic_output(prompt, schema_name),
            token_usage={"estimated_input_tokens": max(1, len(prompt.split()))},
        )


class OpenAIModelProvider:
    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        provider_name: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.base_url = base_url
        if provider_name:
            self.provider_name = provider_name

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if not self.api_key and self.provider_name != "local":
            raise RuntimeError("An API key is required for the selected model provider.")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("Install the optional openai package to use OpenAIModelProvider.") from error

        client_kwargs: dict[str, str] = {"api_key": self.api_key or "local-runtime"}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        client = OpenAI(**client_kwargs)
        text_format = {"type": "json_object"}
        if json_schema:
            text_format = {
                "type": "json_schema",
                "name": schema_name,
                "schema": json_schema,
                "strict": True,
            }
        try:
            response = client.responses.create(
                model=self.model,
                input=prompt,
                text={"format": text_format},
            )
        except Exception as error:
            raise RuntimeError("Model provider request failed. Check provider credentials and runtime availability.") from error
        try:
            output = json.loads(response.output_text)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"OpenAI response was not valid JSON for schema {schema_name}.") from error
        usage = getattr(response, "usage", None)
        token_usage: dict[str, int] = {}
        if usage:
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                value = getattr(usage, key, None)
                if value is not None:
                    token_usage[key] = int(value)
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output=output,
            token_usage=token_usage,
            raw_metadata={"response_id": getattr(response, "id", None)},
        )


def build_model_provider(
    name: str | None = None,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
):
    provider_name = (name or os.getenv("QUAINY_MODEL_PROVIDER", "deterministic")).strip().lower()
    if provider_name in {"deterministic", "mock"}:
        return DeterministicModelProvider()
    if provider_name == "openai":
        return OpenAIModelProvider(api_key=api_key, model=model, base_url=base_url)
    if provider_name in {"openai_compatible", "openai-compatible", "compatible"}:
        return OpenAIModelProvider(
            api_key=api_key or os.getenv("OPENAI_COMPATIBLE_API_KEY"),
            model=model or os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-4.1-mini"),
            base_url=base_url or os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
            provider_name="openai_compatible",
        )
    if provider_name == "local":
        return OpenAIModelProvider(
            api_key=api_key,
            model=model or os.getenv("LOCAL_LLM_MODEL", "llama3.1"),
            base_url=base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"),
            provider_name="local",
        )
    raise ValueError(f"Unknown model provider: {provider_name}")


def _deterministic_output(prompt: str, schema_name: str) -> dict[str, Any]:
    summary = " ".join(prompt.split())[:220]
    if schema_name == "OpportunityRecommendationSet":
        return {
            "recommendations": [
                {
                    "title": "Source-backed communication opportunity",
                    "summary": summary or "Approved context can support a useful public communication.",
                    "why_now": "Approved source context is available and should be reviewed for freshness before publishing.",
                    "confidence": 0.72,
                }
            ]
        }
    if schema_name == "BriefRecommendation":
        return {
            "objective": "Create a source-grounded communication brief for human review.",
            "audience": "The organization's intended public audience.",
            "key_message": "Turn approved context into a useful public-facing story.",
            "supporting_points": [summary or "Approved source context supports this idea."],
            "claims": [],
            "risks": ["Review unsupported claims before publishing."],
        }
    if schema_name == "DraftRecommendationSet":
        return {
            "variants": [
                {
                    "hook": "A source-backed update worth reviewing",
                    "body": summary or "Use approved context to draft a cautious, reviewable update.",
                    "hashtags": [],
                }
            ]
        }
    if schema_name == "ClaimExtractionResult":
        return {"claims": []}
    if schema_name == "RiskCheckResult":
        return {"risks": [], "quality_notes": []}
    if schema_name == "StrategyRecommendationSet":
        return {"recommendations": []}
    return {"summary": summary}


def build_embedding_provider(
    name: str | None = None,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
):
    provider_name = (name or os.getenv("QUAINY_EMBEDDING_PROVIDER", "local_hash")).strip().lower()
    if provider_name in {"local_hash", "local-hash", "deterministic"}:
        return LocalHashEmbeddingProvider()
    if provider_name == "openai":
        return OpenAIEmbeddingProvider(api_key=api_key, model=model, base_url=base_url)
    if provider_name in {"openai_compatible", "openai-compatible", "compatible"}:
        return OpenAIEmbeddingProvider(
            api_key=api_key or os.getenv("OPENAI_COMPATIBLE_API_KEY"),
            model=model or os.getenv("OPENAI_COMPATIBLE_EMBEDDING_MODEL", "text-embedding-3-small"),
            base_url=base_url or os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
            provider_name="openai_compatible",
        )
    if provider_name == "local":
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            model=model or os.getenv("LOCAL_LLM_EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"),
            provider_name="local",
        )
    raise ValueError(f"Unknown embedding provider: {provider_name}")


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))
