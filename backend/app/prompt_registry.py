from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptVersion:
    key: str
    version: str
    description: str


class PromptVersionRegistry:
    def __init__(self) -> None:
        self._versions = {
            "brief_builder": PromptVersion(
                key="brief_builder",
                version="brief_builder.v1",
                description="Build a platform-independent content brief from approved sources.",
            ),
            "linkedin_company_post": PromptVersion(
                key="linkedin_company_post",
                version="linkedin_company_post.v1",
                description="Render a LinkedIn company post from a source-grounded brief.",
            ),
            "blog_outline": PromptVersion(
                key="blog_outline",
                version="blog_outline.v1",
                description="Render a source-grounded blog outline with sections and conclusion.",
            ),
            "newsletter_email": PromptVersion(
                key="newsletter_email",
                version="newsletter_email.v1",
                description="Render a source-grounded newsletter draft with subject lines and source links.",
            ),
            "instagram_caption": PromptVersion(
                key="instagram_caption",
                version="instagram_caption.v1",
                description="Render a visual-first Instagram caption from a source-grounded brief.",
            ),
            "instagram_carousel_outline": PromptVersion(
                key="instagram_carousel_outline",
                version="instagram_carousel_outline.v1",
                description="Render a source-grounded Instagram carousel outline with visual direction.",
            ),
        }

    def get(self, key: str) -> PromptVersion:
        if key not in self._versions:
            raise KeyError(f"Prompt version not registered: {key}")
        return self._versions[key]

    def version(self, key: str) -> str:
        return self.get(key).version

    def as_dict(self) -> dict[str, dict[str, str]]:
        return {
            key: {"version": value.version, "description": value.description}
            for key, value in self._versions.items()
        }


prompt_versions = PromptVersionRegistry()
