import { Plus, RefreshCcw, Sparkles } from "lucide-react";
import type { Opportunity, Source } from "../../types";
import { opportunityWarnings, summarizeNames } from "../../lib/forms";

type OpportunitiesPanelProps = {
  busy: boolean;
  canEditContent: boolean;
  permissionMessage: string;
  approvedSources: Source[];
  rankedOpportunities: Opportunity[];
  visibleOpportunities: Opportunity[];
  hiddenOpportunityCount: number;
  selectedOpportunity: Opportunity | null;
  opportunityMessage: string;
  opportunityCount: number;
  onGenerate: () => void | Promise<void>;
  onCreateBrief: (opportunity: Opportunity) => void | Promise<void>;
  onShowMore: () => void;
};

export function OpportunitiesPanel({
  busy,
  canEditContent,
  permissionMessage,
  approvedSources,
  rankedOpportunities,
  visibleOpportunities,
  hiddenOpportunityCount,
  selectedOpportunity,
  opportunityMessage,
  opportunityCount,
  onGenerate,
  onCreateBrief,
  onShowMore,
}: OpportunitiesPanelProps) {
  const sourceTitleById = new Map(approvedSources.map((source) => [source.id, source.title]));
  const activeSourceSummary = summarizeNames(approvedSources.map((source) => source.title), 3);
  const sampleSourceActive = approvedSources.some((source) => source.uri?.startsWith("sample://"));

  return (
    <section className="panel band">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Opportunities</p>
          <h2>Source-backed angles</h2>
        </div>
        <button
          className="icon-button primary"
          onClick={() => void onGenerate()}
          disabled={busy || !canEditContent}
          title={canEditContent ? "Generate opportunities" : permissionMessage}
        >
          <RefreshCcw size={18} />
          <span>{busy ? "Generating..." : "Generate"}</span>
        </button>
      </div>
      {busy && (
        <div className="work-status" role="status">
          <strong>Working on Studio request</strong>
          <span>Generating opportunities or creating a brief from approved company context.</span>
        </div>
      )}
      {rankedOpportunities.length > 0 && (
        <div className="opportunity-rank-bar">
          <div>
            <span>{visibleOpportunities.length} shown</span>
            <strong>
              {rankedOpportunities.length} ranked source-backed angle{rankedOpportunities.length === 1 ? "" : "s"}
            </strong>
          </div>
          <p>Sorted by relevance, confidence, freshness, source coverage, and latest source activity.</p>
        </div>
      )}
      <div className={`studio-source-strip ${approvedSources.length > 0 ? "ready" : "blocked"}`}>
        <div>
          <span>
            {approvedSources.length} active source{approvedSources.length === 1 ? "" : "s"}
          </span>
          <strong>{activeSourceSummary || "No approved knowledge available"}</strong>
          {sampleSourceActive && (
            <p>Sample context is still active. Disable it in Sources when you want recommendations to come only from your own company knowledge.</p>
          )}
        </div>
        <small>Draft format is selected after a brief is created.</small>
      </div>
      <div className="opportunity-grid">
        {visibleOpportunities.length > 0 ? (
          visibleOpportunities.map((opportunity, index) => (
            <article
              className={`opportunity-card ${selectedOpportunity?.id === opportunity.id ? "selected" : ""} ${
                opportunity.status === "warned" ? "warned" : ""
              }`}
              key={opportunity.id}
            >
              <h3>{opportunity.title}</h3>
              <div className="opportunity-scores" aria-label={`Opportunity ${index + 1} ranking signals`}>
                <span>Opportunity #{index + 1}</span>
                <span className="score">{Math.round(opportunity.relevance_score * 100)}% relevant</span>
                <span>{Math.round(opportunity.confidence_score * 100)}% confidence</span>
                <span>
                  {opportunity.source_ids.length} source{opportunity.source_ids.length === 1 ? "" : "s"}
                </span>
                {opportunity.status === "warned" && <span className="warning-badge">Needs context</span>}
              </div>
              <p className="opportunity-description">{opportunity.reason_today}</p>
              <small className="opportunity-evidence">
                Source support: {opportunity.source_ids.map((sourceId) => sourceTitleById.get(sourceId) ?? sourceId).join(", ") || "No approved source"}
              </small>
              <div className="opportunity-card-actions">
                <button
                  className="icon-button primary"
                  onClick={() => void onCreateBrief(opportunity)}
                  disabled={busy || !canEditContent}
                  type="button"
                  title={canEditContent ? "Create brief from this angle" : permissionMessage}
                >
                  <Plus size={16} />
                  <span>Create brief</span>
                </button>
                <button className="icon-button" disabled title="Opportunity feedback is not connected yet" type="button">
                  Not relevant
                </button>
              </div>
              {opportunityWarnings(opportunity).length > 0 && (
                <ul className="warning-list">
                  {opportunityWarnings(opportunity).map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </article>
          ))
        ) : (
          <div className="empty-opportunities">
            <Sparkles size={22} />
            <p>{opportunityMessage || "Generate opportunities after adding enough approved source context."}</p>
          </div>
        )}
      </div>
      {hiddenOpportunityCount > 0 && (
        <div className="opportunity-load-row">
          <span>
            {hiddenOpportunityCount} lower-ranked angle{hiddenOpportunityCount === 1 ? "" : "s"} available
          </span>
          <button className="icon-button" onClick={onShowMore} type="button" title="Show more source-backed angles">
            <Plus size={18} />
            <span>Show more</span>
          </button>
        </div>
      )}
      {opportunityMessage && opportunityCount > 0 && <p className="notice">{opportunityMessage}</p>}
    </section>
  );
}
