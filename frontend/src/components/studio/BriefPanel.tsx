import { FileCheck2 } from "lucide-react";
import type { ContentBrief, FormatChoice, Opportunity } from "../../types";

type BriefPanelProps = {
  brief: ContentBrief;
  opportunity: Opportunity | null;
  opportunityLabel: string;
  selectedFormatLabel: string;
  formatChoice: FormatChoice;
  busy: boolean;
  canEditContent: boolean;
  permissionMessage: string;
  onSelectContentFormat: (choice: FormatChoice) => void;
  onGenerateDrafts: () => void | Promise<void>;
};

export function BriefPanel({
  brief,
  opportunity,
  opportunityLabel,
  selectedFormatLabel,
  formatChoice,
  busy,
  canEditContent,
  permissionMessage,
  onSelectContentFormat,
  onGenerateDrafts,
}: BriefPanelProps) {
  return (
    <section className="panel band brief-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Brief</p>
          <h2>{opportunity?.title ?? "Brief exists for this opportunity"}</h2>
          <p className="empty-results">Review the source-backed message, choose a format, then generate draft variants.</p>
        </div>
        <div className="format-actions">
          <select value={formatChoice} onChange={(event) => onSelectContentFormat(event.target.value as FormatChoice)}>
            <option value="linkedin_post">LinkedIn post</option>
            <option value="reddit_post">Reddit post</option>
            <option value="instagram_post">Instagram post</option>
          </select>
          <button
            className="icon-button primary"
            onClick={() => void onGenerateDrafts()}
            disabled={busy || !canEditContent}
            title={canEditContent ? "Generate drafts" : permissionMessage}
          >
            <FileCheck2 size={18} />
            <span>{busy ? "Generating..." : "Generate drafts"}</span>
          </button>
        </div>
      </div>
      {busy && (
        <div className="work-status" role="status">
          <strong>Generating drafts</strong>
          <span>Creating variants from the current source-backed brief.</span>
        </div>
      )}
      <div className="brief-grid">
        <section className="brief-summary">
          <div>
            <span>Opportunity ID</span>
            <p>{opportunityLabel}</p>
          </div>
          <div>
            <span>Selected format</span>
            <p>{selectedFormatLabel}</p>
          </div>
          <div>
            <span>Objective</span>
            <p>{brief.objective}</p>
          </div>
          <div>
            <span>Audience</span>
            <p>{brief.audience}</p>
          </div>
          <div>
            <span>Key message</span>
            <p>{brief.key_message}</p>
          </div>
        </section>
        <section className="brief-list">
          <h3>Supporting points</h3>
          <ul className="plain-list">
            {brief.supporting_points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </section>
        <section className="brief-list">
          <h3>Guardrails</h3>
          <ul className="plain-list">
            {[...brief.do_not_say, ...brief.risks].map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}
