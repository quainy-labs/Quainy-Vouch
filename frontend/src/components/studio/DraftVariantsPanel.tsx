import { Sparkles } from "lucide-react";
import type { Draft } from "../../types";
import { draftFormatLabel } from "../../lib/forms";

type DraftVariantsPanelProps = {
  drafts: Draft[];
  selectedDraft: Draft | null;
  selectedDraftMatchesFormat: boolean;
  onSelectDraft: (draft: Draft) => void;
};

export function DraftVariantsPanel({ drafts, selectedDraft, selectedDraftMatchesFormat, onSelectDraft }: DraftVariantsPanelProps) {
  return (
    <section className="panel band">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Drafts</p>
          <h2>{draftFormatLabel(selectedDraft)}</h2>
        </div>
        <Sparkles size={20} />
      </div>
      <div className="draft-tabs">
        {drafts.map((draft, index) => (
          <button key={draft.id} className={selectedDraft?.id === draft.id ? "active" : ""} onClick={() => onSelectDraft(draft)}>
            Variant {index + 1}
          </button>
        ))}
      </div>
      {selectedDraft && (
        <div className="draft-meta-row">
          <span>{String(selectedDraft.generation_metadata.adapter_name ?? selectedDraft.platform ?? "adapter")}</span>
          <span>{String(selectedDraft.generation_metadata.prompt_version ?? "prompt tracked")}</span>
          <span>
            {selectedDraft.source_ids.length} source{selectedDraft.source_ids.length === 1 ? "" : "s"}
          </span>
          <span>{selectedDraftMatchesFormat ? "Matches selected format" : "Different from selected format"}</span>
          <span>
            {Object.keys(selectedDraft.source_map).length} source map candidate{Object.keys(selectedDraft.source_map).length === 1 ? "" : "s"}
          </span>
          {selectedDraft.published_at && <span>Published {new Date(selectedDraft.published_at).toLocaleString()}</span>}
          {selectedDraft.publish_result?.status === "failed" && <span>Publish failed</span>}
        </div>
      )}
    </section>
  );
}
