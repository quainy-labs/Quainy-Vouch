from __future__ import annotations

import hashlib
import json
import math
import os
from typing import Any

from app.intelligence import terms


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


class DeterministicModelProvider:
    provider_name = "deterministic"

    def generate_structured(self, prompt: str, schema_name: str) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "schema_name": schema_name,
            "summary": prompt[:240],
        }


class OpenAIModelProvider:
    provider_name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def generate_structured(self, prompt: str, schema_name: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required when QUAINY_MODEL_PROVIDER=openai.")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("Install the optional openai package to use OpenAIModelProvider.") from error

        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            input=prompt,
            text={"format": {"type": "json_object"}},
        )
        try:
            return json.loads(response.output_text)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"OpenAI response was not valid JSON for schema {schema_name}.") from error


def build_model_provider(name: str | None = None):
    provider_name = (name or os.getenv("QUAINY_MODEL_PROVIDER", "deterministic")).strip().lower()
    if provider_name in {"deterministic", "local", "mock"}:
        return DeterministicModelProvider()
    if provider_name == "openai":
        return OpenAIModelProvider()
    raise ValueError(f"Unknown model provider: {provider_name}")


def build_embedding_provider(name: str | None = None):
    provider_name = (name or os.getenv("QUAINY_EMBEDDING_PROVIDER", "local_hash")).strip().lower()
    if provider_name in {"local_hash", "local-hash", "deterministic"}:
        return LocalHashEmbeddingProvider()
    raise ValueError(f"Unknown embedding provider: {provider_name}")


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))
