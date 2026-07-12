import { Library, RefreshCcw } from "lucide-react";
import type { SourceDetail } from "../../types";
import { sourceStatuses } from "./sourceConfig";

type SourceDetailPanelProps = {
  busy: boolean;
  canEditKnowledge: boolean;
  permissionMessage: string;
  sourceDetail: SourceDetail | null;
  approvedCount: number;
  disabledCount: number;
  archivedCount: number;
  onUpdateSourceStatus: (sourceId: string, approvalStatus: string) => void | Promise<void>;
  onRefreshSource: (sourceId: string) => void | Promise<void>;
  formatAuditTime: (value: string) => string;
};

export function SourceDetailPanel({
  busy,
  canEditKnowledge,
  permissionMessage,
  sourceDetail,
  approvedCount,
  disabledCount,
  archivedCount,
  onUpdateSourceStatus,
  onRefreshSource,
  formatAuditTime,
}: SourceDetailPanelProps) {
  const sourceAuditLogs = [...(sourceDetail?.audit_logs ?? [])].sort(
    (left, right) => Date.parse(right.created_at) - Date.parse(left.created_at),
  );
  const visibleSourceAuditLogs = sourceAuditLogs.slice(0, 6);

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
          <div className="source-actions">
            {sourceStatuses.map((status) => (
              <button
                className={sourceDetail.source.approval_status === status ? "active" : ""}
                key={status}
                onClick={() => void onUpdateSourceStatus(sourceDetail.source.id, status)}
                disabled={busy || !canEditKnowledge}
              >
                {status}
              </button>
            ))}
            <button
              onClick={() => void onRefreshSource(sourceDetail.source.id)}
              disabled={busy || !canEditKnowledge}
              title={canEditKnowledge ? "Refresh source" : permissionMessage}
            >
              <RefreshCcw size={15} />
              refresh
            </button>
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
          <div className="source-raw-block">
            <div>
              <h4>Source text</h4>
              <span>{sourceDetail.raw_text.length.toLocaleString()} chars</span>
            </div>
            <p className="source-raw">{sourceDetail.raw_text}</p>
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
