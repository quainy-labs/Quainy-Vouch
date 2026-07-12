import { FileText, Plus, Save, ShieldCheck } from "lucide-react";
import { useState } from "react";
import type { KnowledgeReadiness, Source, SourceDetail, SourceForm } from "../../types";
import { validateHttpUrl, validateSourceForm } from "../../lib/forms";
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
  sources: Source[];
  selectedSourceId: string | null;
  sourceForm: SourceForm;
  sourceDetail: SourceDetail | null;
  onAddSource: () => void | Promise<void>;
  onReadinessAction: (action: string) => void | Promise<void>;
  onSelectSourceType: (sourceType: string) => void;
  onSelectSource: (sourceId: string | null) => void;
  onCommitSourceForm: (form: SourceForm) => void;
  onSourceFile: (file: File | undefined) => void | Promise<void>;
  onUpdateSourceStatus: (sourceId: string, approvalStatus: string) => void | Promise<void>;
  onUpdateSource: (
    sourceId: string,
    payload: { title?: string; uri?: string | null; raw_text?: string; approval_status?: string; freshness_days?: number },
  ) => void | Promise<void>;
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
  sources,
  selectedSourceId,
  sourceForm,
  sourceDetail,
  onAddSource,
  onReadinessAction,
  onSelectSourceType,
  onSelectSource,
  onCommitSourceForm,
  onSourceFile,
  onUpdateSourceStatus,
  onUpdateSource,
  onRefreshSource,
  formatAuditTime,
}: SourcesViewProps) {
  const [activePanel, setActivePanel] = useState<"overview" | "library" | "add" | "coverage">("overview");
  const [touchedFields, setTouchedFields] = useState<Partial<Record<"title" | "uri" | "raw_text" | "freshness_days", boolean>>>({});
  const sourceCopy = sourceTypeText[sourceForm.source_type] ?? sourceTypeText.manual_note;
  const sourceValidationErrors = validateSourceForm(sourceForm);
  const sourceCanSave = sourceValidationErrors.length === 0;
  const sortedSources = [...sources].sort((left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at));
  const latestSources = sortedSources.slice(0, 6);
  const fieldErrors = activePanel === "add" ? visibleSourceFieldErrors(sourceForm, touchedFields, sourceErrors.length > 0) : {};

  function openSource(sourceId: string) {
    onSelectSource(sourceId);
    setActivePanel("library");
  }

  return (
    <section className="panel band source-library-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Source Library</p>
          <h2>Browse approved company knowledge</h2>
        </div>
      </div>

      <div className="section-workspace">
        <aside className="section-sidebar" aria-label="Source sections">
          <button className={activePanel === "overview" ? "active" : ""} onClick={() => setActivePanel("overview")} type="button">
            <ShieldCheck size={16} />
            <span>Overview</span>
            <small>{approvedCount} approved</small>
          </button>
          <button className={activePanel === "library" ? "active" : ""} onClick={() => setActivePanel("library")} type="button">
            <FileText size={16} />
            <span>Sources</span>
            <small>{totalSourceCount} total</small>
          </button>
          <button className={activePanel === "add" ? "active" : ""} onClick={() => setActivePanel("add")} type="button">
            <Plus size={16} />
            <span>Add source</span>
            <small>Explicit create</small>
          </button>
          <button className={activePanel === "coverage" ? "active" : ""} onClick={() => setActivePanel("coverage")} type="button">
            <ShieldCheck size={16} />
            <span>Coverage</span>
            <small>Guidance</small>
          </button>
        </aside>

        <div className="section-content">
          {activePanel === "overview" && (
            <>
              <div className="source-health-grid">
                <article className={`source-health-tile ${approvedCount > 0 ? "healthy" : "blocked"}`}>
                  <span>Approved</span>
                  <strong>{approvedCount}</strong>
                  <p>{approvedCount > 0 ? "Available to recommendations and drafts." : "Add approved context to unlock source-backed generation."}</p>
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
              <section className="source-overview-list">
                <div className="panel-title">
                  <FileText size={17} />
                  <h2>Latest sources</h2>
                </div>
                {latestSources.length > 0 ? (
                  <div className="source-list-table">
                    {latestSources.map((source) => (
                      <button className="source-list-item" key={source.id} onClick={() => openSource(source.id)} type="button">
                        <div>
                          <strong>{source.title}</strong>
                          <span>{source.source_type.replace("_", " ")}</span>
                        </div>
                        <span className={`status-pill ${source.approval_status}`}>{source.approval_status}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="empty-detail">
                    <FileText size={24} />
                    <strong>No sources yet</strong>
                    <p>Add a source only when you have approved company context ready to use as evidence.</p>
                  </div>
                )}
              </section>
            </>
          )}

          {activePanel === "library" && (
            <div className="source-library-grid browse-mode">
              <section className="source-browser">
                <div className="panel-title">
                  <FileText size={17} />
                  <h2>All sources</h2>
                </div>
                <div className="source-list-table">
                  {sortedSources.map((source) => (
                    <button
                      className={`source-list-item ${selectedSourceId === source.id ? "active" : ""}`}
                      key={source.id}
                      onClick={() => openSource(source.id)}
                      type="button"
                    >
                      <div>
                        <strong>{source.title}</strong>
                        <span>{source.source_type.replace("_", " ")} / refresh every {source.freshness_days} days</span>
                      </div>
                      <span className={`status-pill ${source.approval_status}`}>{source.approval_status}</span>
                    </button>
                  ))}
                  {sortedSources.length === 0 && <p className="empty-results">No sources have been added yet.</p>}
                </div>
              </section>

              <SourceDetailPanel
                busy={busy}
                canEditKnowledge={canEditKnowledge}
                permissionMessage={permissionMessage}
                sourceDetail={sourceDetail}
                selectedSourceId={selectedSourceId}
                approvedCount={approvedCount}
                disabledCount={disabledCount}
                archivedCount={archivedCount}
                onUpdateSourceStatus={onUpdateSourceStatus}
                onUpdateSource={onUpdateSource}
                onRefreshSource={onRefreshSource}
                formatAuditTime={formatAuditTime}
              />
            </div>
          )}

          {activePanel === "add" && (
            <section className="source-create-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Create source</p>
                  <h2>{sourceCopy.heading}</h2>
                  <p className="empty-results">{sourceCopy.helper}</p>
                </div>
                <button
                  className="icon-button primary"
                  onClick={() => void onAddSource()}
                  disabled={busy || !canEditKnowledge || !sourceCanSave}
                  title={!canEditKnowledge ? permissionMessage : sourceCanSave ? "Save and ingest this source" : "Complete the required fields before saving"}
                  type="button"
                >
                  <Save size={18} />
                  <span>{busy ? "Saving..." : "Save source"}</span>
                </button>
              </div>
              {busy && (
                <div className="work-status" role="status">
                  <strong>Saving source</strong>
                  <span>Ingesting approved context and refreshing source-backed surfaces.</span>
                </div>
              )}
              <div className="source-guide-grid" aria-label="Source creation options">
                {sourceGuideCards.map((guide) => (
                  <button
                    className={sourceForm.source_type === guide.source_type ? "source-guide-card active" : "source-guide-card"}
                    key={guide.id}
                    onClick={() => {
                      setTouchedFields({});
                      onSelectSourceType(guide.source_type);
                    }}
                    type="button"
                  >
                    <span>{guide.source_type.replace("_", " ")}</span>
                    <strong>{guide.title}</strong>
                    <small>{guide.description}</small>
                  </button>
                ))}
              </div>
              <SourceFormPanel
                sourceForm={sourceForm}
                sourceCopy={sourceCopy}
                fieldErrors={fieldErrors}
                onFieldTouched={(field) => setTouchedFields((current) => ({ ...current, [field]: true }))}
                onCommitSourceForm={onCommitSourceForm}
                onSourceFile={onSourceFile}
              />
            </section>
          )}

          {activePanel === "coverage" && readiness && (
            <KnowledgeReadinessPanel
              readiness={readiness}
              copy={readinessCopy}
              priorityLabels={readinessPriorityLabel}
              onAction={onReadinessAction}
            />
          )}
        </div>
      </div>
    </section>
  );
}

function sourceFieldErrors(sourceForm: SourceForm): Partial<Record<"title" | "uri" | "raw_text" | "freshness_days", string>> {
  const errors: Partial<Record<"title" | "uri" | "raw_text" | "freshness_days", string>> = {};
  const rawText = sourceForm.raw_text.trim();
  const uri = sourceForm.uri.trim();

  if (!sourceForm.title.trim()) errors.title = "Required";
  if (rawText.length < 20) errors.raw_text = "Must contain at least 20 characters";
  if (Number(sourceForm.freshness_days) < 1) errors.freshness_days = "Must be at least 1 day";

  if (sourceForm.source_type === "url") {
    if (!uri) errors.uri = "Required";
    else if (!validateHttpUrl(uri)) errors.uri = "Enter a valid http(s) URL";
  }
  if (sourceForm.source_type === "github_release") {
    if (!uri) {
      errors.uri = "Required";
    } else if (!validateHttpUrl(uri) || new URL(uri).hostname.toLowerCase() !== "github.com") {
      errors.uri = "Enter a valid github.com URL";
    }
  }
  if (sourceForm.source_type === "notion_page") {
    const isNotionProtocol = uri.startsWith("notion://page/");
    const isNotionUrl = validateHttpUrl(uri) && new URL(uri).hostname.endsWith("notion.so");
    if (!uri) {
      errors.uri = "Required";
    } else if (!isNotionProtocol && !isNotionUrl) {
      errors.uri = "Enter a selected Notion page URL";
    }
  }

  return errors;
}

function visibleSourceFieldErrors(
  sourceForm: SourceForm,
  touchedFields: Partial<Record<"title" | "uri" | "raw_text" | "freshness_days", boolean>>,
  showAll: boolean,
): Partial<Record<"title" | "uri" | "raw_text" | "freshness_days", string>> {
  const allErrors = sourceFieldErrors(sourceForm);
  if (showAll) return allErrors;
  return Object.fromEntries(Object.entries(allErrors).filter(([field]) => touchedFields[field as keyof typeof touchedFields]));
}
