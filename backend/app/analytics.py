from __future__ import annotations

from app.schemas import PerformanceMetricsCreate, PostMemory


def performance_score(snapshot: dict[str, object]) -> float:
    metrics = snapshot.get("metrics", {})
    if not isinstance(metrics, dict):
        return 0.0
    impressions = max(int(metrics.get("impressions", 0) or 0), 1)
    engagement = sum(
        int(metrics.get(key, 0) or 0)
        for key in ["reactions", "comments", "shares", "clicks"]
    )
    return round(min(1.0, engagement / impressions * 10), 3)


def build_performance_snapshot(payload: PerformanceMetricsCreate) -> dict[str, object]:
    metrics = {
        "impressions": payload.impressions,
        "reactions": payload.reactions,
        "comments": payload.comments,
        "shares": payload.shares,
        "clicks": payload.clicks,
    }
    snapshot = {
        "source": payload.source,
        "captured_at": payload.captured_at.isoformat(),
        "metrics": metrics,
        "notes": payload.notes,
    }
    snapshot["performance_score"] = performance_score(snapshot)
    return snapshot


class LocalAnalyticsImportProvider:
    provider_name = "linkedin-analytics-local"

    def import_snapshot(self, memory: PostMemory) -> dict[str, object]:
        seed = len(memory.final_body) + len(memory.idea_fingerprint)
        metrics = {
            "impressions": 100 + seed % 900,
            "reactions": 8 + seed % 45,
            "comments": 1 + seed % 12,
            "shares": seed % 9,
            "clicks": 4 + seed % 30,
        }
        snapshot = {
            "source": self.provider_name,
            "captured_at": memory.published_at.isoformat() if memory.published_at else None,
            "metrics": metrics,
            "notes": "Local deterministic analytics import for workflow validation.",
        }
        snapshot["performance_score"] = performance_score(snapshot)
        return snapshot
