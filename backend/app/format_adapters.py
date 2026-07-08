from __future__ import annotations

from app.contracts import DraftVariant, RenderedDraft
from app.prompt_registry import prompt_versions
from app.schemas import CompanyProfile, ContentBrief, ContentOpportunity, DraftGenerationSpec


class LinkedInCompanyPostAdapter:
    platform = "linkedin"
    content_type = "company_post"
    adapter_name = "linkedin_company_post"
    adapter_version = "1.0.0"
    prompt_version = prompt_versions.version("linkedin_company_post")
    rules = [
        "Render as a LinkedIn company post between 600 and 1,500 characters.",
        "Use short paragraphs for scanability.",
        "Keep the tone professional, specific, and human-approved.",
        "Use only claims present in the brief or approved company profile.",
        "Do not invent unsupported metrics, customer counts, revenue, percentages, or growth claims.",
        "Avoid clickbait, hype, and generic AI-product framing.",
    ]

    def generation_spec(self, brief: ContentBrief) -> DraftGenerationSpec:
        return DraftGenerationSpec(
            content_brief_id=brief.id,
            platform=self.platform,
            content_type=self.content_type,
            adapter_name=self.adapter_name,
            adapter_version=self.adapter_version,
            prompt_version=self.prompt_version,
            rules=self.rules,
            metadata={
                "brief_prompt_version": brief.prompt_version,
                "max_characters": 1500,
                "min_characters": 600,
                "preferred_paragraphs": "4-6",
            },
        )

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
        company_line = (
            profile.one_liner
            or profile.product_summary
            or "The company is turning approved knowledge into clearer public communication."
        )
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
            f"{company_line}\n\n"
            f"This connects to a simple principle: {preferred}. {voice_line}\n\n"
            f"Source-backed note: {proof}\n\n"
            f"That is the message behind this brief: {brief.key_message}. "
            "Specific, grounded, and easier for a human to approve."
        )
        return RenderedDraft(body=body[:1500], hook=variant.hook, hashtags=["#AI", "#ProductBuilding", "#BuilderFirst"])

    def quality_checks(self, body: str, profile: CompanyProfile, brief: ContentBrief) -> list[str]:
        checks: list[str] = []
        if not 600 <= len(body) <= 1500:
            checks.append("LinkedIn company post should usually stay between 600 and 1,500 characters.")
        else:
            checks.append("Fits LinkedIn company-post length guidance.")
        if 3 <= body.count("\n\n") <= 6:
            checks.append("Uses short paragraphs for LinkedIn readability.")
        else:
            checks.append("Review paragraph rhythm for LinkedIn scanability.")
        if any(phrase.lower() in body.lower() for phrase in profile.preferred_phrases):
            checks.append("Uses at least one preferred company phrase.")
        if "specific" in body.lower() or "source" in body.lower():
            checks.append("Avoids generic-only framing by naming the trust mechanism.")
        if has_unsupported_metric(body, brief):
            checks.append("Review any metric-like claim; adapter rules prohibit unsupported numbers or growth claims.")
        return checks


def has_unsupported_metric(body: str, brief: ContentBrief) -> bool:
    metric_markers = ["%", "percent", "revenue", "customers", "users", "growth", "increased", "decreased", "x "]
    lowered = body.lower()
    if not any(marker in lowered for marker in metric_markers):
        return False
    approved_context = " ".join([*brief.claims, *brief.supporting_points]).lower()
    return not any(marker in approved_context for marker in metric_markers)


class BlogOutlineAdapter:
    platform = "blog"
    content_type = "outline"
    adapter_name = "blog_outline"
    adapter_version = "1.0.0"
    prompt_version = prompt_versions.version("blog_outline")
    rules = [
        "Render as a blog outline with a title, introduction, sections, examples, and conclusion.",
        "Use the same platform-independent brief without LinkedIn-specific framing.",
        "Each main section must include source-backed notes from the brief.",
        "Keep claims grounded in approved sources and avoid unsupported metrics.",
        "Include search intent or reader intent when it helps the blog structure.",
    ]

    def generation_spec(self, brief: ContentBrief) -> DraftGenerationSpec:
        return DraftGenerationSpec(
            content_brief_id=brief.id,
            platform=self.platform,
            content_type=self.content_type,
            adapter_name=self.adapter_name,
            adapter_version=self.adapter_version,
            prompt_version=self.prompt_version,
            rules=self.rules,
            metadata={
                "brief_prompt_version": brief.prompt_version,
                "expected_sections": "title, intro, 3 sections, conclusion",
                "format": "markdown-outline",
            },
        )

    def variants(self) -> list[DraftVariant]:
        return [
            DraftVariant("Practical guide", "guide"),
            DraftVariant("Point-of-view article", "pov"),
            DraftVariant("Launch or progress explainer", "explainer"),
        ]

    def render(
        self,
        variant: DraftVariant,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> RenderedDraft:
        supporting = brief.supporting_points or [opportunity.summary]
        first = supporting[0]
        second = supporting[1] if len(supporting) > 1 else first
        third = supporting[2] if len(supporting) > 2 else second
        audience = brief.audience or profile.audience or "the target reader"
        title = f"{brief.key_message}: {variant.hook}"
        if variant.style == "pov":
            reader_intent = "Reader intent: understand the company belief behind this topic and why it matters now."
        elif variant.style == "explainer":
            reader_intent = "Reader intent: understand what changed, what evidence supports it, and what happens next."
        else:
            reader_intent = "Reader intent: learn a practical way to use the source-backed insight."

        body = (
            f"# {title}\n\n"
            f"## Introduction\n"
            f"- Audience: {audience}\n"
            f"- Core message: {brief.key_message}\n"
            f"- {reader_intent}\n\n"
            f"## Section 1: Why this is worth writing now\n"
            f"- Use the opportunity rationale: {opportunity.reason_today}\n"
            f"- Source-backed note: {first}\n\n"
            f"## Section 2: What the reader should understand\n"
            f"- Explain the problem, decision, or product belief behind the brief.\n"
            f"- Source-backed note: {second}\n\n"
            f"## Section 3: Example or application\n"
            f"- Show how this idea affects {audience}.\n"
            f"- Source-backed note: {third}\n\n"
            f"## Conclusion\n"
            f"- Return to the key message: {brief.key_message}\n"
            "- End with a clear, human-approved takeaway.\n"
        )
        return RenderedDraft(body=body, hook=title, hashtags=[])

    def quality_checks(self, body: str, profile: CompanyProfile, brief: ContentBrief) -> list[str]:
        checks: list[str] = []
        if body.startswith("# ") and body.count("\n## ") >= 4:
            checks.append("Uses blog outline structure with title, introduction, sections, and conclusion.")
        else:
            checks.append("Review blog outline structure; expected markdown headings.")
        if "Source-backed note:" in body:
            checks.append("Includes source-backed notes in blog sections.")
        if "Reader intent:" in body:
            checks.append("Includes reader or search intent for blog planning.")
        if any(phrase.lower() in body.lower() for phrase in profile.preferred_phrases):
            checks.append("Uses at least one preferred company phrase.")
        if has_unsupported_metric(body, brief):
            checks.append("Review any metric-like claim; blog rules prohibit unsupported numbers or growth claims.")
        return checks


class NewsletterEmailAdapter:
    platform = "newsletter"
    content_type = "email"
    adapter_name = "newsletter_email"
    adapter_version = "1.0.0"
    prompt_version = prompt_versions.version("newsletter_email")
    rules = [
        "Render as a newsletter email draft with subject line options.",
        "Use an opening/context/takeaway structure rather than social-post pacing.",
        "Preserve only source-backed claims from the platform-independent brief.",
        "Include a source or link section so reviewers can verify the basis of the note.",
        "Keep the voice useful, calm, and relationship-oriented for subscribers.",
    ]

    def generation_spec(self, brief: ContentBrief) -> DraftGenerationSpec:
        return DraftGenerationSpec(
            content_brief_id=brief.id,
            platform=self.platform,
            content_type=self.content_type,
            adapter_name=self.adapter_name,
            adapter_version=self.adapter_version,
            prompt_version=self.prompt_version,
            rules=self.rules,
            metadata={
                "brief_prompt_version": brief.prompt_version,
                "subject_line_options": 3,
                "structure": "subject_options, opening, context, takeaway, sources",
            },
        )

    def variants(self) -> list[DraftVariant]:
        return [
            DraftVariant("A practical note on what is worth saying now", "practical"),
            DraftVariant("What this update means for careful builders", "relationship"),
            DraftVariant("A source-backed view from the latest work", "editorial"),
        ]

    def render(
        self,
        variant: DraftVariant,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> RenderedDraft:
        supporting = brief.supporting_points or [opportunity.summary]
        first = supporting[0]
        second = supporting[1] if len(supporting) > 1 else first
        preferred = profile.preferred_phrases[0] if profile.preferred_phrases else "approved company knowledge"
        audience = brief.audience or profile.audience or "subscribers"
        source_refs = ", ".join(brief.source_ids) if brief.source_ids else "approved source context"

        if variant.style == "relationship":
            opening = (
                f"This note is for {audience}: a quieter look at why this topic is worth attention "
                "before it becomes another public update."
            )
            takeaway = "The useful takeaway is to keep the message close to evidence and easy for a human to approve."
        elif variant.style == "editorial":
            opening = (
                "There is a stronger story here than a quick announcement: the source context points to a clear "
                "belief about how the work should be understood."
            )
            takeaway = "The useful takeaway is to turn real work into a durable point of view, not a disposable post."
        else:
            opening = (
                f"Here is a practical read on {brief.key_message.lower()} and why it matters for {audience}."
            )
            takeaway = "The useful takeaway is to publish from verified context, then adapt the format to the reader."

        body = (
            "Subject options:\n"
            f"- {brief.key_message}\n"
            f"- {variant.hook}\n"
            f"- Why this matters now: {opportunity.title}\n\n"
            "Opening:\n"
            f"{opening}\n\n"
            "Context:\n"
            f"{opportunity.reason_today} The brief centers on {preferred} while staying grounded in approved source material.\n\n"
            "Source-backed detail:\n"
            f"- {first}\n"
            f"- {second}\n\n"
            "Takeaway:\n"
            f"{takeaway} The core message remains: {brief.key_message}.\n\n"
            "Sources and links:\n"
            f"- Review source references before sending: {source_refs}\n"
        )
        return RenderedDraft(body=body, hook=variant.hook, hashtags=[])

    def quality_checks(self, body: str, profile: CompanyProfile, brief: ContentBrief) -> list[str]:
        checks: list[str] = []
        required_sections = ["Subject options:", "Opening:", "Context:", "Takeaway:", "Sources and links:"]
        if all(section in body for section in required_sections):
            checks.append("Uses newsletter structure with subject options, opening, context, takeaway, and sources.")
        else:
            checks.append("Review newsletter structure; expected subject options, opening, context, takeaway, and sources.")
        if body.count("- ") >= 3 and "Subject options:" in body:
            checks.append("Includes multiple subject line options.")
        if "Sources and links:" in body and any(source_id in body for source_id in brief.source_ids):
            checks.append("Includes source references for reviewer verification.")
        if any(phrase.lower() in body.lower() for phrase in profile.preferred_phrases):
            checks.append("Uses at least one preferred company phrase.")
        if "linkedin" not in body.lower() and "#" not in body:
            checks.append("Keeps newsletter voice separate from LinkedIn formatting.")
        if has_unsupported_metric(body, brief):
            checks.append("Review any metric-like claim; newsletter rules prohibit unsupported numbers or growth claims.")
        return checks


class InstagramCaptionAdapter:
    platform = "instagram"
    content_type = "caption"
    adapter_name = "instagram_caption"
    adapter_version = "1.0.0"
    prompt_version = prompt_versions.version("instagram_caption")
    rules = [
        "Render as a short Instagram caption with a strong first line.",
        "Start from a visual-first idea before the caption text.",
        "Use concise wording and avoid long LinkedIn-style paragraphs.",
        "Preserve only source-backed claims from the platform-independent brief.",
        "Include caption-aware hashtags without making them carry factual claims.",
    ]

    def generation_spec(self, brief: ContentBrief) -> DraftGenerationSpec:
        return DraftGenerationSpec(
            content_brief_id=brief.id,
            platform=self.platform,
            content_type=self.content_type,
            adapter_name=self.adapter_name,
            adapter_version=self.adapter_version,
            prompt_version=self.prompt_version,
            rules=self.rules,
            metadata={
                "brief_prompt_version": brief.prompt_version,
                "max_characters": 900,
                "visual_direction_required": True,
            },
        )

    def variants(self) -> list[DraftVariant]:
        return [
            DraftVariant("Build from what is true.", "minimal"),
            DraftVariant("Real context makes better content.", "educational"),
            DraftVariant("Before you post, prove it.", "direct"),
        ]

    def render(
        self,
        variant: DraftVariant,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> RenderedDraft:
        proof = brief.supporting_points[0] if brief.supporting_points else opportunity.summary
        visual = (
            "A clean workspace shot with one highlighted source note, one draft card, and one approval check."
        )
        if variant.style == "educational":
            caption = (
                f"{variant.hook}\n\n"
                f"{brief.key_message}\n\n"
                "The useful part is not more content. It is knowing what is approved, source-backed, and ready for review.\n\n"
                f"Source-backed note: {proof}"
            )
        elif variant.style == "direct":
            caption = (
                f"{variant.hook}\n\n"
                "A strong post should not outrun its evidence.\n\n"
                f"Use approved context first, then adapt the format. Source-backed note: {proof}"
            )
        else:
            caption = (
                f"{variant.hook}\n\n"
                f"{brief.key_message}\n\n"
                f"Source-backed note: {proof}"
            )
        body = (
            f"Visual direction: {visual}\n\n"
            "Caption:\n"
            f"{caption}\n\n"
            "Hashtags: #BuildInPublic #ProductJudgment #SourceBacked"
        )
        return RenderedDraft(
            body=body[:900],
            hook=variant.hook,
            hashtags=["#BuildInPublic", "#ProductJudgment", "#SourceBacked"],
        )

    def quality_checks(self, body: str, profile: CompanyProfile, brief: ContentBrief) -> list[str]:
        checks: list[str] = []
        if len(body) <= 900:
            checks.append("Fits short Instagram caption guidance.")
        else:
            checks.append("Review caption length; Instagram caption should stay concise for this workflow.")
        if body.startswith("Visual direction:") and "Caption:" in body:
            checks.append("Includes visual-first direction before caption copy.")
        if "Hashtags:" in body:
            checks.append("Includes caption-aware hashtags.")
        if "Source-backed note:" in body:
            checks.append("Keeps caption grounded with a source-backed note.")
        if has_unsupported_metric(body, brief):
            checks.append("Review any metric-like claim; caption rules prohibit unsupported numbers or growth claims.")
        return checks


class InstagramCarouselOutlineAdapter:
    platform = "instagram"
    content_type = "carousel_outline"
    adapter_name = "instagram_carousel_outline"
    adapter_version = "1.0.0"
    prompt_version = prompt_versions.version("instagram_carousel_outline")
    rules = [
        "Render as an Instagram carousel outline with slide-by-slide copy.",
        "Keep visual direction separate from the core source-backed message.",
        "Use short slide text and clear progression.",
        "Preserve only source-backed claims from the platform-independent brief.",
        "Include a final slide with a useful takeaway or approval-oriented CTA.",
    ]

    def generation_spec(self, brief: ContentBrief) -> DraftGenerationSpec:
        return DraftGenerationSpec(
            content_brief_id=brief.id,
            platform=self.platform,
            content_type=self.content_type,
            adapter_name=self.adapter_name,
            adapter_version=self.adapter_version,
            prompt_version=self.prompt_version,
            rules=self.rules,
            metadata={
                "brief_prompt_version": brief.prompt_version,
                "slides": 5,
                "visual_direction_required": True,
            },
        )

    def variants(self) -> list[DraftVariant]:
        return [
            DraftVariant("From context to content", "workflow"),
            DraftVariant("Proof before publishing", "proof"),
            DraftVariant("Make the message visible", "visual"),
        ]

    def render(
        self,
        variant: DraftVariant,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> RenderedDraft:
        supporting = brief.supporting_points or [opportunity.summary]
        first = supporting[0]
        second = supporting[1] if len(supporting) > 1 else first
        audience = brief.audience or profile.audience or "the reader"
        body = (
            "Visual direction: Use a simple five-slide carousel with high-contrast text, one idea per slide, "
            "and small source/review markers in the corner.\n\n"
            f"Slide 1: {variant.hook}\n"
            f"- Visual: Approved source note beside a blank draft.\n"
            f"- Copy: {brief.key_message}\n\n"
            "Slide 2: Why it matters now\n"
            f"- Visual: Timeline or signal card.\n"
            f"- Copy: {opportunity.reason_today}\n\n"
            "Slide 3: Source-backed detail\n"
            f"- Visual: Highlighted evidence snippet.\n"
            f"- Copy: {first}\n\n"
            f"Slide 4: What {audience} should remember\n"
            "- Visual: Three small checks for truth, relevance, and review.\n"
            f"- Copy: {second}\n\n"
            "Slide 5: Takeaway\n"
            "- Visual: Draft card moving into approval.\n"
            "- Copy: Build the message from approved context, then choose the format.\n\n"
            "Caption note: Keep the post concise and point back to the source-backed message."
        )
        return RenderedDraft(body=body, hook=variant.hook, hashtags=["#ProductJudgment", "#SourceBacked"])

    def quality_checks(self, body: str, profile: CompanyProfile, brief: ContentBrief) -> list[str]:
        checks: list[str] = []
        if body.startswith("Visual direction:") and body.count("Slide ") >= 5:
            checks.append("Uses carousel structure with visual direction and five slides.")
        else:
            checks.append("Review carousel outline; expected visual direction and slide-by-slide copy.")
        if "Source-backed detail" in body:
            checks.append("Includes a source-backed carousel slide.")
        if "Caption note:" in body:
            checks.append("Keeps caption guidance separate from carousel message structure.")
        if has_unsupported_metric(body, brief):
            checks.append("Review any metric-like claim; carousel rules prohibit unsupported numbers or growth claims.")
        return checks
