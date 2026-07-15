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
        if schema_name == "OpportunityRecommendationSet":
            raise RuntimeError("Opportunity model response was not usable.")
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


class GenericOpportunityStructuredProvider:
    provider_name = "generic-opportunity-test-provider"
    model = "generic-opportunity-v1"

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
                            "title": "Source-backed communication opportunity",
                            "summary": "Approved source context is available.",
                            "why_now": "Use approved context for a reviewable update.",
                            "confidence": 0.72,
                        }
                    ]
                },
                token_usage={"total_tokens": 8},
            )
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"recommendations": []},
            token_usage={"total_tokens": 4},
        )


class IrrelevantOpportunityStructuredProvider:
    provider_name = "irrelevant-opportunity-test-provider"
    model = "irrelevant-opportunity-v1"

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
                            "title": "Announce the new referral rewards program",
                            "summary": "A referral rewards program can drive community growth and customer acquisition.",
                            "why_now": "Referral campaigns are timely and can turn audience attention into signups.",
                            "confidence": 0.88,
                        }
                    ]
                },
                token_usage={"total_tokens": 8},
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
                    "Title: How do you keep reviewer control visible in public stories?\n\n"
                    "Subreddit fit:\nUseful for builders discussing content operations and source-grounded workflows.\n\n"
                    "Post body:\nI am working through a pattern where public stories start from approved context instead of a blank prompt.\n\n"
                    "The useful detail is reviewer control: the source stays visible, claims stay cautious, and the final lesson is operator-facing.\n\n"
                    "Discussion question: What would you verify before publishing a workflow like this?"
                )
                hook = "How do you keep reviewer control visible in public stories?"
            elif "Platform: instagram" in prompt:
                body = (
                    "Visual direction: Show one approved source note beside a draft card with a visible reviewer check.\n\n"
                    "Post copy:\nPublic stories work better when the proof stays visible.\n\n"
                    "Trust cue: approved context, reviewer control, cautious claims, and source visibility all stay in the workflow.\n\n"
                    "Hashtags: #SourceBacked #ProductJudgment"
                )
                hook = "Keep the proof visible."
            else:
                body = (
                    "Public stories get stronger when the review path is visible.\n\n"
                    "For founders and operators, the useful shift is starting from approved context instead of asking a blank prompt to invent the angle.\n\n"
                    "The source-backed detail is reviewer control: source visibility, cautious claims, and operator-facing lessons stay connected before anything public is approved.\n\n"
                    "That makes the final post easier to trust and easier for a human reviewer to improve."
                )
                hook = "Keep reviewer control visible."
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


class ProviderFailureDraftProvider:
    provider_name = "quota-test-provider"
    model = "quota-model-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if schema_name == "DraftRecommendationSet":
            raise RuntimeError("Model provider request failed. Provider returned 429: RESOURCE_EXHAUSTED quota exceeded.")
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"recommendations": []},
            token_usage={"total_tokens": 4},
        )


class MixedLinkedInDraftProvider:
    provider_name = "mixed-linkedin-test-provider"
    model = "mixed-linkedin-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if schema_name == "DraftRecommendationSet":
            body_one = (
                "Approved context works best when reviewer control stays visible.\n\n"
                "The useful shift is simple: public stories should keep source visibility, cautious claims, "
                "and operator-facing lessons connected before anything is approved.\n\n"
                "That gives founders and operators a clearer way to turn real company knowledge into a public update."
            )
            body_two = (
                "Public communication gets stronger when the proof is easy to inspect.\n\n"
                "This workflow starts from approved context, keeps reviewer control in the loop, "
                "and uses cautious claims instead of asking a blank prompt to invent the angle.\n\n"
                "The result is a source-visible story an operator can review before publishing."
            )
            return ModelProviderResult(
                provider=self.provider_name,
                model=self.model,
                output={
                    "variants": [
                        {"hook": "Keep reviewer control visible", "body": body_one, "hashtags": []},
                        {"hook": "Make the proof inspectable", "body": body_two, "hashtags": []},
                        {"hook": "Too short", "body": "Approved context helps.", "hashtags": []},
                    ]
                },
                token_usage={"total_tokens": 34},
            )
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"recommendations": []},
            token_usage={"total_tokens": 4},
        )


class LongSingleParagraphInstagramProvider:
    provider_name = "instagram-single-paragraph-test-provider"
    model = "instagram-single-paragraph-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if schema_name == "DraftRecommendationSet":
            body = (
                "Approved context helps teams create public stories with reviewer control. Source visibility keeps the proof close to the message. "
                "Cautious claims make the final post easier for a human to trust. Operator-facing lessons help founders understand what changed before publishing. "
                "That is why source-grounded workflows are useful for public communication."
            )
            return ModelProviderResult(
                provider=self.provider_name,
                model=self.model,
                output={"variants": [{"hook": "Keep the proof close", "body": body, "hashtags": ["#SourceBacked"]}]},
                token_usage={"total_tokens": 24},
            )
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"recommendations": []},
            token_usage={"total_tokens": 4},
        )


class InstagramCompanyBioDraftProvider:
    provider_name = "instagram-company-bio-test-provider"
    model = "instagram-company-bio-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if schema_name == "DraftRecommendationSet":
            body = (
                "Quainy is a builder-first AI ecosystem. We build active products like Quainy Vouch. "
                "Quainy Vouch is a secure, source-grounded communication agent. It helps teams use approved "
                "company knowledge for consistent content. With human approval before publishing."
            )
            return ModelProviderResult(
                provider=self.provider_name,
                model=self.model,
                output={"variants": [{"hook": "How do you ensure your company's AI communication is accurate?", "body": body, "hashtags": []}]},
                token_usage={"total_tokens": 22},
            )
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"recommendations": []},
            token_usage={"total_tokens": 4},
        )


class InstagramCorporateBlurbDraftProvider:
    provider_name = "instagram-corporate-blurb-test-provider"
    model = "instagram-corporate-blurb-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if schema_name == "DraftRecommendationSet":
            body = (
                "Meaningful ideas drive useful products.\n\n"
                "Quainy offers a dedicated library, Meaningful Problems, to help builders. "
                "It is designed for understanding what is worth solving, who it affects, and why a product should exist.\n\n"
                "This insight is foundational to Quainy's mission to create production-ready products."
            )
            return ModelProviderResult(
                provider=self.provider_name,
                model=self.model,
                output={"variants": [{"hook": "What problem are you really solving with AI?", "body": body, "hashtags": []}]},
                token_usage={"total_tokens": 28},
            )
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"recommendations": []},
            token_usage={"total_tokens": 4},
        )


class InstagramAnnouncementDraftProvider:
    provider_name = "instagram-announcement-test-provider"
    model = "instagram-announcement-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if schema_name == "DraftRecommendationSet":
            body = (
                "Published blog today: Product Judgment in the AI Era shows that building meaningful ideas into "
                "production-ready products is only possible when we use AI responsibly. At Quainy, we believe that "
                "product judgment is crucial to creating successful AI-native products. Our latest blog post explores "
                "how builders can make informed decisions about what to build, who it should serve, and how to harness "
                "the power of AI without losing sight of product sense."
            )
            return ModelProviderResult(
                provider=self.provider_name,
                model=self.model,
                output={"variants": [{"hook": "Product judgment matters", "body": body, "hashtags": ["#ProductJudgment"]}]},
                token_usage={"total_tokens": 18},
            )
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"recommendations": []},
            token_usage={"total_tokens": 4},
        )


class InstagramLabsPromoDraftProvider:
    provider_name = "instagram-labs-promo-test-provider"
    model = "instagram-labs-promo-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if schema_name == "DraftRecommendationSet":
            body = (
                "Real context makes better content.\n\n"
                "Get Hands-on with Quainy Labs' Python First Principles.\n\n"
                "The trust comes from the proof: Quainy Labs are public, inspectable learning paths that turn "
                "Quainy's culture into real work. Python First Principles helps learners understand Python deeply "
                "through first principles reasoning, implementation.\n\n"
                "Read more about Quainy Labs' Python First Principles and start building capable learners today!"
            )
            return ModelProviderResult(
                provider=self.provider_name,
                model=self.model,
                output={"variants": [{"hook": "Real context makes better content.", "body": body, "hashtags": ["#QuainyLabs"]}]},
                token_usage={"total_tokens": 18},
            )
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"recommendations": []},
            token_usage={"total_tokens": 4},
        )


class RedditPromoDraftProvider:
    provider_name = "reddit-promo-test-provider"
    model = "reddit-promo-v1"

    def generate_structured(
        self,
        prompt: str,
        schema_name: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelProviderResult:
        if schema_name == "DraftRecommendationSet":
            body = (
                "**Build production-ready AI products with Quainy Labs**\n\n"
                "As I built my first Quainy Lab project, Python First Principles helped me understand the importance "
                "of testing tradeoffs in software engineering. What's your experience with tradeoff analysis? "
                "Should we prioritize speed or reliability in our AI projects?\n\n"
                "As AI leverages grow, we need to focus on what truly matters: product judgment, market understanding, "
                "and architecture. Quainy Labs are public, inspectable learning paths that turn our culture into real work. "
                "But what's the value of this capability-building path?\n\n"
                "Ever wondered how Quainy Labs' Python First Principles helps learners build a strong foundation in software engineering? "
                "I recently stumbled upon an excerpt from their source code, which highlighted the importance of implementing tests and understanding tradeoffs. "
                "What's more, this approach not only enhances productivity but also enables builders to reason from problem to product. "
                "I'm curious: How do you prioritize testing and iteration when working on AI-powered projects?\n\n"
                "Read more about Quainy Labs' Python First Principles and start building capable learners today!"
            )
            return ModelProviderResult(
                provider=self.provider_name,
                model=self.model,
                output={"variants": [{"hook": "Build production-ready AI products with Quainy Labs", "body": body, "hashtags": []}]},
                token_usage={"total_tokens": 18},
            )
        return ModelProviderResult(
            provider=self.provider_name,
            model=self.model,
            output={"recommendations": []},
            token_usage={"total_tokens": 4},
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


def enable_live_model_generation(org_id: str) -> None:
    client.patch(
        f"/organizations/{org_id}/ai-provider-settings",
        json={
            "generation_provider": "openai_compatible",
            "generation_model": "live-test-model",
            "generation_base_url": "https://models.example.test/v1",
            "generation_api_key_env_var": "LIVE_MODEL_KEY",
            "embedding_provider": "deterministic",
            "embedding_model": "local-hash",
            "enabled": True,
        },
    ).raise_for_status()


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


def test_live_model_opportunity_failure_does_not_create_deterministic_fallback(monkeypatch):
    org = create_context_org("Live Failed Opportunity Org")
    enable_live_model_generation(org["id"])
    monkeypatch.setattr(store, "model_provider_for_org", lambda organization_id: InvalidStructuredProvider())

    response = client.post(f"/organizations/{org['id']}/opportunities/generate")

    assert response.status_code == 422
    assert "No deterministic fallback was used" in response.json()["detail"]
    assert client.get(f"/organizations/{org['id']}/opportunities").json() == []
    calls = client.get(f"/organizations/{org['id']}/model-calls").json()
    opportunity_call = next(call for call in calls if call["schema_name"] == "OpportunityRecommendationSet")
    assert opportunity_call["status"] == "failed"
    assert opportunity_call["provider"] == "invalid-test-provider"
    jobs = client.get(f"/organizations/{org['id']}/jobs").json()
    generation_job = next(job for job in jobs if job["kind"] == "opportunity_generation")
    assert generation_job["status"] == "failed"
    assert "No deterministic fallback was used" in generation_job["error_message"]


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
    assert all(opportunity["metadata"]["generation_basis"] == "model_recommendation" for opportunity in opportunities)


def test_successful_llm_opportunity_call_does_not_add_deterministic_fallbacks():
    org = create_context_org("Generic LLM Opportunity Org")
    original_provider = store.model_provider
    store.model_provider = GenericOpportunityStructuredProvider()
    try:
        opportunities = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"]
    finally:
        store.model_provider = original_provider

    assert opportunities == []
    calls = client.get(f"/organizations/{org['id']}/model-calls").json()
    opportunity_call = next(call for call in calls if call["schema_name"] == "OpportunityRecommendationSet")
    assert opportunity_call["status"] == "succeeded"
    assert opportunity_call["provider"] == "generic-opportunity-test-provider"


def test_source_irrelevant_llm_opportunity_is_rejected():
    org = client.post("/organizations", json={"name": "Irrelevant LLM Opportunity Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "audience": "education teams",
            "content_pillars": ["learning design", "software education"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Backend testing lab",
            "raw_text": (
                "The approved lab teaches learners how to design backend tests, inspect failure cases, "
                "compare implementation tradeoffs, and explain reliability decisions before shipping code. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()
    original_provider = store.model_provider
    store.model_provider = IrrelevantOpportunityStructuredProvider()
    try:
        opportunities = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"]
    finally:
        store.model_provider = original_provider

    assert opportunities == []
    calls = client.get(f"/organizations/{org['id']}/model-calls").json()
    opportunity_call = next(call for call in calls if call["schema_name"] == "OpportunityRecommendationSet")
    assert opportunity_call["status"] == "succeeded"
    assert opportunity_call["provider"] == "irrelevant-opportunity-test-provider"


def test_live_model_weak_opportunities_are_rejected_without_fallback(monkeypatch):
    org = create_context_org("Live Weak Opportunity Org")
    enable_live_model_generation(org["id"])
    monkeypatch.setattr(store, "model_provider_for_org", lambda organization_id: GenericOpportunityStructuredProvider())

    response = client.post(f"/organizations/{org['id']}/opportunities/generate")

    assert response.status_code == 422
    assert "no source-grounded opportunities" in response.json()["detail"]
    assert client.get(f"/organizations/{org['id']}/opportunities").json() == []
    calls = client.get(f"/organizations/{org['id']}/model-calls").json()
    opportunity_call = next(call for call in calls if call["schema_name"] == "OpportunityRecommendationSet")
    assert opportunity_call["status"] == "succeeded"
    assert opportunity_call["provider"] == "generic-opportunity-test-provider"


def test_social_draft_model_output_becomes_visible_draft_body():
    org = create_context_org("Social Draft Model Org")
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    original_provider = store.model_provider
    store.model_provider = SocialDraftStructuredProvider()
    try:
        reddit = client.post(f"/briefs/{brief['id']}/drafts?platform=reddit&content_type=post").json()["drafts"][0]
        instagram = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=post").json()["drafts"][0]
    finally:
        store.model_provider = original_provider

    assert reddit["body"].startswith("I am working through a pattern")
    assert "Subreddit fit:" not in reddit["body"]
    assert reddit["hook"] == "How do you keep reviewer control visible in public stories?"
    assert reddit["generation_metadata"]["body_source"] == "model_recommendation"
    assert instagram["body"].startswith("Public stories work better")
    assert "Visual direction:" not in instagram["body"]
    assert "Post copy:" not in instagram["body"]
    assert "Hashtags:" not in instagram["body"]
    assert "Trust cue:" not in instagram["body"]
    assert "The trust comes from the proof:" in instagram["body"]
    assert instagram["hook"] == "Keep the proof visible."
    assert instagram["generation_metadata"]["body_source"] == "model_recommendation"


def test_instagram_announcement_prose_is_rejected_for_caption_body():
    org = client.post("/organizations", json={"name": "Instagram Blog Caption Org"}).json()
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

    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    original_provider = store.model_provider
    store.model_provider = InstagramAnnouncementDraftProvider()
    try:
        instagram = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=post").json()["drafts"][0]
    finally:
        store.model_provider = original_provider

    lowered = instagram["body"].lower()
    assert instagram["generation_metadata"]["body_source"] == "adapter_render"
    assert "model_rejection_reason" in instagram["generation_metadata"]
    assert "published blog today:" not in lowered
    assert "at quainy, we believe" not in lowered
    assert "latest blog post explores" not in lowered
    assert "harness the power of ai" not in lowered
    assert instagram["body"].startswith("Build from what is true.")
    assert "what is worth building" in lowered
    assert "without replacing judgment" in lowered


def test_live_model_rejected_instagram_draft_does_not_save_adapter_fallback(monkeypatch):
    org = client.post("/organizations", json={"name": "Live Instagram Draft Org"}).json()
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

    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    enable_live_model_generation(org["id"])
    monkeypatch.setattr(store, "model_provider_for_org", lambda organization_id: InstagramAnnouncementDraftProvider())

    response = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=post")

    assert response.status_code == 422
    assert "No fallback draft was saved" in response.json()["detail"]
    assert client.get(f"/briefs/{brief['id']}/drafts").json() == []
    calls = client.get(f"/organizations/{org['id']}/model-calls").json()
    draft_call = next(call for call in calls if call["schema_name"] == "DraftRecommendationSet")
    assert draft_call["status"] == "succeeded"
    jobs = client.get(f"/organizations/{org['id']}/jobs").json()
    draft_job = next(job for job in jobs if job["kind"] == "draft_generation")
    assert draft_job["status"] == "failed"
    assert "No fallback draft was saved" in draft_job["error_message"]


def test_live_model_provider_quota_failure_returns_502(monkeypatch):
    org = create_context_org("Live Quota Draft Org")
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    enable_live_model_generation(org["id"])
    monkeypatch.setattr(store, "model_provider_for_org", lambda organization_id: ProviderFailureDraftProvider())

    response = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=post")

    assert response.status_code == 502
    assert "RESOURCE_EXHAUSTED" in response.json()["detail"]
    assert client.get(f"/briefs/{brief['id']}/drafts").json() == []


def test_live_model_instagram_single_paragraph_is_split_before_validation(monkeypatch):
    org = create_context_org("Instagram Single Paragraph Org")
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    enable_live_model_generation(org["id"])
    monkeypatch.setattr(store, "model_provider_for_org", lambda organization_id: LongSingleParagraphInstagramProvider())

    response = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=post")

    assert response.status_code == 200
    draft = response.json()["drafts"][0]
    assert draft["generation_metadata"]["body_source"] == "model_recommendation"
    assert "\n\n" in draft["body"]
    assert "instagram_long_single_paragraph" not in draft["generation_metadata"].get("model_rejection_reasons", [])


def test_live_model_instagram_company_bio_copy_is_rejected(monkeypatch):
    org = create_context_org("Instagram Company Bio Org")
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    enable_live_model_generation(org["id"])
    monkeypatch.setattr(store, "model_provider_for_org", lambda organization_id: InstagramCompanyBioDraftProvider())

    response = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=post")

    assert response.status_code == 422
    assert "instagram_company_bio_copy" in response.json()["detail"]
    assert client.get(f"/briefs/{brief['id']}/drafts").json() == []


def test_live_model_instagram_corporate_blurb_is_rejected(monkeypatch):
    org = create_context_org("Instagram Corporate Blurb Org")
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    enable_live_model_generation(org["id"])
    monkeypatch.setattr(store, "model_provider_for_org", lambda organization_id: InstagramCorporateBlurbDraftProvider())

    response = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=post")

    assert response.status_code == 422
    assert "instagram_corporate_blurb" in response.json()["detail"]
    assert client.get(f"/briefs/{brief['id']}/drafts").json() == []


def test_live_model_saves_valid_draft_variants_when_one_variant_is_rejected(monkeypatch):
    org = create_context_org("Mixed LinkedIn Draft Org")
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    enable_live_model_generation(org["id"])
    monkeypatch.setattr(store, "model_provider_for_org", lambda organization_id: MixedLinkedInDraftProvider())

    response = client.post(f"/briefs/{brief['id']}/drafts?platform=linkedin&content_type=company_post")

    assert response.status_code == 200
    drafts = response.json()["drafts"]
    assert len(drafts) == 2
    assert all(draft["generation_metadata"]["body_source"] == "model_recommendation" for draft in drafts)
    assert {draft["hook"] for draft in drafts} == {"Keep reviewer control visible", "Make the proof inspectable"}
    stored = client.get(f"/briefs/{brief['id']}/drafts").json()
    assert len(stored) == 2


def test_instagram_labs_promo_or_source_dump_is_rejected():
    org = client.post("/organizations", json={"name": "Instagram Labs Promo Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "audience": "students, developers, founders, curious learners, and one-person builders",
            "content_pillars": ["Python First Principles", "Quainy Labs"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Python First Principles",
            "raw_text": (
                "Quainy Labs are public, inspectable learning paths that turn Quainy's culture into real work. "
                "Python First Principles helps learners understand Python deeply through first principles reasoning, "
                "implementation, testing, tradeoffs, internals, software engineering, ecosystem knowledge, and capstone projects. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()

    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    opportunity["title"] = "Get Hands-on with Quainy Labs' Python First Principles"
    store.opportunities[opportunity["id"]] = store.opportunities[opportunity["id"]].model_copy(update={"title": opportunity["title"]})
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    original_provider = store.model_provider
    store.model_provider = InstagramLabsPromoDraftProvider()
    try:
        instagram = client.post(f"/briefs/{brief['id']}/drafts?platform=instagram&content_type=post").json()["drafts"][0]
    finally:
        store.model_provider = original_provider

    lowered = instagram["body"].lower()
    assert instagram["generation_metadata"]["body_source"] == "adapter_render"
    assert "model_rejection_reason" in instagram["generation_metadata"]
    assert "real context makes better content" not in lowered
    assert "get hands-on with quainy labs" not in lowered
    assert "quainy labs are public" not in lowered
    assert "turn quainy's culture into real work" not in lowered
    assert "read more about" not in lowered
    assert "start building" not in lowered
    assert "tests" in lowered
    assert "tradeoffs" in lowered


def test_reddit_promotional_or_invented_post_is_rejected():
    org = client.post("/organizations", json={"name": "Reddit Labs Caption Org"}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "audience": "students, developers, founders, curious learners, and one-person builders",
            "content_pillars": ["Python First Principles", "Quainy Labs"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "manual_note",
            "title": "Quainy Labs Python First Principles",
            "raw_text": (
                "Quainy Labs includes Python First Principles as a hands-on lab for understanding software engineering tradeoffs. "
                "The lab helps builders reason about speed, reliability, testing, and production readiness without treating AI as a shortcut. "
            )
            * 4,
            "approval_status": "approved",
        },
    ).raise_for_status()

    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    original_provider = store.model_provider
    store.model_provider = RedditPromoDraftProvider()
    try:
        reddit = client.post(f"/briefs/{brief['id']}/drafts?platform=reddit&content_type=post").json()["drafts"][0]
    finally:
        store.model_provider = original_provider

    lowered = reddit["body"].lower()
    assert reddit["generation_metadata"]["body_source"] == "adapter_render"
    assert "model_rejection_reason" in reddit["generation_metadata"]
    assert "**build production-ready ai products with quainy labs**" not in lowered
    assert "as i built my first" not in lowered
    assert "what's your experience" not in lowered
    assert "should we prioritize speed or reliability" not in lowered
    assert "as ai leverages grow" not in lowered
    assert "what truly matters" not in lowered
    assert "turn our culture into real work" not in lowered
    assert "what's the value of this capability-building path" not in lowered
    assert "ever wondered" not in lowered
    assert "i recently stumbled upon" not in lowered
    assert "enhances productivity" not in lowered
    assert "ai-powered projects" not in lowered
    assert "read more about" not in lowered
    assert "start building" not in lowered
    assert "Question for the community:" not in reddit["body"]
    assert reddit["body"].count("?") >= 1
