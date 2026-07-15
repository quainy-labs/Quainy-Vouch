from app.briefs import PlatformIndependentBriefBuilder
from app.format_adapters import (
    BlogOutlineAdapter,
    InstagramCaptionAdapter,
    InstagramCarouselOutlineAdapter,
    InstagramPostAdapter,
    LinkedInCompanyPostAdapter,
    NewsletterEmailAdapter,
    RedditPostAdapter,
)
from app.schemas import CompanyProfile, ContentOpportunity, SourceChunk


def test_brief_builder_creates_platform_independent_brief():
    profile = CompanyProfile(
        organization_id="org_brief",
        audience="technical founders",
        banned_phrases=["fully autonomous marketing"],
        content_pillars=["source-backed communication"],
    )
    opportunity = ContentOpportunity(
        organization_id="org_brief",
        title="Source-backed company communication",
        summary="Approved source context supports public communication.",
        reason_today="Strong approved context exists.",
        source_ids=["src_brief"],
        freshness_score=0.82,
        relevance_score=0.84,
        confidence_score=0.86,
    )
    chunks = [
        SourceChunk(
            source_id="src_brief",
            organization_id="org_brief",
            chunk_text=(
                "Quainy Vouch turns approved company knowledge into human-reviewed communication. "
                "The workflow keeps source visibility and reviewer control before anything public is exported."
            ),
            chunk_index=0,
        )
    ]

    brief = PlatformIndependentBriefBuilder().build(profile, opportunity, chunks)

    assert "LinkedIn" not in brief.objective
    assert "format adapter" in brief.objective
    assert brief.audience == "technical founders"
    assert brief.supporting_points
    assert "fully autonomous marketing" in brief.do_not_say
    assert brief.builder_metadata["evidence_chunk_ids"] == [chunks[0].id]


def test_linkedin_adapter_exposes_generation_spec_and_metric_guardrail():
    profile = CompanyProfile(organization_id="org_linkedin", preferred_phrases=["source-backed"])
    opportunity = ContentOpportunity(
        organization_id="org_linkedin",
        title="Trustworthy company updates",
        summary="Approved context supports a careful company update.",
        reason_today="Approved source detail exists.",
        source_ids=["src_linkedin"],
        freshness_score=0.8,
        relevance_score=0.8,
        confidence_score=0.8,
    )
    brief = PlatformIndependentBriefBuilder().build(
        profile,
        opportunity,
        [
            SourceChunk(
                source_id="src_linkedin",
                organization_id="org_linkedin",
                chunk_text="The product uses approved context and human review for source-backed communication.",
                chunk_index=0,
            )
        ],
    )
    adapter = LinkedInCompanyPostAdapter()

    spec = adapter.generation_spec(brief)
    body = adapter.render(adapter.variants()[0], profile, brief, opportunity).body
    checks = adapter.quality_checks(
        "Source-backed update.\n\nThis system increased revenue by 45%.\n\nHuman review still matters.\n\nSpecific context matters.",
        profile,
        brief,
    )

    assert spec.platform == "linkedin"
    assert spec.content_type == "company_post"
    assert spec.prompt_version == "linkedin_company_post.v1"
    assert any("unsupported metrics" in rule for rule in spec.rules)
    assert any("unsupported numbers" in check for check in checks)
    assert "Quainy" not in body
    assert "45%" not in body


def test_linkedin_adapter_avoids_visible_template_scaffolding():
    profile = CompanyProfile(
        organization_id="org_linkedin_voice",
        audience="students, developers, founders, curious learners, and one-person builders",
        preferred_phrases=["Build what matters"],
        product_summary="Quainy helps builders turn meaningful ideas into production-ready products.",
    )
    opportunity = ContentOpportunity(
        organization_id="org_linkedin_voice",
        title="Behind the Scenes of Quainy Vouch: Secure Company Communication Made Easy",
        summary="Quainy Vouch supports source-grounded public communication.",
        reason_today="Approved source detail exists.",
        source_ids=["src_linkedin_voice"],
        freshness_score=0.8,
        relevance_score=0.8,
        confidence_score=0.8,
    )
    brief = PlatformIndependentBriefBuilder().build(
        profile,
        opportunity,
        [
            SourceChunk(
                source_id="src_linkedin_voice",
                organization_id="org_linkedin_voice",
                chunk_text=(
                    "Quainy Vouch is an active Quainy product being built now. "
                    "Quainy Vouch is a secure, source grounded company communication agent. "
                    "It helps teams turn approved company knowledge into timely, accurate, voice consistent content across platforms, "
                    "with human approval before publishing."
                ),
                chunk_index=0,
            ),
            SourceChunk(
                source_id="src_linkedin_voice",
                organization_id="org_linkedin_voice",
                chunk_text=(
                    "Quainy public content should help builders think better and build better. "
                    "It should start from real problems, first principles, product judgment, engineering clarity, and production readiness."
                ),
                chunk_index=1,
            ),
        ],
    )
    rendered = LinkedInCompanyPostAdapter().render(LinkedInCompanyPostAdapter().variants()[0], profile, brief, opportunity)

    assert "One concrete detail" not in rendered.body
    assert "A second detail" not in rendered.body
    assert "The takeaway" not in rendered.body
    assert "The approved context is specific" not in rendered.body
    assert "Quainy Vouch is an active Quainy product being built now. Quainy Vouch is" not in rendered.body
    assert "source-grounded" in rendered.body
    assert "voice-consistent" in rendered.body


def test_blog_outline_adapter_uses_same_brief_with_headings_and_source_sections():
    profile = CompanyProfile(
        organization_id="org_blog",
        audience="technical founders",
        preferred_phrases=["approved context"],
    )
    opportunity = ContentOpportunity(
        organization_id="org_blog",
        title="Use approved context for public learning",
        summary="Approved context can support public learning.",
        reason_today="Approved sources contain practical context for public learning.",
        source_ids=["src_blog"],
        freshness_score=0.82,
        relevance_score=0.84,
        confidence_score=0.86,
    )
    brief = PlatformIndependentBriefBuilder().build(
        profile,
        opportunity,
        [
            SourceChunk(
                source_id="src_blog",
                organization_id="org_blog",
                chunk_text="Approved context helps technical founders explain product work with source-backed sections.",
                chunk_index=0,
            )
        ],
    )
    adapter = BlogOutlineAdapter()

    rendered = adapter.render(adapter.variants()[0], profile, brief, opportunity)
    checks = adapter.quality_checks(rendered.body, profile, brief)
    spec = adapter.generation_spec(brief)

    assert spec.platform == "blog"
    assert spec.content_type == "outline"
    assert spec.prompt_version == "blog_outline.v1"
    assert rendered.body.startswith("# ")
    assert "## Introduction" in rendered.body
    assert "## Section 1" in rendered.body
    assert "Source-backed note:" in rendered.body
    assert any("blog outline structure" in check for check in checks)


def test_newsletter_adapter_uses_same_brief_with_subjects_takeaway_and_sources():
    profile = CompanyProfile(
        organization_id="org_newsletter",
        audience="technical founders",
        preferred_phrases=["approved context"],
    )
    opportunity = ContentOpportunity(
        organization_id="org_newsletter",
        title="Share source-backed product judgment",
        summary="Approved context can support a useful subscriber note.",
        reason_today="Approved sources explain why this topic is timely for subscribers.",
        source_ids=["src_newsletter"],
        freshness_score=0.82,
        relevance_score=0.84,
        confidence_score=0.86,
    )
    brief = PlatformIndependentBriefBuilder().build(
        profile,
        opportunity,
        [
            SourceChunk(
                source_id="src_newsletter",
                organization_id="org_newsletter",
                chunk_text="Approved context helps technical founders explain product work with source-backed detail.",
                chunk_index=0,
            )
        ],
    )
    adapter = NewsletterEmailAdapter()

    rendered = adapter.render(adapter.variants()[0], profile, brief, opportunity)
    checks = adapter.quality_checks(rendered.body, profile, brief)
    spec = adapter.generation_spec(brief)

    assert spec.platform == "newsletter"
    assert spec.content_type == "email"
    assert spec.prompt_version == "newsletter_email.v1"
    assert "Subject options:" in rendered.body
    assert "Opening:" in rendered.body
    assert "Context:" in rendered.body
    assert "Takeaway:" in rendered.body
    assert "Sources and links:" in rendered.body
    assert "src_newsletter" in rendered.body
    assert any("subject line options" in check for check in checks)
    assert any("separate from LinkedIn" in check for check in checks)


def test_instagram_adapters_keep_visual_constraints_separate_from_core_message():
    profile = CompanyProfile(
        organization_id="org_instagram",
        audience="builders",
        preferred_phrases=["approved context"],
    )
    opportunity = ContentOpportunity(
        organization_id="org_instagram",
        title="Turn approved context into visual content",
        summary="Approved context can support short visual content.",
        reason_today="Approved sources explain a timely product communication workflow.",
        source_ids=["src_instagram"],
        freshness_score=0.82,
        relevance_score=0.84,
        confidence_score=0.86,
    )
    brief = PlatformIndependentBriefBuilder().build(
        profile,
        opportunity,
        [
            SourceChunk(
                source_id="src_instagram",
                organization_id="org_instagram",
                chunk_text="Approved context helps builders create source-backed content with human review.",
                chunk_index=0,
            )
        ],
    )
    caption_adapter = InstagramCaptionAdapter()
    carousel_adapter = InstagramCarouselOutlineAdapter()

    caption = caption_adapter.render(caption_adapter.variants()[0], profile, brief, opportunity)
    carousel = carousel_adapter.render(carousel_adapter.variants()[0], profile, brief, opportunity)
    caption_checks = caption_adapter.quality_checks(caption.body, profile, brief)
    carousel_checks = carousel_adapter.quality_checks(carousel.body, profile, brief)

    assert caption_adapter.generation_spec(brief).prompt_version == "instagram_caption.v1"
    assert carousel_adapter.generation_spec(brief).prompt_version == "instagram_carousel_outline.v1"
    assert caption.body.startswith("Visual direction:")
    assert "Caption:" in caption.body
    assert "Source-backed note:" in caption.body
    assert "Hashtags:" in caption.body
    assert carousel.body.startswith("Visual direction:")
    assert "Slide 1:" in carousel.body
    assert "Slide 5:" in carousel.body
    assert "Caption note:" in carousel.body
    assert any("short Instagram caption" in check for check in caption_checks)
    assert any("visual direction and five slides" in check for check in carousel_checks)


def test_reddit_and_instagram_post_adapters_are_supported_public_formats():
    profile = CompanyProfile(
        organization_id="org_social",
        audience="builders",
        preferred_phrases=["approved context"],
    )
    opportunity = ContentOpportunity(
        organization_id="org_social",
        title="Turn approved context into public posts",
        summary="Approved context can support useful public posts.",
        reason_today="Approved sources explain a timely source-grounded workflow.",
        source_ids=["src_social"],
        freshness_score=0.82,
        relevance_score=0.84,
        confidence_score=0.86,
    )
    brief = PlatformIndependentBriefBuilder().build(
        profile,
        opportunity,
        [
            SourceChunk(
                source_id="src_social",
                organization_id="org_social",
                chunk_text="Approved context helps builders create source-backed public posts with human review.",
                chunk_index=0,
            )
        ],
    )
    reddit_adapter = RedditPostAdapter()
    instagram_adapter = InstagramPostAdapter()

    reddit = reddit_adapter.render(reddit_adapter.variants()[0], profile, brief, opportunity)
    instagram = instagram_adapter.render(instagram_adapter.variants()[0], profile, brief, opportunity)
    reddit_checks = reddit_adapter.quality_checks(reddit.body, profile, brief)
    instagram_checks = instagram_adapter.quality_checks(instagram.body, profile, brief)

    assert reddit_adapter.generation_spec(brief).platform == "reddit"
    assert reddit_adapter.generation_spec(brief).content_type == "post"
    assert reddit_adapter.generation_spec(brief).prompt_version == "reddit_post.v1"
    assert reddit.body.count("?") >= 1
    assert "Subreddit fit:" not in reddit.body
    assert "Title:" not in reddit.body
    assert "Question for the community:" not in reddit.body
    assert "#" not in reddit.body
    assert any("Reddit post structure" in check for check in reddit_checks)
    assert any("planning labels" in check for check in reddit_checks)

    community_adapter = RedditPostAdapter(target_community="r/learnpython")
    community_reddit = community_adapter.render(community_adapter.variants()[0], profile, brief, opportunity)
    community_spec = community_adapter.generation_spec(brief)
    community_checks = community_adapter.quality_checks(community_reddit.body, profile, brief)

    assert community_spec.metadata["target_community"] == "r/learnpython"
    assert community_spec.metadata["community_rules"] == [
        "Follow r/learnpython rules and posting norms",
        "Avoid self-promotion unless the community explicitly allows it",
        "Keep the post useful, specific, and discussion-oriented",
    ]
    assert "r/learnpython" in community_reddit.body
    assert any("Names the target Reddit community" in check for check in community_checks)

    assert instagram_adapter.generation_spec(brief).platform == "instagram"
    assert instagram_adapter.generation_spec(brief).content_type == "post"
    assert instagram_adapter.generation_spec(brief).prompt_version == "instagram_post.v1"
    assert instagram.body.startswith("Show the proof before the claim.")
    assert "Visual direction:" not in instagram.body
    assert "Post copy:" not in instagram.body
    assert "Hashtags:" not in instagram.body
    assert "Trust cue:" not in instagram.body
    assert instagram.hashtags
    assert any("Instagram post" in check for check in instagram_checks)


def test_reddit_adapter_paraphrases_labs_context_instead_of_dumping_source_blocks():
    profile = CompanyProfile(
        organization_id="org_reddit_labs",
        audience="students, developers, founders, curious learners, and one-person builders",
        content_pillars=["Python First Principles", "Quainy Labs"],
    )
    opportunity = ContentOpportunity(
        organization_id="org_reddit_labs",
        title="Get Hands-on with Quainy Labs' Python First Principles",
        summary="Python First Principles helps learners reason through Python and engineering tradeoffs.",
        reason_today="Approved lab context is available.",
        source_ids=["src_reddit_labs"],
        freshness_score=0.8,
        relevance_score=0.8,
        confidence_score=0.8,
    )
    brief = PlatformIndependentBriefBuilder().build(
        profile,
        opportunity,
        [
            SourceChunk(
                source_id="src_reddit_labs",
                organization_id="org_reddit_labs",
                chunk_text=(
                    "Quainy Labs are public, inspectable learning paths that turn Quainy's culture into real work. "
                    "Python First Principles helps learners understand Python deeply through first principles reasoning, "
                    "implementation, testing, tradeoffs, internals, software engineering, ecosystem knowledge, and capstone projects."
                ),
                chunk_index=0,
            ),
            SourceChunk(
                source_id="src_reddit_labs",
                organization_id="org_reddit_labs",
                chunk_text=(
                    "Quainy is currently organized around three public systems: 1. Meaningful Problems: a dedicated library "
                    "for understanding what is worth solving, who it affects, and why a product should exist. 2. Labs."
                ),
                chunk_index=1,
            ),
        ],
    )
    reddit = RedditPostAdapter().render(RedditPostAdapter().variants()[0], profile, brief, opportunity)
    lowered = reddit.body.lower()

    assert "quainy labs are public" not in lowered
    assert "turn quainy's culture into real work" not in lowered
    assert "meaningful problems:" not in lowered
    assert "1." not in reddit.body
    assert "2." not in reddit.body
    assert "checklist" in lowered
    assert "what makes a lab stick for you" in lowered


def test_instagram_adapter_turns_labs_context_into_caption_instead_of_source_dump():
    profile = CompanyProfile(
        organization_id="org_instagram_labs",
        audience="students, developers, founders, curious learners, and one-person builders",
        content_pillars=["Python First Principles", "Quainy Labs"],
    )
    opportunity = ContentOpportunity(
        organization_id="org_instagram_labs",
        title="Get Hands-on with Quainy Labs' Python First Principles",
        summary="Python First Principles helps learners reason through Python and engineering tradeoffs.",
        reason_today="Approved lab context is available.",
        source_ids=["src_instagram_labs"],
        freshness_score=0.8,
        relevance_score=0.8,
        confidence_score=0.8,
    )
    brief = PlatformIndependentBriefBuilder().build(
        profile,
        opportunity,
        [
            SourceChunk(
                source_id="src_instagram_labs",
                organization_id="org_instagram_labs",
                chunk_text=(
                    "Quainy Labs are public, inspectable learning paths that turn Quainy's culture into real work. "
                    "Python First Principles helps learners understand Python deeply through first principles reasoning, "
                    "implementation, testing, tradeoffs, internals, software engineering, ecosystem knowledge, and capstone projects."
                ),
                chunk_index=0,
            )
        ],
    )
    adapter = InstagramPostAdapter()
    instagram = adapter.render(adapter.variants()[1], profile, brief, opportunity)
    lowered = instagram.body.lower()

    assert "real context makes better content" not in lowered
    assert "get hands-on with quainy labs" not in lowered
    assert "quainy labs are public" not in lowered
    assert "turn quainy's culture into real work" not in lowered
    assert "tests" in lowered
    assert "tradeoffs" in lowered
    assert "one grounded proof point" not in lowered
    assert "completed exercise" in lowered
    assert "learning artifact" in lowered
