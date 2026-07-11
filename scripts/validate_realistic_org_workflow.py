from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app


def assert_quality(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    client = TestClient(app)
    suffix = uuid4().hex[:8]
    org = client.post(
        "/organizations",
        json={
            "name": f"PulseCare Clinics {suffix}",
            "website_url": "https://pulsecare.example",
            "industry": "Healthcare operations",
            "description": (
                "PulseCare helps cardiology clinics run remote patient monitoring programs "
                "with clearer follow-up workflows and patient adherence support."
            ),
            "audience_summary": "Cardiology clinic operators, care coordinators, and healthcare operations leaders",
        },
    ).json()
    org_id = org["id"]
    client.patch(
        f"/organizations/{org_id}/profile",
        json={
            "one_liner": "PulseCare helps cardiology clinics keep remote-monitoring patients on track between visits.",
            "mission": "Make remote patient monitoring easier for clinics to operate and easier for patients to follow.",
            "product_summary": (
                "The platform combines patient check-ins, device reading review queues, escalation rules, "
                "and care-coordinator workflows for cardiology teams."
            ),
            "audience": "cardiology clinic operators, care coordinators, and healthcare operations leaders",
            "voice_rules": ["Practical", "Clinically careful", "Operationally specific"],
            "preferred_phrases": ["between-visit care", "care coordinator workflow", "patient follow-through"],
            "banned_phrases": ["revolutionary", "magic", "guaranteed outcomes"],
            "approved_claims": [
                "PulseCare supports remote patient monitoring workflows for cardiology clinics.",
                "Care coordinators can review patient check-ins and device-reading queues.",
            ],
            "forbidden_claims": ["Do not claim clinical outcomes without cited evidence."],
            "content_pillars": ["remote patient monitoring", "cardiology follow-up", "patient adherence"],
            "sensitive_topics": ["clinical outcomes", "patient privacy"],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org_id}/sources",
        json={
            "source_type": "manual_note",
            "title": "Remote monitoring follow-up playbook",
            "raw_text": (
                "PulseCare supports remote patient monitoring for cardiology clinics. "
                "Care coordinators use patient check-ins, device-reading queues, and escalation rules "
                "to decide which patients need follow-up between visits. "
                "The operating goal is not to replace clinicians; it is to make routine review work visible, "
                "prioritized, and easier to act on. "
                "Patient adherence improves when reminders, check-ins, and follow-up tasks are connected "
                "to one care coordinator workflow. "
            )
            * 5,
            "approval_status": "approved",
            "freshness_days": 120,
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org_id}/sources",
        json={
            "source_type": "manual_note",
            "title": "Care coordinator workflow notes",
            "raw_text": (
                "The PulseCare care coordinator workflow gives clinics a daily review list for remote monitoring. "
                "The list groups check-ins, missing readings, flagged readings, and outreach tasks. "
                "Clinic operators care about consistency: every task should have an owner, a status, and a next step. "
                "Public communication should avoid clinical guarantees and focus on operational clarity, "
                "patient follow-through, and safer review habits. "
            )
            * 5,
            "approval_status": "approved",
            "freshness_days": 120,
        },
    ).raise_for_status()

    opportunities = client.post(f"/organizations/{org_id}/opportunities/generate").json()["opportunities"]
    assert_quality(bool(opportunities), "Expected at least one opportunity from realistic approved context.")
    top = opportunities[0]
    assert_quality("source-backed update" not in top["title"].lower(), "Top opportunity title is still generic.")
    assert_quality(
        any(term in (top["title"] + " " + top["summary"]).lower() for term in ["remote", "cardiology", "patient", "clinic"]),
        "Top opportunity does not reflect the realistic organization context.",
    )
    assert_quality(top["metadata"].get("rank_signals", {}).get("source_support", 0) > 0, "Missing source-support ranking signal.")

    brief = client.post(f"/opportunities/{top['id']}/briefs").json()
    assert_quality(
        any(term in (brief["key_message"] + " " + " ".join(brief["supporting_points"])).lower() for term in ["remote", "cardiology", "patient", "clinic"]),
        "Brief does not preserve realistic organization context.",
    )

    draft = client.post(f"/briefs/{brief['id']}/drafts?platform=linkedin&content_type=company_post").json()["drafts"][0]
    body = draft["body"]
    lowered = body.lower()
    forbidden_generic = [
        "build what matters",
        "publishing more is not",
        "generic ai content",
        "source-backed note:",
        "what the evidence supports:",
        "that is the message behind this brief",
        "builders and small teams",
        "approved context",
        "this brief",
    ]
    assert_quality(not any(phrase in lowered for phrase in forbidden_generic), "LinkedIn draft still contains generic template language.")
    assert_quality(
        any(term in lowered for term in ["remote monitoring", "cardiology", "patient", "clinic", "care coordinator"]),
        "LinkedIn draft does not communicate the realistic organization context.",
    )
    assert_quality(3 <= body.count("\n\n") <= 6, "LinkedIn draft should use short LinkedIn-style paragraphs.")

    print("\n=== Top Opportunity ===")
    print(top["title"])
    print(top["reason_today"])
    print(top["metadata"].get("rank_signals"))
    print("\n=== Brief ===")
    print(brief["key_message"])
    for point in brief["supporting_points"][:2]:
        print(f"- {point}")
    print("\n=== LinkedIn Draft ===")
    print(body)
    print("\nHashtags:", " ".join(draft["hashtags"]))
    print("\nQuality checks:")
    for check in draft["quality_report"]:
        print(f"- {check}")


if __name__ == "__main__":
    main()
