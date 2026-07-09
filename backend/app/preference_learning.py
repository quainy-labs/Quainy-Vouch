from __future__ import annotations

import re
from collections import Counter

from app.schemas import ApprovalDecision, Decision, PreferenceSuggestion, PreferenceSuggestionKind, now_utc


def _terms(text: str) -> list[str]:
    return [
        term
        for term in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{3,}", text.lower())
        if term not in {"draft", "content", "needs", "more", "less", "with", "from", "this", "that", "should"}
    ]


class PreferenceLearningEngine:
    def build_suggestions(self, organization_id: str, decisions: list[ApprovalDecision]) -> list[PreferenceSuggestion]:
        suggestions: list[PreferenceSuggestion] = []
        edit_phrases = self._repeated_edit_phrases(decisions)
        rejected_terms = self._rejected_terms(decisions)

        if edit_phrases:
            suggestions.append(
                PreferenceSuggestion(
                    organization_id=organization_id,
                    kind=PreferenceSuggestionKind.voice_phrase,
                    title="Add repeated edited phrasing to preferred phrases",
                    rationale="Reviewers repeatedly edited drafts toward this wording.",
                    proposed_update={"preferred_phrases_add": edit_phrases},
                    evidence=edit_phrases,
                    confidence=min(0.9, 0.55 + len(edit_phrases) * 0.1),
                    created_at=now_utc(),
                )
            )

        if rejected_terms:
            suggestions.append(
                PreferenceSuggestion(
                    organization_id=organization_id,
                    kind=PreferenceSuggestionKind.rejected_pattern,
                    title="Track repeated rejection patterns",
                    rationale="Reviewers repeatedly rejected drafts for these themes.",
                    proposed_update={"banned_phrases_add": rejected_terms},
                    evidence=rejected_terms,
                    confidence=min(0.88, 0.5 + len(rejected_terms) * 0.08),
                    created_at=now_utc(),
                )
            )

        return suggestions

    def _repeated_edit_phrases(self, decisions: list[ApprovalDecision]) -> list[str]:
        phrases: Counter[str] = Counter()
        for decision in decisions:
            if not decision.edited_body:
                continue
            for phrase in re.findall(r"\b(?:approved context|source-backed|human review|product judgment|careful updates|reviewer judgment)\b", decision.edited_body.lower()):
                phrases[phrase] += 1
        return [phrase for phrase, count in phrases.most_common(5) if count >= 2]

    def _rejected_terms(self, decisions: list[ApprovalDecision]) -> list[str]:
        terms = Counter()
        for decision in decisions:
            if decision.decision != Decision.reject or not decision.reason:
                continue
            terms.update(_terms(decision.reason))
        return [term for term, count in terms.most_common(5) if count >= 2]
