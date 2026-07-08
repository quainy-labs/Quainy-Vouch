from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Quainy Vouch deterministic MVP evaluation.")
    parser.add_argument("--fixtures", default=str(ROOT / "docs/evaluation/golden_cases.json"))
    parser.add_argument("--output", default=str(ROOT / "docs/evaluation/reports/latest.json"))
    args = parser.parse_args()

    fixture_path = Path(args.fixtures)
    cases = json.loads(fixture_path.read_text())
    client = TestClient(app)
    results = [run_case(client, case) for case in cases]
    passed = sum(1 for result in results if result["passed"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixtures": str(fixture_path.relative_to(ROOT)),
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": round(passed / max(len(results), 1), 3),
        },
        "results": results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
    return 0 if report["summary"]["failed"] == 0 else 1


def run_case(client: TestClient, case: dict[str, Any]) -> dict[str, Any]:
    kind = case["kind"]
    if kind == "source_backed_flow":
        return evaluate_source_backed_flow(client, case)
    if kind == "unsupported_metric_block":
        return evaluate_unsupported_metric_block(client, case)
    if kind == "duplicate_memory":
        return evaluate_duplicate_memory(client, case)
    return result(case, False, {"error": f"Unknown eval kind: {kind}"})


def evaluate_source_backed_flow(client: TestClient, case: dict[str, Any]) -> dict[str, Any]:
    bootstrap = client.get("/bootstrap").json()
    org_id = bootstrap["organization"]["id"]
    opportunity = client.post(f"/organizations/{org_id}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    drafts = client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"]
    first = drafts[0]
    checks = {
        "draft_count": len(drafts),
        "source_ids": first["source_ids"],
        "generation_metadata": first["generation_metadata"],
        "claim_count": len(first["claims"]),
    }
    expected = case["expected"]
    passed = (
        checks["draft_count"] >= expected["minimum_drafts"]
        and (not expected["requires_sources"] or bool(checks["source_ids"]))
        and (not expected["requires_generation_metadata"] or bool(checks["generation_metadata"]))
        and checks["claim_count"] > 0
    )
    return result(case, passed, checks)


def evaluate_unsupported_metric_block(client: TestClient, case: dict[str, Any]) -> dict[str, Any]:
    draft = create_reviewable_draft(client, "Eval Unsupported Metric Org", "unsupported metric checks")
    edited = client.patch(
        f"/drafts/{draft['id']}",
        json={"body": "The company is the fastest market leader with 45% revenue growth."},
    ).json()
    approval = client.post(f"/drafts/{draft['id']}/approve", json={})
    checks = {
        "approval_status": approval.status_code,
        "risk_report": edited["risk_report"],
        "unsupported_claims": [claim["text"] for claim in edited["claims"] if claim["support_status"] == "unsupported"],
    }
    expected = case["expected"]
    passed = (
        checks["approval_status"] == expected["approval_status"]
        and any(expected["risk_contains"] in risk for risk in checks["risk_report"])
        and bool(checks["unsupported_claims"])
    )
    return result(case, passed, checks)


def evaluate_duplicate_memory(client: TestClient, case: dict[str, Any]) -> dict[str, Any]:
    draft = create_reviewable_draft(client, "Eval Duplicate Org", "duplicate memory")
    client.post(f"/drafts/{draft['id']}/approve", json={}).raise_for_status()
    regenerated = client.post(f"/briefs/{draft['content_brief_id']}/drafts").json()["drafts"][0]
    duplicate_report = regenerated["duplicate_report"]
    checks = {
        "duplicate_score": duplicate_report["duplicate_score"],
        "similar_posts": duplicate_report["similar_posts"],
    }
    expected = case["expected"]
    passed = (
        checks["duplicate_score"] >= expected["minimum_duplicate_score"]
        and len(checks["similar_posts"]) >= expected["minimum_similar_posts"]
    )
    return result(case, passed, checks)


def create_reviewable_draft(client: TestClient, org_name: str, pillar: str) -> dict[str, Any]:
    org = client.post("/organizations", json={"name": org_name}).json()
    client.patch(
        f"/organizations/{org['id']}/profile",
        json={
            "one_liner": "Turns approved context into reviewable public communication.",
            "preferred_phrases": ["approved context"],
            "content_pillars": [pillar],
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org['id']}/sources",
        json={
            "source_type": "text",
            "title": f"{pillar.title()} source",
            "raw_text": (
                f"Approved context supports {pillar} with reviewer visibility, source evidence, "
                "and human approval before public export. "
            )
            * 5,
            "approval_status": "approved",
        },
    ).raise_for_status()
    opportunity = client.post(f"/organizations/{org['id']}/opportunities/generate").json()["opportunities"][0]
    brief = client.post(f"/opportunities/{opportunity['id']}/briefs").json()
    return client.post(f"/briefs/{brief['id']}/drafts").json()["drafts"][0]


def result(case: dict[str, Any], passed: bool, checks: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["id"],
        "description": case["description"],
        "kind": case["kind"],
        "passed": passed,
        "checks": checks,
    }


if __name__ == "__main__":
    raise SystemExit(main())
