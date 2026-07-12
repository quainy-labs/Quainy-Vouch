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


class OpportunityStructuredProvider:
    provider_name = "model-test-provider"
    model = "specific-opportunity-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if schema_name == "OpportunityRecommendationSet":
            return ModelProviderResult(
                provider=self.provider_name,
                model=self.model,
                output={
                    "recommendations": [
                        {
                            "title": "Announce the new Product Judgment in the AI Era blog",
                            "summary": "The organization has a fresh product judgment blog that explains how builders decide what is worth building with AI.",
                            "why_now": "The blog was published today and is the most timely public proof artifact.",
                            "confidence": 0.91,
                        }
                    ]
                },
                token_usage={"total_tokens": 12},
            )
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"recommendations": []},
            token_usage={"total_tokens": 4},
        )


class SocialDraftStructuredProvider:
    provider_name = "social-draft-test-provider"
    model = "social-draft-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if schema_name == "DraftRecommendationSet":
            if "Platform: reddit" in prompt:
                body = (
                    "Title: Model-written Reddit post\n\n"
                    "Subreddit fit:\nUseful for builders discussing source-grounded content.\n\n"
                    "Post body:\nThis is the model-written Reddit body using approved context.\n\n"
                    "Discussion question: What would you verify before publishing this?"
                )
                hook = "Model-written Reddit post"
            elif "Platform: instagram" in prompt:
                body = (
                    "Visual direction: A model-written source card beside a draft.\n\n"
                    "Post copy:\nModel-written Instagram post from approved context.\n\n"
                    "Hashtags: #SourceBacked #ProductJudgment"
                )
                hook = "Model-written Instagram post"
            else:
                body = "Model-written LinkedIn post from approved context."
                hook = "Model-written LinkedIn post"
            return ModelProviderResult(
                provider=self.provider_name,
                model=self.model,
                output={"variants": [{"hook": hook, "body": body, "hashtags": ["#ModelWritten"]}]},
                token_usage={"total_tokens": 18},
            )
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={
                "recommendations": [
                    {
                        "title": "Use approved context for public posts",
                        "summary": "Approved context can support useful public posts.",
                        "why_now": "Source context is available for review today.",
                        "confidence": 0.86,
                    }
                ]
            },
            token_usage={"total_tokens": 6},
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


def test_grounded_model_recommendation_becomes_top_opportunity():
    org = client.post("/organizations", json={"name": "Specific Model Opportunity Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "audience": "AI builders and founders",
            "content_pillars": ["product judgment", "AI building"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Published blog today",
            "raw_text": (
                "The organization published Product Judgment in the AI Era today. "
                "The blog explains how builders decide what is worth building, who it should serve, "
                "what promise to make, and how to use AI without losing product sense. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    original_provider = store.model_provider
    store.model_provider = OpportunityStructuredProvider()
    try:
        opportunities = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"]
    finally:
        store.model_provider = original_provider

    assert opportunities[0]["title"] == "Announce the new Product Judgment in the AI Era blog"
    assert opportunities[0]["metadata"]["generation_basis"] == "model_recommendation"


def test_social_draft_model_output_becomes_visible_draft_body():
    org = create_context_org("Social Draft Model Org")
    original_provider = store.model_provider
    store.model_provider = SocialDraftStructuredProvider()
    try:
        opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
        brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
        reddit = client.post(f"/briefs/{brief['id']}/drafts?platform=reddit&content_type=post").json()["drafts"][0]
        instagram = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=post").json()["drafts"][0]
    finally:
        store.model_provider = original_provider

    assert reddit["body"].startswith("Title: Model-written Reddit post")
    assert reddit["hook"] == "Model-written Reddit post"
    assert reddit["generation_metadata"]["body_source"] == "model_recommendation"
    assert instagram["body"].startswith("Visual direction: A model-written source card")
    assert instagram["hook"] == "Model-written Instagram post"
    assert instagram["generation_metadata"]["body_source"] == "model_recommendation"
