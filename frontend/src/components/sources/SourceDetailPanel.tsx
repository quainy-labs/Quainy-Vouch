import { Library, RefreshCcw, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { SourceDetail } from "../../types";
import { sourceStatuses } from "./sourceConfig";

type SourceDetailPanelProps = {
  busy: boolean;
  canEditKnowledge: boolean;
  permissionMessage: string;
  selectedSourceId: string | null;
  sourceDetail: SourceDetail | null;
  approvedCount: number;
  disabledCount: number;
  archivedCount: number;
  onUpdateSourceStatus: (sourceId: string, approvalStatus: string) => void | Promise<void>;
  onUpdateSource: (
    sourceId: string,
    payload: { title?: string; uri?: string | null; raw_text?: string; approval_status?: string; freshness_days?: number },
  ) => void | Promise<void>;
  onRefreshSource: (sourceId: string) => void | Promise<void>;
  formatAuditTime: (value: string) => string;
};

export function SourceDetailPanel({
  busy,
  canEditKnowledge,
  permissionMessage,
  selectedSourceId,
  sourceDetail,
  approvedCount,
  disabledCount,
  archivedCount,
  onUpdateSourceStatus,
  onUpdateSource,
  onRefreshSource,
  formatAuditTime,
}: SourceDetailPanelProps) {
  const [draft, setDraft] = useState({ title: "", uri: "", raw_text: "", approval_status: "approved", freshness_days: "180" });
  const sourceAuditLogs = [...(sourceDetail?.audit_logs ?? [])].sort(
    (left, right) => Date.parse(right.created_at) - Date.parse(left.created_at),
  );
  const visibleSourceAuditLogs = sourceAuditLogs.slice(0, 6);
  const hasSourceChanges = useMemo(() => {
    if (!sourceDetail) return false;
    return (
      draft.title !== sourceDetail.source.title ||
      draft.uri !== (sourceDetail.source.uri ?? "") ||
      draft.raw_text !== sourceDetail.raw_text ||
      draft.approval_status !== sourceDetail.source.approval_status ||
      Number(draft.freshness_days) !== sourceDetail.source.freshness_days
    );
  }, [draft, sourceDetail]);
  const canSaveSource =
    Boolean(sourceDetail) && draft.title.trim().length > 0 && draft.raw_text.trim().length >= 20 && Number(draft.freshness_days) >= 1 && hasSourceChanges;

  useEffect(() => {
    if (!sourceDetail) return;
    setDraft({
      title: sourceDetail.source.title,
      uri: sourceDetail.source.uri ?? "",
      raw_text: sourceDetail.raw_text,
      approval_status: sourceDetail.source.approval_status,
      freshness_days: String(sourceDetail.source.freshness_days),
    });
  }, [sourceDetail]);

  return (
    <section className="source-detail">
      {sourceDetail ? (
        <>
          <div className="source-detail-header">
            <div>
              <p className="eyebrow">Source Detail</p>
              <h3>{sourceDetail.source.title}</h3>
            </div>
            <span className={`status-pill ${sourceDetail.source.approval_status}`}>{sourceDetail.source.approval_status}</span>
          </div>
          {busy && (
            <div className="work-status" role="status">
              <strong>Updating source</strong>
              <span>Saving changes, refreshing detail, and invalidating generated work that depends on old evidence.</span>
            </div>
          )}

          <div className="source-edit-panel">
            <div className="source-edit-grid">
              <label className="micro-field wide">
                <span>Title</span>
                <input value={draft.title} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} />
              </label>
              <label className="micro-field">
                <span>Status</span>
                <select value={draft.approval_status} onChange={(event) => setDraft((current) => ({ ...current, approval_status: event.target.value }))}>
                  {sourceStatuses.map((status) => (
                    <option value={status} key={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label className="micro-field">
                <span>Refresh days</span>
                <input
                  value={draft.freshness_days}
                  onChange={(event) => setDraft((current) => ({ ...current, freshness_days: event.target.value }))}
                  inputMode="numeric"
                />
              </label>
              <label className="micro-field wide">
                <span>Origin</span>
                <input value={draft.uri} onChange={(event) => setDraft((current) => ({ ...current, uri: event.target.value }))} />
              </label>
              <label className="micro-field wide">
                <span>Source text</span>
                <textarea
                  className="source-textarea"
                  value={draft.raw_text}
                  onChange={(event) => setDraft((current) => ({ ...current, raw_text: event.target.value }))}
                />
              </label>
            </div>
            <div className="source-actions">
              <button
                className="icon-button primary"
                onClick={() =>
                  void onUpdateSource(sourceDetail.source.id, {
                    title: draft.title,
                    uri: draft.uri || null,
                    raw_text: draft.raw_text,
                    approval_status: draft.approval_status,
                    freshness_days: Number(draft.freshness_days) || 180,
                  })
                }
                disabled={busy || !canEditKnowledge || !canSaveSource}
                title={!canEditKnowledge ? permissionMessage : canSaveSource ? "Save source changes" : "Change a valid source field before saving"}
                type="button"
              >
                <Save size={16} />
                <span>Save source</span>
              </button>
              <button
                className="icon-button"
                onClick={() => void onRefreshSource(sourceDetail.source.id)}
                disabled={busy || !canEditKnowledge}
                title={canEditKnowledge ? "Refresh source" : permissionMessage}
                type="button"
              >
                <RefreshCcw size={16} />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          <div className="source-meta">
            <div>
              <span>Type</span>
              <strong>{sourceDetail.source.source_type.replace("_", " ")}</strong>
            </div>
            <div>
              <span>Chunks</span>
              <strong>{sourceDetail.chunk_count}</strong>
            </div>
            <div>
              <span>Refresh</span>
              <strong>{sourceDetail.source.freshness_days} days</strong>
            </div>
            {sourceDetail.source.uri && (
              <div>
                <span>Origin</span>
                <strong>{sourceDetail.source.uri}</strong>
              </div>
            )}
          </div>
          <div className="audit-list">
            <div className="audit-heading">
              <h4>Audit events</h4>
              {sourceAuditLogs.length > 0 && (
                <span>
                  Latest {visibleSourceAuditLogs.length} of {sourceAuditLogs.length} - IST
                </span>
              )}
            </div>
            {sourceAuditLogs.length > 0 ? (
              <div className="audit-scroll">
                {visibleSourceAuditLogs.map((log) => (
                  <div className="audit-row" key={log.id}>
                    <strong>{log.action}</strong>
                    <span>{formatAuditTime(log.created_at)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-results">No audit events recorded yet.</p>
            )}
          </div>
        </>
      ) : selectedSourceId ? (
        <div className="empty-detail">
          <Library size={24} />
          <strong>Loading source detail</strong>
          <p>The selected source detail, source text, status controls, and audit events will appear here.</p>
        </div>
      ) : (
        <div className="empty-detail">
          <Library size={24} />
          <strong>Choose a source to inspect</strong>
          <p>Source text, status, chunk count, origin, refresh policy, and audit events will appear here.</p>
          <div className="empty-detail-stats">
            <span>{approvedCount} approved</span>
            <span>{disabledCount} disabled</span>
            <span>{archivedCount} archived</span>
          </div>
        </div>
      )}
    </section>
  );
}
