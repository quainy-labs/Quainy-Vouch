from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.schemas import (
    ClaimCheck,
    CompanyProfile,
    ContentBrief,
    ContentOpportunity,
    Draft,
    DraftGenerationSpec,
    PostMemory,
    ReviewerPackage,
    Source,
    SourceChunk,
)


@dataclass(frozen=True)
class ExtractedSource:
    title: str
    raw_text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DraftVariant:
    hook: str
    style: str


@dataclass(frozen=True)
class RenderedDraft:
    body: str
    hook: str
    hashtags: list[str]


class SourceConnector(Protocol):
    source_type: str

    def extract(self, payload: dict[str, Any]) -> ExtractedSource:
        """Extract approved source text from a connector-specific payload."""


class ContextRetriever(Protocol):
    def retrieve(self, organization_id: str, query: str, limit: int = 6) -> list[SourceChunk]:
        """Return approved, organization-scoped chunks only."""


class ContentOpportunityGenerator(Protocol):
    def generate(
        self,
        profile: CompanyProfile,
        sources: list[Source],
        chunks: list[SourceChunk],
    ) -> list[ContentOpportunity]:
        """Suggest source-backed content opportunities or return none."""


class RelevanceScorer(Protocol):
    def score(
        self,
        opportunity: ContentOpportunity,
        sources: list[Source],
        memory: list[PostMemory],
    ) -> dict[str, float | list[str]]:
        """Score freshness, relevance, confidence, and duplicate risk."""


class BriefBuilder(Protocol):
    def build(
        self,
        profile: CompanyProfile,
        opportunity: ContentOpportunity,
        chunks: list[SourceChunk],
    ) -> ContentBrief:
        """Create a platform-independent content brief."""


class FormatAdapter(Protocol):
    platform: str
    content_type: str
    adapter_name: str
    adapter_version: str

    def generation_spec(self, brief: ContentBrief) -> DraftGenerationSpec:
        """Return platform/content-type rules used to generate drafts."""

    def variants(self) -> list[DraftVariant]:
        """Return generation variants for this platform/content type."""

    def render(
        self,
        variant: DraftVariant,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> RenderedDraft:
        """Render a platform-specific draft from a platform-independent brief."""

    def quality_checks(self, body: str, profile: CompanyProfile, brief: ContentBrief) -> list[str]:
        """Return platform-specific quality and fit checks."""


class DraftGenerator(Protocol):
    def generate(
        self,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
        chunks: list[SourceChunk],
        memory: list[PostMemory],
        adapter: FormatAdapter,
    ) -> list[Draft]:
        """Generate drafts through a provided format adapter."""


class ClaimExtractor(Protocol):
    def extract(self, body: str) -> list[str]:
        """Extract factual and judgment claims from a draft body."""


class ClaimGroundingChecker(Protocol):
    def check(self, claims: list[str], chunks: list[SourceChunk]) -> list[ClaimCheck]:
        """Check claim support against approved source chunks."""


class QualityRiskChecker(Protocol):
    def check(
        self,
        body: str,
        profile: CompanyProfile,
        claims: list[ClaimCheck],
        duplicate_report: dict[str, object],
        opportunity: ContentOpportunity,
        adapter: FormatAdapter,
    ) -> dict[str, list[str]]:
        """Return quality and risk checks for a reviewable draft."""


class DuplicateChecker(Protocol):
    def check(self, body: str, memory: list[PostMemory]) -> dict[str, object]:
        """Compare a draft against approved/exported/published memory."""


class ReviewerPackageBuilder(Protocol):
    def build(self, draft_id: str) -> ReviewerPackage:
        """Prepare the object a reviewer uses to decide safely."""


class LearningSignalRecorder(Protocol):
    def record(self, draft: Draft, decision: str, metadata: dict[str, Any]) -> None:
        """Persist approval, rejection, edit, export, and future performance signals."""


class ModelProvider(Protocol):
    provider_name: str

    def generate_structured(self, prompt: str, schema_name: str) -> dict[str, Any]:
        """Generate structured output from a model provider."""


class EmbeddingProvider(Protocol):
    provider_name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for retrieval, duplicate checks, or evaluations."""
