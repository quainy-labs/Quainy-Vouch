import { Plus } from "lucide-react";
import type { KnowledgeReadiness, SourceDetail, SourceForm } from "../../types";
import { ErrorList } from "../ui/ErrorList";
import { KnowledgeReadinessPanel } from "./KnowledgeReadinessPanel";
import { SourceDetailPanel } from "./SourceDetailPanel";
import { SourceFormPanel } from "./SourceFormPanel";
import { readinessCopy, readinessPriorityLabel, sourceGuideCards, sourceTypeText } from "./sourceConfig";

type SourcesViewProps = {
  busy: boolean;
  canEditKnowledge: boolean;
  permissionMessage: string;
  sourceErrors: string[];
  readiness: KnowledgeReadiness | null;
  approvedCount: number;
  disabledCount: number;
  archivedCount: number;
  totalSourceCount: number;
  sourceForm: SourceForm;
  sourceDetail: SourceDetail | null;
  onAddSource: () => void | Promise<void>;
  onReadinessAction: (action: string) => void | Promise<void>;
  onSelectSourceType: (sourceType: string) => void;
  onCommitSourceForm: (form: SourceForm) => void;
  onSourceFile: (file: File | undefined) => void | Promise<void>;
  onUpdateSourceStatus: (sourceId: string, approvalStatus: string) => void | Promise<void>;
  onRefreshSource: (sourceId: string) => void | Promise<void>;
  formatAuditTime: (value: string) => string;
};

export function SourcesView({
  busy,
  canEditKnowledge,
  permissionMessage,
  sourceErrors,
  readiness,
  approvedCount,
  disabledCount,
  archivedCount,
  totalSourceCount,
  sourceForm,
  sourceDetail,
  onAddSource,
  onReadinessAction,
  onSelectSourceType,
  onCommitSourceForm,
  onSourceFile,
  onUpdateSourceStatus,
  onRefreshSource,
  formatAuditTime,
}: SourcesViewProps) {
  const sourceCopy = sourceTypeText[sourceForm.source_type] ?? sourceTypeText.manual_note;

  return (
    <section className="panel band source-library-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Source Library</p>
          <h2>Approved company knowledge</h2>
        </div>
        <button
          className="icon-button primary"
          onClick={() => void onAddSource()}
          disabled={busy || !canEditKnowledge}
          title={canEditKnowledge ? "Add source" : permissionMessage}
        >
          <Plus size={18} />
          <span>Add source</span>
        </button>
      </div>
      <ErrorList errors={sourceErrors} />
      {readiness && (
        <KnowledgeReadinessPanel
          readiness={readiness}
          copy={readinessCopy}
          priorityLabels={readinessPriorityLabel}
          onAction={onReadinessAction}
        />
      )}
      <div className="source-health-grid">
        <article className={`source-health-tile ${approvedCount > 0 ? "healthy" : "blocked"}`}>
          <span>Approved</span>
          <strong>{approvedCount}</strong>
          <p>{approvedCount > 0 ? "Available to recommendations and drafts." : "Add approved context to unlock safe generation."}</p>
        </article>
        <article className="source-health-tile">
          <span>Disabled</span>
          <strong>{disabledCount}</strong>
          <p>Not used as active evidence until re-approved.</p>
        </article>
        <article className="source-health-tile">
          <span>Archived</span>
          <strong>{archivedCount}</strong>
          <p>Kept for audit history, not active guidance.</p>
        </article>
        <article className="source-health-tile">
          <span>Library</span>
          <strong>{totalSourceCount}</strong>
          <p>Total source records in this workspace.</p>
        </article>
      </div>
      <div className="source-guide-grid" aria-label="Source onboarding options">
        {sourceGuideCards.map((guide) => (
          <button
            className={sourceForm.source_type === guide.source_type ? "source-guide-card active" : "source-guide-card"}
            key={guide.id}
            onClick={() => onSelectSourceType(guide.source_type)}
            type="button"
          >
            <span>{guide.source_type.replace("_", " ")}</span>
            <strong>{guide.title}</strong>
            <small>{guide.description}</small>
          </button>
        ))}
      </div>
      <div className="source-library-grid">
        <SourceFormPanel
          sourceForm={sourceForm}
          sourceCopy={sourceCopy}
          onCommitSourceForm={onCommitSourceForm}
          onSourceFile={onSourceFile}
        />

        <SourceDetailPanel
          busy={busy}
          canEditKnowledge={canEditKnowledge}
          permissionMessage={permissionMessage}
          sourceDetail={sourceDetail}
          approvedCount={approvedCount}
          disabledCount={disabledCount}
          archivedCount={archivedCount}
          onUpdateSourceStatus={onUpdateSourceStatus}
          onRefreshSource={onRefreshSource}
          formatAuditTime={formatAuditTime}
        />
      </div>
    </section>
  );
}
