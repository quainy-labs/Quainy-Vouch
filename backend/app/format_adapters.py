from __future__ import annotations

import re

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
        "Lead with a point of view or operating tension, then earn trust with source-backed detail.",
        "Keep the tone professional, specific, and human-approved without sounding like a template.",
        "Use only claims present in the brief or approved company profile.",
        "Do not invent unsupported metrics, customer counts, revenue, percentages, or growth claims.",
        "Avoid clickbait, hype, generic AI-product framing, and visible planning labels.",
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
                "visible_body_contract": "public LinkedIn copy only; no section headings or planning notes",
                "trust_pattern": "hook, audience relevance, source-backed proof, practical takeaway",
            },
        )

    def variants(self) -> list[DraftVariant]:
        return [
            DraftVariant("Lead with the operational insight.", "practical"),
            DraftVariant("Lead with the human problem.", "reflective"),
            DraftVariant("Lead with the clear takeaway.", "direct"),
        ]

    def render(
        self,
        variant: DraftVariant,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> RenderedDraft:
        supporting = brief.supporting_points or [opportunity.summary]
        proof = clean_linkedin_proof_sentence(supporting[0], 280)
        second_proof = clean_linkedin_proof_sentence(supporting[1], 220) if len(supporting) > 1 else ""
        key_message = clean_key_message(brief.key_message)
        topic_label = public_topic_label(brief.key_message)
        audience = concise_audience(brief.audience or profile.audience)
        preferred_clean = clean_preferred_phrase(profile.preferred_phrases[0] if profile.preferred_phrases else "")
        company_line = (
            profile.one_liner
            or profile.product_summary
            or "We are focused on turning real operating knowledge into useful public communication."
        )
        if variant.style == "reflective":
            hook = f"{audience.capitalize()} do not need another vague update. They need a useful operating signal."
            angle = f"The signal here is about {topic_label.lower()}, but the post only works if the proof stays visible."
        elif variant.style == "direct":
            hook = direct_hook(topic_label, preferred_clean)
            angle = f"This matters for {audience} because the evidence points to a concrete operating decision, not a broad claim."
        else:
            hook = practical_hook(topic_label, preferred_clean)
            angle = f"For {audience}, the useful part is not another announcement. It is seeing what the team can actually support."

        paragraphs = [
            hook,
            angle,
            f"{company_line} That is the bar for the way we talk about the work too.",
            proof,
        ]
        if second_proof and second_proof != proof:
            paragraphs.append(second_proof)
        if preferred_clean:
            paragraphs.append(f"For us, {preferred_clean} means making the proof visible, keeping the claim narrow, and letting the work carry the message.")
        else:
            paragraphs.append("The useful move is simple: make the proof visible, keep the claim narrow, and let the work carry the message.")

        body = "\n\n".join(paragraphs)
        return RenderedDraft(body=body[:1500], hook=hook, hashtags=linkedin_hashtags(profile, brief))

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


class RedditPostAdapter:
    platform = "reddit"
    content_type = "post"
    adapter_name = "reddit_post"
    adapter_version = "1.0.0"
    prompt_version = prompt_versions.version("reddit_post")
    rules = [
        "Render as a Reddit post where the hook field is the title and the body reads like a real community post.",
        "Use community-aware, non-promotional language.",
        "Avoid hashtags, markdown headline formatting, corporate announcement tone, hard selling, and visible planning labels.",
        "Do not invent a first-person user story or pretend the author personally built the project.",
        "Preserve only source-backed claims from the platform-independent brief.",
        "Share a specific situation, what the source-backed detail changes, and one honest discussion question.",
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
                "hook_field": "reddit title",
                "visible_body_contract": "community post body only; no markdown headline, Title/Subreddit fit/Post body labels, or promotional copy",
                "structure": "practical context, source-backed detail, tradeoff, honest discussion question",
                "avoid": "hashtags, sales copy, invented first-person story, corporate announcement tone, generic engagement bait",
            },
        )

    def variants(self) -> list[DraftVariant]:
        return [
            DraftVariant("What would you check before trusting this?", "discussion"),
            DraftVariant("A practical lesson from source-backed work", "practical"),
            DraftVariant("Where this workflow can go wrong", "caution"),
        ]

    def render(
        self,
        variant: DraftVariant,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> RenderedDraft:
        supporting = brief.supporting_points or [opportunity.summary]
        observation = reddit_observation_from_context(brief.key_message, " ".join(supporting))
        tradeoff = reddit_tradeoff_from_context(brief.key_message, " ".join(supporting))
        audience = concise_audience(brief.audience or profile.audience)
        title = reddit_title_from_brief(brief.key_message)
        if variant.style == "caution":
            opening = "A lab is useful when it makes the tradeoffs visible, not when it promises a shortcut."
            question = "What would you want a beginner-facing lab to prove before you would trust it?"
        elif variant.style == "practical":
            opening = f"For {audience}, the interesting part is whether the exercise helps people reason through the work, not just finish it."
            question = "Where do you usually draw the line between moving fast and understanding the tradeoff?"
        else:
            opening = "This kind of exercise seems most useful when it turns tradeoffs into something a learner can inspect."
            question = "What makes a lab stick for you: seeing internals, writing tests, debugging failure cases, or building a capstone?"

        body_parts = [
            opening,
            "",
            observation,
        ]
        if tradeoff and tradeoff != observation:
            body_parts.extend(["", tradeoff])
        body_parts.extend(["", question])
        return RenderedDraft(body="\n".join(body_parts), hook=title, hashtags=[])

    def quality_checks(self, body: str, profile: CompanyProfile, brief: ContentBrief) -> list[str]:
        checks: list[str] = []
        if body.count("?") >= 1:
            checks.append("Uses Reddit post structure with context, source-backed detail, and a discussion question.")
        else:
            checks.append("Review Reddit post structure; expected context, source-backed detail, and a discussion question.")
        if "#" not in body:
            checks.append("Avoids hashtag formatting for Reddit.")
        if not any(label in body for label in ["Title:", "Subreddit fit:", "Post body:", "Question for the community:"]):
            checks.append("Keeps Reddit planning labels out of visible copy.")
        if not any(term in body.lower() for term in ["buy now", "sign up", "limited time"]):
            checks.append("Avoids overt promotional language.")
        if not any(term in body.lower() for term in ["the source material points to this", "meaningful problems:", "culture into real work"]):
            checks.append("Avoids source-dump wording in visible Reddit copy.")
        if not re.search(r"\b[12]\.\s+[A-Z]", body):
            checks.append("Avoids truncated numbered-list source fragments.")
        if has_unsupported_metric(body, brief):
            checks.append("Review any metric-like claim; Reddit post rules prohibit unsupported numbers or growth claims.")
        return checks


def has_unsupported_metric(body: str, brief: ContentBrief) -> bool:
    metric_markers = ["%", "percent", "revenue", "customers", "users", "growth", "increased", "decreased", "x "]
    lowered = body.lower()
    if not any(marker in lowered for marker in metric_markers):
        return False
    approved_context = " ".join([*brief.claims, *brief.supporting_points]).lower()
    return not any(marker in approved_context for marker in metric_markers)


def clean_public_sentence(text: str, max_chars: int) -> str:
    clean = re.sub(r"\s+", " ", text.replace("#", "")).replace("...", ".").strip()
    clean = re.sub(r"^(source-backed note|approved note|note|source):\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^Quainy Context\s+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(
        r"^Quainy (?:Core Context|Labs Source|Public Communication Rules|Vouch Product Source)\s+",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"^Quainy Active Products And Website\s+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^Published Blog Today:\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^Use this file as the shared source of context.+?(?=Quainy|The product|Python|AI Engineering)", "", clean, flags=re.IGNORECASE)
    if len(clean) <= max_chars:
        return clean.rstrip(".") + "."
    window = clean[: max_chars - 1].rstrip()
    sentence_end = max(window.rfind("."), window.rfind("?"), window.rfind("!"))
    if sentence_end >= int(max_chars * 0.45):
        return window[: sentence_end + 1]
    trimmed = window.rsplit(" ", 1)[0].rstrip(" ,;:")
    return trimmed.rstrip(".") + "."


def clean_linkedin_proof_sentence(text: str, max_chars: int) -> str:
    clean = clean_public_sentence(text, max_chars)
    clean = clean.replace("source grounded", "source-grounded").replace("voice consistent", "voice-consistent")
    clean = re.sub(
        r"^([A-Z][\w .'-]{2,80}?\s+(?:is|are)\s+[^.]{8,160}\.)\s+\1\s+",
        r"\1 ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^([A-Z][\w .'-]{2,80}?)\s+is\s+([^.]{8,160}\.)\s+\1\s+is\s+",
        r"\1 is \2 It is ",
        clean,
        count=1,
    )
    return clean


def clean_key_message(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    clean = re.sub(r"^Turn\s+(.+?)\s+into\s+a\s+source-backed\s+update$", r"Share the useful lesson from \1", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^Explain\s+what\s+(.+?)\s+shows\s+about\s+", r"What \1 shows about ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^Share\s+a\s+practical\s+point\s+of\s+view\s+on\s+(.+)$", r"What the approved context shows about \1", clean, flags=re.IGNORECASE)
    return clean[:180].rstrip(" .") or "Share one useful lesson from approved company context"


def reddit_title_from_brief(text: str) -> str:
    clean = clean_key_message(text)
    lowered = clean.lower()
    if is_learning_context(lowered):
        subject = "Python exercise" if "python" in lowered else "hands-on learning path"
        return f"What makes a {subject} useful beyond just finishing it?"
    clean = re.sub(r"^Get hands-on with\s+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^Build\s+", "What is a practical way to build ", clean, flags=re.IGNORECASE)
    if not clean.endswith("?") and any(term in lowered for term in ["lesson", "learn", "principles", "tradeoff", "workflow"]):
        clean = f"What would you check before trusting {clean[0].lower() + clean[1:]}?"
    return clean[:140].rstrip(" .")


def reddit_observation_from_context(key_message: str, supporting_text: str) -> str:
    combined = f"{key_message} {supporting_text}".lower()
    if is_learning_context(combined) and any(term in combined for term in ["test", "tradeoff", "internals", "implementation"]):
        return (
            "The useful angle is not finishing the exercise faster. It is whether the work connects concepts, implementation, "
            "tests, and tradeoffs instead of treating each topic as a separate checklist."
        )
    if is_learning_context(combined):
        return "The useful angle is whether a lab makes the reasoning visible enough for someone else to inspect and challenge."
    return "The useful angle is whether the exercise makes the underlying reasoning visible, not just whether it produces a finished result."


def reddit_tradeoff_from_context(key_message: str, supporting_text: str) -> str:
    combined = f"{key_message} {supporting_text}".lower()
    if "speed" in combined and "reliability" in combined:
        return "That feels like the real tradeoff: move fast enough to learn, but slowly enough that mistakes become inspectable."
    if "capstone" in combined or "testing" in combined or "internals" in combined:
        return "A capstone can help, but only if it forces choices: what to test, what to simplify, and what to understand before adding more AI."
    return "That feels like the real test: whether the learner can explain the decision they made, not just show the output."


def instagram_caption_message(text: str) -> str:
    clean = clean_key_message(text)
    lowered = clean.lower()
    if is_learning_context(lowered):
        return "The useful part is not finishing the exercise. It is seeing the choices behind the work."
    if "product judgment" in lowered:
        return "Product judgment is deciding what is worth building before AI makes building faster."
    if "approved context" in lowered or "source-backed" in lowered:
        return "Better content starts with proof the team can actually support."
    match = re.match(r"^What\s+.+?\s+shows\s+about\s+(.+)$", clean, flags=re.IGNORECASE)
    if match:
        topic = match.group(1).strip(" .").lower()
        return f"{topic.capitalize()} works best when the proof stays visible."
    return clean.rstrip(".") + "."


def instagram_proof_line(text: str) -> str:
    clean = clean_public_sentence(text, 220)
    lowered = clean.lower()
    if is_learning_context(lowered) and any(term in lowered for term in ["test", "tradeoff", "internals", "implementation", "capstone"]):
        return "The concrete standard: implementation, tests, tradeoffs, internals, and capstone work should be visible enough to inspect."
    if "what is worth building" in lowered and "who" in lowered and "ai" in lowered:
        return "The concrete standard: explain what is worth building, who it serves, and how AI changes the work without replacing judgment."
    return clean


def is_learning_context(text: str) -> bool:
    return any(
        marker in text
        for marker in ["lab", "lesson", "learn", "learner", "learning", "exercise", "course", "workshop", "tutorial", "capstone"]
    )


def instagram_hook_for_context(variant: DraftVariant, brief: ContentBrief, proof: str) -> str:
    combined = f"{brief.key_message} {proof}".lower()
    if is_learning_context(combined) and any(term in combined for term in ["test", "tradeoff", "internals", "implementation"]):
        return "A good lab makes the tradeoffs visible."
    if "approved context" in combined or "source-backed" in combined:
        return "Show the proof before the claim."
    return variant.hook


def public_topic_label(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip(" .")
    patterns = [
        r"^Share\s+a\s+practical\s+point\s+of\s+view\s+on\s+(.+)$",
        r"^Explain\s+what\s+.+?\s+shows\s+about\s+(.+)$",
        r"^What\s+.+?\s+shows\s+about\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, clean, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .").lower()
    return clean[:80].strip(" .").lower() or "the operating lesson"


def practical_hook(topic_label: str, preferred: str) -> str:
    topic = topic_label.lower()
    if "lab" in topic and "proof" in topic:
        return "Learning becomes more credible when it leaves behind public proof."
    if "production" in topic and "readiness" in topic:
        return "A demo is a beginning. Production readiness is where the real building starts."
    if "product judgment" in topic:
        return "AI can speed up building, but product judgment decides what is worth building."
    if "first-principles" in topic or "first principles" in topic:
        return "First-principles learning helps builders understand the system, not just follow steps."
    if "ai engineering" in topic:
        return "Useful AI engineering starts with the workflow, not the model."
    if "adherence" in topic:
        return "Patient adherence is not only about reminders. It depends on clear follow-up between visits."
    if "remote" in topic and "monitoring" in topic:
        return "Remote patient monitoring works best when review and follow-up are easy to act on."
    if preferred.lower() == "build what matters":
        return "Build what matters gets stronger when there is visible proof behind it."
    if preferred.lower() == "ship what works":
        return "Ship what works means taking the idea past the demo."
    if preferred:
        return f"{preferred.capitalize()} works best when the idea becomes specific enough to build."
    return f"{topic_label.capitalize()} works best when the idea becomes specific enough to build."


def direct_hook(topic_label: str, preferred: str) -> str:
    topic = topic_label.lower()
    if "lab" in topic and "proof" in topic:
        return "A lab should show the work, not just describe the philosophy."
    if "production" in topic and "readiness" in topic:
        return "Production readiness is the difference between a promising demo and a useful product."
    if "product judgment" in topic:
        return "Product judgment is what keeps AI leverage pointed at real problems."
    if "first-principles" in topic or "first principles" in topic:
        return "First-principles learning gives builders ownership of their decisions."
    if "ai engineering" in topic:
        return "AI engineering is strongest when it is grounded in real workflows."
    if "adherence" in topic:
        return "Patient adherence needs an owner, a status, and a next step."
    if "remote" in topic and "monitoring" in topic:
        return "Remote monitoring is only useful when teams can act on the signal."
    if preferred:
        return f"{preferred.capitalize()}: make the next step visible."
    return f"{topic_label.capitalize()}: make the next step visible."


def concise_audience(audience: str | None) -> str:
    clean = re.sub(r"\s+", " ", audience or "").strip(" .")
    if not clean:
        return "the people this serves"
    if len(clean) <= 90:
        return clean
    if " who " in clean[:120]:
        return clean[: clean.index(" who ")].rstrip(" ,;:")
    return clean[:90].rsplit(" ", 1)[0].rstrip(" ,;:")


def clean_preferred_phrase(phrase: str) -> str:
    return re.sub(r"\s+", " ", phrase or "").strip(" .")


def linkedin_hashtags(profile: CompanyProfile, brief: ContentBrief) -> list[str]:
    terms: list[str] = []
    for phrase in [*profile.content_pillars, brief.key_message]:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9]+", phrase.title().replace("-", " ")):
            if len(word) >= 4 and word.lower() not in {"share", "practical", "point", "view", "explain", "what", "about"}:
                terms.append(word)
            if len(terms) >= 3:
                break
        if len(terms) >= 3:
            break
    hashtags = []
    for term in terms:
        tag = f"#{term[:32]}"
        if tag not in hashtags:
            hashtags.append(tag)
    return hashtags or ["#CompanyBuilding", "#Operations", "#Leadership"]


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
            DraftVariant("Make the useful part easy to see.", "educational"),
            DraftVariant("Show the proof before the claim.", "direct"),
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


class InstagramPostAdapter:
    platform = "instagram"
    content_type = "post"
    adapter_name = "instagram_post"
    adapter_version = "1.0.0"
    prompt_version = prompt_versions.version("instagram_post")
    rules = [
        "Render as a public Instagram caption only; do not include visual direction or production notes in the visible body.",
        "Lead with a short hook, then use a trust cue and short takeaway.",
        "Use short lines rather than LinkedIn-style paragraphs.",
        "Preserve only source-backed claims from the platform-independent brief.",
        "Put hashtags in the hashtags field, not inside the body.",
        "Avoid abstract source-grounding language unless it is tied to a concrete proof detail.",
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
                "visible_body_contract": "public caption only; no Visual direction/Post copy/Hashtags labels",
                "caption_pattern": "hook, source-backed trust cue, takeaway",
            },
        )

    def variants(self) -> list[DraftVariant]:
        return [
            DraftVariant("Build from what is true.", "minimal"),
            DraftVariant("Make the useful part easy to see.", "educational"),
            DraftVariant("Show the work before the claim.", "direct"),
        ]

    def render(
        self,
        variant: DraftVariant,
        profile: CompanyProfile,
        brief: ContentBrief,
        opportunity: ContentOpportunity,
    ) -> RenderedDraft:
        proof = clean_public_sentence(brief.supporting_points[0] if brief.supporting_points else opportunity.summary, 260)
        key_message = instagram_caption_message(brief.key_message)
        proof = instagram_proof_line(proof)
        hook = instagram_hook_for_context(variant, brief, proof)
        if variant.style == "educational":
            body = (
                f"{hook}\n\n"
                f"{key_message}\n\n"
                f"{proof}\n\n"
                "That is the difference between a completed exercise and a learning artifact someone can actually trust."
            )
        elif variant.style == "direct":
            body = (
                f"{hook}\n\n"
                "A strong post should not outrun its evidence.\n\n"
                f"{proof}\n\n"
                "Use the proof first, then choose the format."
            )
        else:
            body = f"{hook}\n\n{key_message}\n\n{proof}"
        return RenderedDraft(
            body=body[:900],
            hook=hook,
            hashtags=["#BuildInPublic", "#ProductJudgment", "#SourceBacked"],
        )

    def quality_checks(self, body: str, profile: CompanyProfile, brief: ContentBrief) -> list[str]:
        checks: list[str] = []
        if len(body) <= 900:
            checks.append("Fits concise Instagram post guidance.")
        else:
            checks.append("Review Instagram post length; this workflow expects concise copy.")
        if not any(label in body for label in ["Visual direction:", "Post copy:", "Hashtags:", "Trust cue:"]):
            checks.append("Keeps Instagram post body as public caption copy.")
        if "proof" in body.lower() or "source-backed note:" in body:
            checks.append("Keeps Instagram post grounded with a visible proof point.")
        if has_unsupported_metric(body, brief):
            checks.append("Review any metric-like claim; Instagram post rules prohibit unsupported numbers or growth claims.")
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
