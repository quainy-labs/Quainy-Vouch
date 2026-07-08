from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import urlparse

from app.contracts import ExtractedSource, SourceConnector
from app.intelligence import normalize_text


class ManualTextConnector:
    source_type = "manual_note"

    def extract(self, payload: dict[str, Any]) -> ExtractedSource:
        raw_text = str(payload["raw_text"])
        return ExtractedSource(
            title=str(payload["title"]),
            raw_text=normalize_text(raw_text),
            metadata={"connector": self.source_type},
        )


class PlainTextConnector(ManualTextConnector):
    source_type = "text"


class MarkdownConnector:
    source_type = "markdown"

    def extract(self, payload: dict[str, Any]) -> ExtractedSource:
        raw_text = str(payload["raw_text"])
        text = re.sub(r"```.*?```", " ", raw_text, flags=re.DOTALL)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"!\[[^\]]*]\([^)]*\)", " ", text)
        text = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", text)
        text = re.sub(r"[*_~>#-]+", " ", text)
        return ExtractedSource(
            title=str(payload["title"]),
            raw_text=normalize_text(text),
            metadata={"connector": self.source_type, "markdown_stripped": True},
        )


class UrlPageConnector:
    source_type = "url"

    def extract(self, payload: dict[str, Any]) -> ExtractedSource:
        uri = str(payload.get("uri") or "").strip()
        parsed = urlparse(uri)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("URL sources require a single http(s) page URI.")
        raw_text = str(payload["raw_text"])
        text = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", raw_text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = html.unescape(text)
        return ExtractedSource(
            title=str(payload["title"]),
            raw_text=normalize_text(text),
            metadata={
                "connector": self.source_type,
                "uri": uri,
                "domain": parsed.netloc,
                "single_page_only": True,
                "robots_policy": "single selected public page; no domain crawl",
            },
        )


class GitHubReleaseConnector:
    source_type = "github_release"

    def extract(self, payload: dict[str, Any]) -> ExtractedSource:
        uri = str(payload.get("uri") or "").strip()
        owner, repo, release_ref = parse_github_release_uri(uri)
        raw_text = str(payload["raw_text"])
        markdown = MarkdownConnector().extract({"title": payload["title"], "raw_text": raw_text, "uri": uri})
        release_date = parse_release_date(raw_text)
        return ExtractedSource(
            title=str(payload["title"]),
            raw_text=markdown.raw_text,
            metadata={
                "connector": self.source_type,
                "uri": uri,
                "owner": owner,
                "repo": repo,
                "release_ref": release_ref,
                "release_date": release_date,
                "selected_repo_only": True,
                "access_policy": "public GitHub release or changelog only; no private repo access",
            },
        )


class NotionSelectedPageConnector:
    source_type = "notion_page"

    def extract(self, payload: dict[str, Any]) -> ExtractedSource:
        uri = str(payload.get("uri") or "").strip()
        page_id = parse_notion_page_uri(uri)
        raw_text = str(payload["raw_text"])
        markdown = MarkdownConnector().extract({"title": payload["title"], "raw_text": raw_text, "uri": uri})
        return ExtractedSource(
            title=str(payload["title"]),
            raw_text=markdown.raw_text,
            metadata={
                "connector": self.source_type,
                "uri": uri,
                "page_id": page_id,
                "access_scope": "selected_page",
                "auth_flow": "selected Notion page token/OAuth grant; token not stored in source text",
                "revocation": "disable or archive the source to remove it from retrieval and generation",
            },
        )


def parse_notion_page_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme == "notion" and parsed.netloc == "page" and parsed.path.strip("/"):
        return parsed.path.strip("/")
    if parsed.scheme in {"http", "https"} and parsed.netloc.endswith("notion.so"):
        slug = parsed.path.strip("/").split("/")[-1]
        match = re.search(r"([a-fA-F0-9]{32}|[a-fA-F0-9-]{36})$", slug)
        if match:
            return match.group(1)
    raise ValueError("Notion page sources require a selected page URI, such as notion://page/{page_id}.")


def parse_github_release_uri(uri: str) -> tuple[str, str, str | None]:
    parsed = urlparse(uri)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        raise ValueError("GitHub release sources require a selected public github.com owner/repo URI.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub release URI must include owner and repo.")
    owner, repo = parts[0], parts[1]
    release_ref = None
    if len(parts) >= 5 and parts[2] == "releases" and parts[3] == "tag":
        release_ref = parts[4]
    elif len(parts) >= 4 and parts[2] in {"releases", "tag"}:
        release_ref = parts[3]
    elif len(parts) >= 3 and parts[2] not in {"releases", "tags", "blob", "tree"}:
        raise ValueError("GitHub source must point to a repo, release, tag, or changelog page.")
    return owner, repo, release_ref


def parse_release_date(raw_text: str) -> str | None:
    match = re.search(r"(?:released|date|published)[:\s]+(\d{4}-\d{2}-\d{2})", raw_text, flags=re.IGNORECASE)
    return match.group(1) if match else None


def default_source_connectors() -> dict[str, SourceConnector]:
    connectors: list[SourceConnector] = [
        ManualTextConnector(),
        PlainTextConnector(),
        MarkdownConnector(),
        UrlPageConnector(),
        GitHubReleaseConnector(),
        NotionSelectedPageConnector(),
    ]
    return {connector.source_type: connector for connector in connectors}
