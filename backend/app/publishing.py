from __future__ import annotations

import os

from app.schemas import Draft, DraftPublishCreate, PublishResult, now_utc, new_id


class LinkedInPublishingAdapter:
    provider_name = "linkedin-local"

    def publish_company_post(
        self,
        draft: Draft,
        payload: DraftPublishCreate,
        page_urn: str,
        page_name: str | None = None,
    ) -> PublishResult:
        requested_at = now_utc()
        if payload.simulate_failure:
            return PublishResult(
                provider=self.provider_name,
                status="failed",
                draft_id=draft.id,
                page_urn=page_urn,
                page_name=page_name,
                failure_reason="Simulated LinkedIn publishing failure; approved content was preserved.",
                requested_at=requested_at,
            )

        provider_post_id = new_id("li_post")
        return PublishResult(
            provider=self.provider_name,
            status="published",
            draft_id=draft.id,
            page_urn=page_urn,
            page_name=page_name,
            provider_post_id=provider_post_id,
            published_url=f"https://www.linkedin.com/feed/update/{provider_post_id}",
            requested_at=requested_at,
            published_at=now_utc(),
        )


def build_linkedin_publisher(provider_name: str | None = None) -> LinkedInPublishingAdapter:
    selected = (provider_name or os.getenv("QUAINY_LINKEDIN_PUBLISHING_PROVIDER", "local")).strip().lower()
    if selected in {"local", "linkedin-local"}:
        return LinkedInPublishingAdapter()
    raise ValueError(f"Unknown LinkedIn publishing provider: {selected}")
