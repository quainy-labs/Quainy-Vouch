from __future__ import annotations

from app.contracts import DraftVariant, RenderedDraft
from app.schemas import CompanyProfile, ContentBrief, ContentOpportunity


class LinkedInCompanyPostAdapter:
    platform = "linkedin"
    content_type = "company_post"

    def variants(self) -> list[DraftVariant]:
        return [
            DraftVariant("Build what matters starts with knowing what is true.", "practical"),
            DraftVariant("Useful company content should come from real work.", "reflective"),
            DraftVariant("Publishing more is not the same as communicating better.", "direct"),
        ]

    def render(
        self,
        variant: DraftVariant,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> RenderedDraft:
        proof = brief.supporting_points[0] if brief.supporting_points else opportunity.summary
        voice_line = "The useful path is controlled context, source visibility, and human approval before anything goes public."
        if variant.style == "reflective":
            middle = (
                "AI can make drafts faster, but trust still depends on the quality of the context "
                "and the judgment around what is worth saying."
            )
        elif variant.style == "direct":
            middle = (
                "A strong communication system should decide what is true, safe, relevant, and supported "
                "before it decides how to format the post."
            )
        else:
            middle = (
                "For builders and small teams, the hard part is turning real work into clear public proof "
                "without drifting into generic AI content."
            )

        preferred = profile.preferred_phrases[0] if profile.preferred_phrases else "production-ready products"
        body = (
            f"{variant.hook}\n\n"
            f"{middle}\n\n"
            f"At Quainy, this connects to a simple principle: {preferred}. {voice_line}\n\n"
            f"Source-backed note: {proof}\n\n"
            "That is the kind of company communication Quainy Vouch is being built for: "
            "specific, grounded, and easier for a human to approve."
        )
        return RenderedDraft(body=body[:1500], hook=variant.hook, hashtags=["#AI", "#ProductBuilding", "#BuilderFirst"])

    def quality_checks(self, body: str, profile: CompanyProfile) -> list[str]:
        checks: list[str] = []
        if not 600 <= len(body) <= 1500:
            checks.append("LinkedIn company post should usually stay between 600 and 1,500 characters.")
        if body.count("\n\n") >= 3:
            checks.append("Uses short paragraphs for LinkedIn readability.")
        if any(phrase.lower() in body.lower() for phrase in profile.preferred_phrases):
            checks.append("Uses at least one preferred company phrase.")
        if "specific" in body.lower() or "source" in body.lower():
            checks.append("Avoids generic-only framing by naming the trust mechanism.")
        return checks
