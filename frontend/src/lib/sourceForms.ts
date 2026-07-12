import type { SourceForm } from "../types";
import { emptySourceFormFor } from "./forms";

export async function sourceFormFromFile(file: File, currentForm: SourceForm): Promise<SourceForm> {
  const rawText = await file.text();
  const lowerName = file.name.toLowerCase();
  const sourceType = lowerName.endsWith(".md") || lowerName.endsWith(".markdown") ? "markdown" : "text";
  const title = file.name.replace(/\.[^/.]+$/, "");

  return {
    ...emptySourceFormFor(sourceType),
    approval_status: currentForm.approval_status,
    freshness_days: currentForm.freshness_days,
    source_type: sourceType,
    title,
    uri: file.name,
    raw_text: rawText,
  };
}
