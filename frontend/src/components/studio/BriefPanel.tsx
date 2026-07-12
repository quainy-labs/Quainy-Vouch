import { FileCheck2 } from "lucide-react";
import type { ContentBrief, FormatChoice } from "../../types";

type BriefPanelProps = {
  brief: ContentBrief;
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
          <h2>Source brief for {selectedFormatLabel}</h2>
        </div>
        <div className="format-actions">
          <select value={formatChoice} onChange={(event) => onSelectContentFormat(event.target.value as FormatChoice)}>
            <option value="linkedin_company_post">LinkedIn post</option>
            <option value="blog_outline">Blog outline</option>
            <option value="newsletter_email">Newsletter email</option>
            <option value="instagram_caption">Instagram caption</option>
            <option value="instagram_carousel_outline">Instagram carousel</option>
          </select>
          <button
            className="icon-button primary"
            onClick={() => void onGenerateDrafts()}
            disabled={busy || !canEditContent}
            title={canEditContent ? "Generate drafts" : permissionMessage}
          >
            <FileCheck2 size={18} />
            <span>Generate drafts</span>
          </button>
        </div>
      </div>
      <div className="brief-grid">
        <section className="brief-summary">
          <span>Selected format</span>
          <p>{selectedFormatLabel}</p>
          <span>Objective</span>
          <p>{brief.objective}</p>
          <span>Audience</span>
          <p>{brief.audience}</p>
          <span>Key message</span>
          <p>{brief.key_message}</p>
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
