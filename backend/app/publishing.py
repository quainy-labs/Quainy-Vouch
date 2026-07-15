from __future__ import annotations

import os
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas import Draft, DraftPublishCreate, PublishResult, now_utc, new_id


class LinkedInPublishingAdapter:
    provider_name = "linkedin-local"

    def publish_company_post(
        self,
        draft: Draft,
        payload: DraftPublishCreate,
        page_urn: str,
        page_name: str | None = None,
        access_token: str | None = None,
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


class LinkedInApiPublishingAdapter:
    provider_name = "linkedin-api"

    def publish_company_post(
        self,
        draft: Draft,
        payload: DraftPublishCreate,
        page_urn: str,
        page_name: str | None = None,
        access_token: str | None = None,
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
        if not access_token:
            return PublishResult(
                provider=self.provider_name,
                status="failed",
                draft_id=draft.id,
                page_urn=page_urn,
                page_name=page_name,
                failure_reason="LinkedIn access token is missing.",
                requested_at=requested_at,
            )

        body = {
            "author": page_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": draft.body},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        request = Request(
            "https://api.linkedin.com/v2/ugcPosts",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                provider_post_id = response.headers.get("x-restli-id") or new_id("li_post")
        except (HTTPError, URLError, TimeoutError) as error:
            return PublishResult(
                provider=self.provider_name,
                status="failed",
                draft_id=draft.id,
                page_urn=page_urn,
                page_name=page_name,
                failure_reason=f"LinkedIn publish request failed: {error}",
                requested_at=requested_at,
            )

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
    selected = (provider_name or os.getenv("VOUCH_LINKEDIN_PUBLISHING_PROVIDER") or os.getenv("QUAINY_LINKEDIN_PUBLISHING_PROVIDER", "local")).strip().lower()
    if selected in {"local", "linkedin-local"}:
        return LinkedInPublishingAdapter()
    if selected in {"api", "linkedin-api"}:
        return LinkedInApiPublishingAdapter()
    raise ValueError(f"Unknown LinkedIn publishing provider: {selected}")
