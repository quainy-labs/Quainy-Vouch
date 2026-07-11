from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
API_BASES = ["http://127.0.0.1:8000", "http://127.0.0.1:8001"]


QUAINY_CORE_SOURCE = """
# Quainy Core Context

Quainy is a builder-first AI ecosystem helping people turn meaningful ideas into production-ready products
through AI leverage, engineering clarity, and product judgment.

Quainy exists because AI is making raw code and demos easier to generate, but the full act of building still matters:
product judgment, market understanding, architecture, quality, iteration, and production readiness.

Quainy's mission is to help ambitious builders move from insight to production-ready products by learning how to choose,
build, test, ship, and improve useful AI-native products.

Quainy is for students who want to become builders, developers who want stronger product judgment, curious learners,
founders, creators, communities, and teams that need practical technology capability.

Quainy should feel serious but welcoming, practical but curious, deep but understandable, builder-first, open,
honest, and public-learning oriented. It should not feel like a generic course marketplace, AI hype brand,
motivational productivity community, shallow tutorial library, or corporate training vendor.

The public one-liner is: Quainy is a builder-first AI ecosystem helping people turn meaningful ideas into
production-ready products through AI leverage, engineering clarity, and product judgment.

Useful public messages include Build what matters, Ship what works, develop product judgment, reason from first
principles, start with problems, build production-ready products, create meaningful impact, learn in public,
and move from idea to useful product.
""".strip()


LABS_SOURCE = """
# Quainy Labs Source

Quainy Labs are public, inspectable learning paths that turn Quainy's culture into real work.

Python First Principles helps learners understand Python deeply through first-principles reasoning,
implementation, testing, tradeoffs, internals, software engineering, ecosystem knowledge, and capstone projects.
It is not just a syntax tutorial. It is a capability-building path that helps learners understand why code works,
how it fails, and how to reason through problems.

AI Engineering First Principles helps learners build reliable intelligent systems from real workflows.
It starts with deciding when AI is useful, designing system boundaries, organizing data and context,
using models as components, building retrieval and tool-using systems, evaluating quality, handling production concerns,
and improving with feedback. It teaches when not to use AI as seriously as when to use AI.

The public story for Quainy Labs should connect learning to visible proof: repositories, demos, notes, systems,
tradeoff explanations, and production-minded build paths. It should avoid generic course-marketplace language and
instead show how curious learners become capable, independent builders.
""".strip()


CONTENT_RULES_SOURCE = """
# Quainy Public Communication Rules

Quainy public content should help builders think better and build better. It should start from real problems,
first principles, product judgment, engineering clarity, and production readiness.

Strong Quainy content usually does one of these jobs:

- explains why demos are not the finish line and what production readiness requires;
- teaches builders how to reason from problem to product decision;
- shows why AI leverage still needs product judgment, architecture, evaluation, and iteration;
- turns a lab, repo, build note, or experiment into public proof of capability creation;
- helps one-person builders understand the path from idea to useful product.

The voice should be serious but welcoming, practical but curious, deep but understandable, and modern without hype.
Use phrases like "Build what matters", "Ship what works", "product judgment", "production-ready products",
"first-principles thinking", "learn in public", and "move from idea to useful product".

Avoid public claims about guaranteed income, viral growth, replacing teams, AI replacing human thinking, or Quainy
being a generic course marketplace. Do not use internal strategy language such as funnel, conversion, monetization,
or revenue in public-facing copy.
""".strip()


QUAINY_PRODUCTS_SOURCE = """
# Quainy Active Products And Website

Quainy is currently organized around three public systems:

1. Meaningful Problems: a dedicated library for understanding what is worth solving, who it affects,
and why a product should exist.

2. Quainy Open Paths: learning paths, tutorials, notes, and first-principles maps that align knowledge
with product ideas and vision.

3. Quainy Labs: builder projects based on meaningful problems, designed to develop judgment, production skill,
proof, and earning potential.

The homepage currently frames Quainy as a builder-first AI ecosystem with the headline:
"Build what matters. Ship what works."

The public product story is that AI can write code, assemble interfaces, and generate working demos,
but Quainy focuses on what comes after and around that: architecture, quality, testing, deployment,
feedback, iteration, and the discipline to serve real users.

The Quainy system is not passive content. Every path is designed to help people move from insight to
production-quality building, product judgment, technical clarity, and visible ownership.
""".strip()


TODAY_BLOG_SOURCE = """
# Published Blog Today: Product Judgment in the AI Era

Quainy published a blog post on July 11, 2026 titled "Product Judgment in the AI Era".

The post explains how builders decide what is worth building, who it should serve, what promise to make,
and how to use AI without losing product sense.

The post connects directly to Quainy's public message: AI can speed up code and demos, but product judgment
decides what is worth building, what problem matters, who the user is, and what promise the product should make.

This is a timely content opportunity because the blog is new today and can become:

- a LinkedIn company post announcing the blog;
- a founder-style post about why product judgment matters more as AI accelerates execution;
- a short carousel outline explaining the questions builders should ask before using AI to build;
- a newsletter note pointing readers to the new blog and Quainy's wider builder-first philosophy.

Any public content about this blog should avoid vague AI hype. It should frame product judgment as the human
skill that keeps AI leverage pointed at real problems and useful products.
""".strip()


QUAINY_VOUCH_SOURCE = """
# Quainy Vouch Product Source

Quainy Vouch is an active Quainy product being built now.

Quainy Vouch is a secure, source-grounded company communication agent. It helps teams turn approved company
knowledge into timely, accurate, voice-consistent content across platforms, with human approval before publishing.

The product is not just a LinkedIn post generator. It helps companies decide what is true, safe, relevant,
and worth publishing today. It uses approved context, checks claims against sources, considers timing,
adapts messages to platform and content type, and asks a human before anything is published.

The current workflow supports signup, organization onboarding, organization profile setup, source upload or links,
knowledge readiness, opportunity generation, brief creation, draft generation, review, export, publishing identifiers,
manual performance capture, and learning from what performs.

Quainy Vouch is relevant to Quainy's own story because it is a proof artifact: Quainy is building a production-minded
AI-native product that uses source grounding, review workflows, model provider flexibility, local LLM support,
and measurable improvement loops.

A strong content opportunity should explain what Quainy Vouch is teaching Quainy about building useful AI products:
context quality matters, source grounding matters, human review matters, and generic AI output is not enough.
""".strip()


def request_json(
    base: str,
    method: str,
    path: str,
    payload: dict | None = None,
    token: str | None = None,
    timeout: int = 30,
) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with {error.code}: {detail}") from error


def find_api_base() -> str:
    for base in API_BASES:
        try:
            data = request_json(base, "GET", "/health")
            if data.get("status") == "ok":
                return base
        except (RuntimeError, URLError, TimeoutError):
            continue
    raise RuntimeError("Could not reach the local Quainy Vouch API. Start the backend or Docker Compose first.")


def add_source(base: str, token: str, organization_id: str, title: str, raw_text: str) -> dict:
    return request_json(
        base,
        "POST",
        f"/organizations/{organization_id}/sources",
        {
            "source_type": "markdown",
            "title": title,
            "uri": f"seed://quainy-test/{title.lower().replace(' ', '-')}",
            "raw_text": raw_text,
            "approval_status": "approved",
            "freshness_days": 180,
        },
        token,
    )


def generate_non_deterministic_opportunities(base: str, token: str, organization_id: str) -> list[dict]:
    last_titles: list[str] = []
    for attempt in range(1, 4):
        opportunities = request_json(
            base,
            "POST",
            f"/organizations/{organization_id}/opportunities/generate",
            token=token,
            timeout=180,
        )["opportunities"]
        last_titles = [opportunity["title"] for opportunity in opportunities[:5]]
        top_title = opportunities[0]["title"].lower() if opportunities else ""
        top_is_not_scaffold = not top_title.startswith("share a practical point of view")
        top_is_priority = any(term in top_title for term in ["vouch", "product judgment", "blog"])
        if opportunities and top_is_not_scaffold and top_is_priority:
            return opportunities
        model_calls = request_json(base, "GET", f"/organizations/{organization_id}/model-calls", token=token)
        latest = model_calls[0] if model_calls else {}
        print(
            f"Attempt {attempt}: model opportunity was not promoted. "
            f"top={top_title!r} latest model status={latest.get('status')} "
            f"provider={latest.get('provider')} error={latest.get('error_message')}",
            file=sys.stderr,
        )
    raise RuntimeError(f"Top opportunity is still deterministic scaffolding after retries: {last_titles}")


def configure_local_llm(base: str, token: str, organization_id: str) -> dict:
    candidates = [
        ("http://host.docker.internal:11434/v1", "Docker backend to host Ollama"),
        ("http://127.0.0.1:11434/v1", "Local backend to local Ollama"),
    ]
    last_error = ""
    for generation_base_url, label in candidates:
        settings = {
            "generation_provider": "local",
            "generation_model": "llama3.2:3b",
            "generation_base_url": generation_base_url,
            "generation_api_key_env_var": None,
            "embedding_provider": "local",
            "embedding_model": "embeddinggemma:latest",
            "embedding_base_url": generation_base_url,
            "embedding_api_key_env_var": None,
            "local_runtime": "ollama",
            "enabled": True,
        }
        try:
            request_json(base, "PATCH", f"/organizations/{organization_id}/ai-provider-settings", settings, token)
            result = request_json(base, "POST", f"/organizations/{organization_id}/ai-provider-settings/test", token=token)
            if result.get("status") == "succeeded":
                return {"label": label, **result}
            last_error = str(result)
        except Exception as error:
            last_error = str(error)
    raise RuntimeError(f"Could not configure local Ollama LLM for this workspace: {last_error}")


def main() -> None:
    base = find_api_base()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    email = f"quainy.test.{stamp}@example.com"
    password = f"QuainyTest!{stamp[-6:]}"

    signup = request_json(
        base,
        "POST",
        "/auth/signup",
        {
            "name": "Quainy Test Owner",
            "email": email,
            "password": password,
            "organization_name": "Quainy Test Workspace",
            "website_url": "https://quainy.com",
            "industry": "AI education, builder ecosystem, and AI-native product practice",
            "description": "A builder-first AI ecosystem helping people turn meaningful ideas into production-ready products.",
            "audience_summary": "Students, developers, founders, curious learners, and one-person builders",
            "default_timezone": "Asia/Kolkata",
        },
    )
    token = str(signup["token"])
    organization_id = signup["workspace"]["organization"]["id"]

    request_json(
        base,
        "PATCH",
        f"/organizations/{organization_id}/profile",
        {
            "one_liner": "Quainy helps builders turn meaningful ideas into production-ready products.",
            "mission": "Help ambitious builders move from insight to production-ready products by learning how to choose, build, test, ship, and improve useful AI-native products.",
            "product_summary": "Quainy is a builder-first AI ecosystem with labs, build paths, and tools for product judgment, AI leverage, engineering clarity, and production readiness.",
            "audience": "students, developers, founders, curious learners, and one-person builders who want to build useful AI-native products",
            "voice_rules": [
                "Serious but welcoming.",
                "Practical but curious.",
                "Deep but understandable.",
                "Start from problems and first principles.",
                "Avoid hype, fear hooks, and generic course language.",
            ],
            "preferred_phrases": [
                "Build what matters.",
                "Ship what works.",
                "product judgment",
                "production-ready products",
                "first-principles thinking",
                "learn in public",
                "move from idea to useful product",
            ],
            "banned_phrases": [
                "go viral",
                "10x your content",
                "replace your team",
                "guaranteed income",
                "AI will replace",
                "course marketplace",
            ],
            "approved_claims": [
                "Quainy is a builder-first AI ecosystem.",
                "Quainy helps builders turn meaningful ideas into production-ready products.",
                "Quainy Labs are public, inspectable learning paths.",
                "Python First Principles and AI Engineering First Principles are Quainy Labs.",
            ],
            "forbidden_claims": [
                "Quainy guarantees income, engagement, or revenue.",
                "Quainy replaces human product judgment.",
                "Quainy is only a course marketplace.",
            ],
            "content_pillars": [
                "production readiness",
                "product judgment",
                "first-principles learning",
                "AI engineering practice",
                "Quainy Labs proof artifacts",
                "one-person builder capability",
            ],
            "sensitive_topics": [
                "income claims",
                "AI replacement claims",
                "student outcomes",
            ],
        },
        token,
    )
    ai_provider_test = configure_local_llm(base, token, organization_id)

    sources = [
        add_source(base, token, organization_id, "Quainy core context and voice", QUAINY_CORE_SOURCE),
        add_source(base, token, organization_id, "Quainy Labs public proof", LABS_SOURCE),
        add_source(base, token, organization_id, "Quainy public communication rules", CONTENT_RULES_SOURCE),
        add_source(base, token, organization_id, "Quainy active products and website", QUAINY_PRODUCTS_SOURCE),
        add_source(base, token, organization_id, "Published blog today: Product Judgment in the AI Era", TODAY_BLOG_SOURCE),
        add_source(base, token, organization_id, "Quainy Vouch product source", QUAINY_VOUCH_SOURCE),
    ]
    readiness = request_json(base, "GET", f"/organizations/{organization_id}/knowledge-readiness", token=token)
    opportunities = generate_non_deterministic_opportunities(base, token, organization_id)
    if not opportunities:
        raise RuntimeError("Quainy workspace created, but no opportunities were generated.")
    brief = request_json(base, "POST", f"/opportunities/{opportunities[0]['id']}/briefs", token=token, timeout=120)
    draft = request_json(
        base,
        "POST",
        f"/briefs/{brief['id']}/drafts?platform=linkedin&content_type=company_post",
        token=token,
        timeout=180,
    )["drafts"][0]
    lowered_draft = draft["body"].lower()
    blocked_phrases = [
        "use this file",
        "latest company context",
        "build what matters. needs",
        "approved context",
        "this brief",
        "buil,",
        "who want to,",
        "quainy core context",
        "quainy labs source",
        "quainy vouch product source",
        "quainy active products and website",
        "published blog today:",
        "public communication rules",
        "share a practical point of view",
        "product vouch",
    ]
    if any(phrase in lowered_draft for phrase in blocked_phrases):
        raise RuntimeError(f"Generated LinkedIn draft still contains weak template/source leakage: {draft['body']}")
    if "vouch" in opportunities[0]["title"].lower() and "vouch" not in lowered_draft:
        raise RuntimeError(f"Top opportunity is about Vouch, but the draft lost Vouch context: {draft['body']}")
    if "launch" in opportunities[0]["reason_today"].lower() and "vouch" in opportunities[0]["title"].lower():
        raise RuntimeError(f"Top Vouch opportunity has unsupported launch framing: {opportunities[0]['reason_today']}")
    if "launch" in opportunities[0]["title"].lower() and "vouch" in opportunities[0]["title"].lower():
        raise RuntimeError(f"Top Vouch opportunity has unsupported launch title: {opportunities[0]['title']}")
    unsupported_reason_terms = ["new milestone", "recently reached", "impact it's having", "impact it is having"]
    if any(term in opportunities[0]["reason_today"].lower() for term in unsupported_reason_terms):
        raise RuntimeError(f"Top opportunity has unsupported timing/proof framing: {opportunities[0]['reason_today']}")
    if "http" in opportunities[0]["reason_today"].lower() or "fresh off the press" in opportunities[0]["reason_today"].lower():
        raise RuntimeError(f"Top opportunity has invented URL or hype timing: {opportunities[0]['reason_today']}")
    if "<" in opportunities[0]["reason_today"] or ">" in opportunities[0]["reason_today"]:
        raise RuntimeError(f"Top opportunity has HTML in rationale: {opportunities[0]['reason_today']}")
    if opportunities[0]["reason_today"].strip() == "2026-07-11":
        raise RuntimeError("Top opportunity reason_today is only a date.")
    top_title = opportunities[0]["title"].lower()
    if not any(term in top_title for term in ["vouch", "product judgment", "blog"]):
        raise RuntimeError(f"Top opportunity is not focused on Vouch or today's blog: {opportunities[0]['title']}")

    print(json.dumps({
        "email": email,
        "password": password,
        "organization_id": organization_id,
        "source_titles": [source["title"] for source in sources],
        "ai_provider": ai_provider_test,
        "knowledge_readiness": {
            "score": readiness["overall_score"],
            "status": readiness["status"],
            "approved_source_count": readiness["approved_source_count"],
            "covered_pillar_count": readiness["covered_pillar_count"],
            "total_pillar_count": readiness["total_pillar_count"],
        },
        "top_opportunities": [
            {
                "title": opportunity["title"],
                "reason_today": opportunity["reason_today"],
                "rank_signals": opportunity["metadata"].get("rank_signals", {}),
            }
            for opportunity in opportunities[:5]
        ],
        "brief_key_message": brief["key_message"],
        "linkedin_draft_preview": draft["body"],
        "hashtags": draft["hashtags"],
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
