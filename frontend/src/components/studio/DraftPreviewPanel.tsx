import type { Draft, Opportunity, ReviewerPackage } from "../../types";
import { contentTypeDisplayName, draftFormatLabel, platformDisplayName } from "../../lib/forms";

type DraftPreviewPanelProps = {
  draft: Draft;
  selectedOpportunity: Opportunity | null;
  reviewPackage: ReviewerPackage | null;
  previewParagraphs: string[];
  supportedClaimCount: number;
  unsupportedClaimCount: number;
  duplicateMatchCount: number;
};

export function DraftPreviewPanel({
  draft,
  selectedOpportunity,
  reviewPackage,
  previewParagraphs,
  supportedClaimCount,
  unsupportedClaimCount,
  duplicateMatchCount,
}: DraftPreviewPanelProps) {
  const evidencePoints =
    reviewPackage?.source_chunks.slice(0, 3).map((chunk) => {
      const text = chunk.chunk_text.trim().replace(/\s+/g, " ");
      return text.length > 170 ? `${text.slice(0, 170).trim()}...` : text;
    }) ?? [];

  return (
    <section className="panel band preview-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Preview</p>
          <h2>{platformDisplayName(draft.platform)} artifact</h2>
        </div>
        <span className="platform-count">{contentTypeDisplayName(draft.content_type)}</span>
      </div>
      <div className="preview-layout">
        <article className={`platform-preview ${draft.platform}`}>
          <div className="preview-chrome">
            <div>
              <span>{platformDisplayName(draft.platform)}</span>
              <strong>{draft.hook || draftFormatLabel(draft)}</strong>
            </div>
            <small>{draft.status.replace("_", " ")}</small>
          </div>
          <div className="preview-body">
            {previewParagraphs.length > 0 ? (
              previewParagraphs.map((paragraph, index) => <p key={`${draft.id}-paragraph-${index}`}>{paragraph}</p>)
            ) : (
              <p>{draft.body}</p>
            )}
          </div>
        </article>

        <aside className="trust-summary">
          <div className="trust-card evidence-card">
            <span>Evidence</span>
            <strong>{draft.source_ids.length}</strong>
            <small>
              approved source{draft.source_ids.length === 1 ? "" : "s"}
            </small>
          </div>
          <div className={unsupportedClaimCount > 0 ? "trust-card claims-card warning" : "trust-card claims-card"}>
            <span>Claims</span>
            <strong>
              {supportedClaimCount}/{draft.claims.length}
            </strong>
            <small>{unsupportedClaimCount > 0 ? `${unsupportedClaimCount} need review` : "supported or non-factual"}</small>
          </div>
          <div className={draft.risk_report.length > 0 ? "trust-card risk-card warning" : "trust-card risk-card"}>
            <span>Risk</span>
            <strong>{draft.risk_report.length}</strong>
            <small>{draft.risk_report.length === 1 ? "review note" : "review notes"}</small>
          </div>
          <div className={duplicateMatchCount > 0 ? "trust-card memory-card warning" : "trust-card memory-card"}>
            <span>Memory</span>
            <strong>{duplicateMatchCount}</strong>
            <small>
              similar post{duplicateMatchCount === 1 ? "" : "s"}
            </small>
          </div>
          {selectedOpportunity && (
            <div className="trust-explain">
              <span>Why today</span>
              <p>{selectedOpportunity.reason_today}</p>
            </div>
          )}
          <div className={draft.risk_report.length > 0 ? "trust-detail-list risk-detail warning" : "trust-detail-list risk-detail"}>
            <span>Risks</span>
            {draft.risk_report.length > 0 ? (
              draft.risk_report.map((risk) => <p key={risk}>{risk}</p>)
            ) : (
              <p>No risk notes.</p>
            )}
          </div>
          <div className={unsupportedClaimCount > 0 ? "trust-detail-list claims-detail warning" : "trust-detail-list claims-detail"}>
            <span>Claims</span>
            {draft.claims.map((claim) => (
              <div className="preview-claim-row" key={claim.text}>
                <span className={`dot ${claim.support_status}`} />
                <p>{claim.text}</p>
              </div>
            ))}
          </div>
          {draft.duplicate_report.similar_posts.length > 0 && (
            <div className="trust-detail-list memory-detail warning">
              <span>Similar memory</span>
              {draft.duplicate_report.similar_posts.map((post) => (
                <div className="preview-memory-row" key={post.excerpt}>
                  <strong>{Math.round(post.score * 100)}% similar</strong>
                  <p>{post.excerpt}</p>
                </div>
              ))}
            </div>
          )}
          {evidencePoints.length ? (
            <div className="trust-evidence evidence-detail">
              <span>Evidence points</span>
              {evidencePoints.map((point, index) => (
                <p key={`${draft.id}-evidence-${index}`}>{point}</p>
              ))}
            </div>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
