import { useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { api } from "../lib/api";
import type { Draft, ReviewerPackage } from "../types";

type UseReviewerPackageOptions = {
  selectedDraft: Draft | null;
  onBodyLoaded: Dispatch<SetStateAction<string>>;
  onReasonReset: Dispatch<SetStateAction<string>>;
};

export function useReviewerPackage({ selectedDraft, onBodyLoaded, onReasonReset }: UseReviewerPackageOptions) {
  const [reviewPackage, setReviewPackage] = useState<ReviewerPackage | null>(null);

  useEffect(() => {
    if (!selectedDraft) {
      setReviewPackage(null);
      return;
    }
    api<ReviewerPackage>(`/drafts/${selectedDraft.id}/reviewer-package`).then((pkg) => {
      setReviewPackage(pkg);
      onBodyLoaded(pkg.draft.body);
      onReasonReset("");
    });
  }, [onBodyLoaded, onReasonReset, selectedDraft]);

  return { reviewPackage, setReviewPackage };
}
