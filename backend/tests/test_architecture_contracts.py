from app.contracts import DraftVariant, RenderedDraft
from app.drafts import generate_drafts
from app.schemas import CompanyProfile, ContentBrief, ContentOpportunity, DraftGenerationSpec


class ExampleFormatAdapter:
    platform = "example_platform"
    content_type = "example_post"
    adapter_name = "example_adapter"
    adapter_version = "0.1.0"

    def generation_spec(self, brief: ContentBrief) -> DraftGenerationSpec:
        return DraftGenerationSpec(
            content_brief_id=brief.id,
            platform=self.platform,
            content_type=self.content_type,
            adapter_name=self.adapter_name,
            adapter_version=self.adapter_version,
            prompt_version="example_adapter.v1",
            rules=["Example adapter owns platform rules."],
        )

    def variants(self) -> list[DraftVariant]:
        return [DraftVariant(hook="Adapter-owned hook.", style="example")]

    def render(
        self,
        variant: DraftVariant,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> RenderedDraft:
        return RenderedDraft(
            body=f"{variant.hook}\n\n{brief.key_message}\n\nSource-backed note: {opportunity.summary}",
            hook=variant.hook,
            hashtags=["#Example"],
        )

    def quality_checks(self, body: str, profile: CompanyProfile, brief: ContentBrief) -> list[str]:
        return ["Adapter quality check ran."]


def test_core_draft_generation_uses_provided_format_adapter():
    profile = CompanyProfile(organization_id="org_test", preferred_phrases=["source-backed"])
    opportunity = ContentOpportunity(
        organization_id="org_test",
        title="Adapter boundary",
        summary="Approved context can be rendered by a non-LinkedIn adapter.",
        reason_today="Architecture lock",
        source_ids=[],
        freshness_score=0.8,
        relevance_score=0.8,
        confidence_score=0.8,
    )
    brief = ContentBrief(
        opportunity_id=opportunity.id,
        organization_id="org_test",
        objective="Prove adapter boundary.",
        audience="Builders",
        key_message="Format adapters own platform rendering.",
        supporting_points=[],
        claims=[],
        source_ids=[],
    )

    drafts = generate_drafts(profile, brief, opportunity, chunks=[], memory=[], adapter=ExampleFormatAdapter())

    assert len(drafts) == 1
    assert drafts[0].platform == "example_platform"
    assert drafts[0].content_type == "example_post"
    assert drafts[0].hook == "Adapter-owned hook."
    assert drafts[0].hashtags == ["#Example"]
    assert drafts[0].quality_report == ["Adapter quality check ran."]
    assert drafts[0].generation_metadata["adapter_name"] == "example_adapter"
    assert drafts[0].generation_metadata["prompt_version"] == "example_adapter.v1"
