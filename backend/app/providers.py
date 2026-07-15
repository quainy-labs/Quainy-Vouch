from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.intelligence import terms


DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def resolve_secret_reference(name: str | None) -> str | None:
    if not name:
        return None
    key = name.strip()
    if not key:
        return None
    value = os.getenv(key)
    if value:
        return value
    return dotenv_value(key)


def dotenv_value(name: str, env_path: Path | None = None) -> str | None:
    path = env_path or DOTENV_PATH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        key, separator, raw_value = stripped.partition("=")
        if separator and key.strip() == name:
            return clean_dotenv_value(raw_value)
    return None


def clean_dotenv_value(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _provider_error_message(prefix: str, error: Exception) -> str:
    detail = getattr(error, "message", None) or str(error)
    status_code = getattr(error, "status_code", None)
    if status_code and detail:
        return f"{prefix} Provider returned {status_code}: {detail}"
    if detail:
        return f"{prefix} Provider error: {detail}"
    return prefix


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
        self.api_key = api_key or resolve_secret_reference("OPENAI_API_KEY")
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
        self.api_key = api_key or resolve_secret_reference("OPENAI_API_KEY")
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
        if self.provider_name != "openai":
            return self._generate_chat_completion(client, prompt, schema_name, json_schema)
        text_format = self._responses_text_format(schema_name, json_schema)
        try:
            response = client.responses.create(
                model=self.model,
                input=prompt,
                text={"format": text_format},
            )
        except Exception as error:
            raise RuntimeError(_provider_error_message("Model provider request failed. Check provider credentials and runtime availability.", error)) from error
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

    def _generate_chat_completion(
        self,
        client: Any,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None,
    ) -> ModelProviderResult:
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format=self._chat_response_format(schema_name, json_schema),
            )
        except Exception as error:
            raise RuntimeError(_provider_error_message("Model provider request failed. Check provider credentials and runtime availability.", error)) from error
        content = response.choices[0].message.content if response.choices else ""
        try:
            output = json.loads(content or "{}")
        except json.JSONDecodeError as error:
            raise RuntimeError(f"OpenAI-compatible response was not valid JSON for schema {schema_name}.") from error
        usage = getattr(response, "usage", None)
        token_usage: dict[str, int] = {}
        if usage:
            for source_key, target_key in (
                ("prompt_tokens", "input_tokens"),
                ("completion_tokens", "output_tokens"),
                ("total_tokens", "total_tokens"),
            ):
                value = getattr(usage, source_key, None)
                if value is not None:
                    token_usage[target_key] = int(value)
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output=output,
            token_usage=token_usage,
            raw_metadata={"response_id": getattr(response, "id", None)},
        )

    def _responses_text_format(self, schema_name: str, json_schema: dict[str, Any] | None) -> dict[str, Any]:
        if not json_schema:
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "name": schema_name,
            "schema": json_schema,
            "strict": True,
        }

    def _chat_response_format(self, schema_name: str, json_schema: dict[str, Any] | None) -> dict[str, Any]:
        if not json_schema:
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "schema": json_schema,
                "strict": True,
            },
        }


class GeminiModelProvider:
    provider_name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or resolve_secret_reference("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL") or dotenv_value("GEMINI_MODEL") or "gemini-2.5-flash"
        self.base_url = (
            base_url
            or os.getenv("GEMINI_BASE_URL")
            or dotenv_value("GEMINI_BASE_URL")
            or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if not self.api_key:
            raise RuntimeError("An API key is required for the selected model provider.")
        instruction = self._structured_prompt(prompt, schema_name, json_schema)
        endpoint = (
            f"{self.base_url}/models/{urllib.parse.quote(self.model, safe='')}:generateContent"
            f"?key={urllib.parse.quote(self.api_key, safe='')}"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": instruction}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                response_body = response.read().decode("utf-8")
        except TimeoutError as error:
            raise RuntimeError(
                "Model provider request failed. Check provider credentials and runtime availability. Provider error: request timed out."
            ) from error
        except urllib.error.HTTPError as error:
            detail = self._http_error_detail(error)
            raise RuntimeError(
                f"Model provider request failed. Check provider credentials and runtime availability. Provider returned {error.code}: {detail}"
            ) from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Model provider request failed. Check provider credentials and runtime availability. Provider error: {error.reason}"
            ) from error
        try:
            decoded = json.loads(response_body)
            content = self._extract_text(decoded)
            output = json.loads(content or "{}")
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Gemini response was not valid JSON for schema {schema_name}.") from error
        usage = decoded.get("usageMetadata", {}) if isinstance(decoded, dict) else {}
        token_usage: dict[str, int] = {}
        for source_key, target_key in (
            ("promptTokenCount", "input_tokens"),
            ("candidatesTokenCount", "output_tokens"),
            ("totalTokenCount", "total_tokens"),
        ):
            value = usage.get(source_key)
            if value is not None:
                token_usage[target_key] = int(value)
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output=output,
            token_usage=token_usage,
            raw_metadata={"candidate_count": len(decoded.get("candidates", [])) if isinstance(decoded, dict) else 0},
        )

    def _structured_prompt(self, prompt: str, schema_name: str, json_schema: dict[str, Any] | None) -> str:
        schema_text = json.dumps(json_schema or {}, separators=(",", ":"))
        return (
            f"{prompt}\n\n"
            f"Return only valid JSON for schema {schema_name}. Do not include markdown fences or commentary.\n"
            f"JSON schema: {schema_text}"
        )

    def _extract_text(self, response: dict[str, Any]) -> str:
        candidates = response.get("candidates") or []
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(str(part.get("text", "")) for part in parts)

    def _http_error_detail(self, error: urllib.error.HTTPError) -> str:
        try:
            body = error.read().decode("utf-8")
        except Exception:
            return str(error)
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError:
            return body
        if isinstance(decoded, dict):
            provider_error = decoded.get("error")
            if isinstance(provider_error, dict):
                return str(provider_error.get("message") or provider_error)
        return str(decoded)


def build_model_provider(
    name: str | None = None,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
):
    provider_name = (name or os.getenv("VOUCH_MODEL_PROVIDER") or os.getenv("QUAINY_MODEL_PROVIDER", "deterministic")).strip().lower()
    if provider_name in {"deterministic", "mock"}:
        return DeterministicModelProvider()
    if provider_name == "openai":
        return OpenAIModelProvider(api_key=api_key, model=model, base_url=base_url)
    if provider_name in {"gemini", "google", "google_gemini", "google-gemini"}:
        return GeminiModelProvider(
            api_key=api_key or resolve_secret_reference("GEMINI_API_KEY"),
            model=model,
            base_url=base_url,
        )
    if provider_name in {"openai_compatible", "openai-compatible", "compatible"}:
        return OpenAIModelProvider(
            api_key=api_key or resolve_secret_reference("OPENAI_COMPATIBLE_API_KEY"),
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
    provider_name = (name or os.getenv("VOUCH_EMBEDDING_PROVIDER") or os.getenv("QUAINY_EMBEDDING_PROVIDER", "local_hash")).strip().lower()
    if provider_name in {"local_hash", "local-hash", "deterministic"}:
        return LocalHashEmbeddingProvider()
    if provider_name == "openai":
        return OpenAIEmbeddingProvider(api_key=api_key, model=model, base_url=base_url)
    if provider_name in {"openai_compatible", "openai-compatible", "compatible"}:
        return OpenAIEmbeddingProvider(
            api_key=api_key or resolve_secret_reference("OPENAI_COMPATIBLE_API_KEY"),
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
