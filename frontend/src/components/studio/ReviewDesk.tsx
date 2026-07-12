import { Archive, CalendarClock, Check, Clipboard, FileText, Library, RefreshCcw, Save, Send, ShieldCheck, X } from "lucide-react";
import type { ApprovalPolicy, Draft, LinkedInIntegration, ReviewerPackage } from "../../types";
import { InsightList } from "../ui/InsightList";

type ReviewDeskProps = {
  busy: boolean;
  canEditContent: boolean;
  canReviewContent: boolean;
  canApproveDraft: boolean;
  canExportDraft: boolean;
  canScheduleDraft: boolean;
  canAttemptLinkedinPublish: boolean;
  knowledgePermissionMessage: string;
  reviewPermissionMessage: string;
  approvalBlocked: boolean;
  publishCapabilityText: string;
  draft: Draft;
  reviewPackage: ReviewerPackage;
  approvalPolicy: ApprovalPolicy | null;
  approvalProgress: Record<string, unknown>;
  editedBody: string;
  reviewReason: string;
  scheduleFor: string;
  linkedinIntegration: LinkedInIntegration | null;
  onEditedBodyChange: (body: string) => void;
  onReviewReasonChange: (reason: string) => void;
  onSaveDraftEdit: () => void | Promise<void>;
  onApproveDraft: () => void | Promise<void>;
  onRejectDraft: () => void | Promise<void>;
  onExportDraft: () => void | Promise<void>;
  onPublishDraftToLinkedIn: () => void | Promise<void>;
  onRegenerateSelectedDraft: () => void | Promise<void>;
  onScheduleForChange: (value: string) => void;
  onScheduleDraft: () => void | Promise<void>;
};

export function ReviewDesk({
  busy,
  canEditContent,
  canReviewContent,
  canApproveDraft,
  canExportDraft,
  canScheduleDraft,
  canAttemptLinkedinPublish,
  knowledgePermissionMessage,
  reviewPermissionMessage,
  approvalBlocked,
  publishCapabilityText,
  draft,
  reviewPackage,
  approvalPolicy,
  approvalProgress,
  editedBody,
  reviewReason,
  scheduleFor,
  linkedinIntegration,
  onEditedBodyChange,
  onReviewReasonChange,
  onSaveDraftEdit,
  onApproveDraft,
  onRejectDraft,
  onExportDraft,
  onPublishDraftToLinkedIn,
  onRegenerateSelectedDraft,
  onScheduleForChange,
  onScheduleDraft,
}: ReviewDeskProps) {
  return (
    <section className="review-grid">
      <section className="panel review-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Review Desk</p>
            <h2>{draft.status.replace("_", " ")}</h2>
          </div>
          <span className="review-status">{reviewPackage.suggested_action}</span>
        </div>
        <textarea value={editedBody} onChange={(event) => onEditedBodyChange(event.target.value)} />
        {approvalPolicy && (
          <div className="approval-progress">
            <span>
              {Number(approvalProgress.approved_reviewer_count ?? 0)} / {approvalPolicy.required_reviewer_count} approvals
            </span>
            <span>{String((approvalProgress.approved_reviewer_ids as string[] | undefined)?.join(", ") || "No approvals yet")}</span>
          </div>
        )}
        <div className="review-control-stack">
          <label className="review-note-field">
            <span>Decision note</span>
            <input
              value={reviewReason}
              onChange={(event) => onReviewReasonChange(event.target.value)}
              placeholder="Add context for approval, rejection, export, or scheduling"
            />
          </label>
          <div className="review-action-grid">
            <section className="review-action-card">
              <div>
                <span>Review decision</span>
                <p>Approve only when claims and risk checks are acceptable. Rejections require a note.</p>
              </div>
              <div className="action-row">
                <button
                  className="icon-button"
                  onClick={() => void onSaveDraftEdit()}
                  disabled={busy || !canEditContent || editedBody === draft.body}
                  title={canEditContent ? "Save edit" : knowledgePermissionMessage}
                >
                  <Save size={18} />
                  <span>Save edit</span>
                </button>
                <button
                  className="icon-button primary"
                  onClick={() => void onApproveDraft()}
                  disabled={!canApproveDraft}
                  title={!canReviewContent ? reviewPermissionMessage : approvalBlocked ? "Resolve unsupported claims before approval" : "Approve draft"}
                >
                  <Check size={18} />
                  <span>Approve</span>
                </button>
                <button
                  className="icon-button"
                  onClick={() => void onRejectDraft()}
                  disabled={busy || !canReviewContent || !reviewReason.trim()}
                  title={canReviewContent ? "Reject draft" : reviewPermissionMessage}
                >
                  <X size={18} />
                  <span>Reject</span>
                </button>
              </div>
            </section>

            <section className="review-action-card">
              <div>
                <span>Delivery</span>
                <p>{publishCapabilityText}</p>
              </div>
              <div className="action-row">
                <button className="icon-button" onClick={() => void onExportDraft()} disabled={busy || !canExportDraft} title="Export draft">
                  <Clipboard size={18} />
                  <span>Export</span>
                </button>
                <button
                  className="icon-button"
                  onClick={() => void onPublishDraftToLinkedIn()}
                  disabled={busy || !canAttemptLinkedinPublish || !linkedinIntegration?.selected_page_urn}
                  title="Publish approved LinkedIn post"
                >
                  <Send size={18} />
                  <span>Publish</span>
                </button>
                <button
                  className="icon-button"
                  onClick={() => void onRegenerateSelectedDraft()}
                  disabled={busy || !canEditContent || !draft}
                  title={canEditContent ? "Regenerate drafts" : knowledgePermissionMessage}
                >
                  <RefreshCcw size={18} />
                  <span>Regenerate</span>
                </button>
              </div>
            </section>

            <section className="review-action-card schedule-card">
              <div>
                <span>Schedule intent</span>
                <p>Save this artifact to the internal calendar for planning. This does not publish to Reddit, blogs, or unsupported channels.</p>
              </div>
              <div className="schedule-row">
                <input
                  type="datetime-local"
                  value={scheduleFor}
                  onChange={(event) => onScheduleForChange(event.target.value)}
                  aria-label="Schedule intent date and time"
                />
                <button
                  className="icon-button"
                  onClick={() => void onScheduleDraft()}
                  disabled={busy || !canScheduleDraft || !scheduleFor}
                  title="Save schedule intent"
                >
                  <CalendarClock size={18} />
                  <span>Schedule</span>
                </button>
              </div>
            </section>
          </div>
        </div>
      </section>

      <aside className="evidence-column">
        <InsightList title="Risk" icon={<Archive size={17} />} items={draft.risk_report} />
        <InsightList title="Quality" icon={<ShieldCheck size={17} />} items={draft.quality_report} />
        {draft.duplicate_report.similar_posts.length > 0 && (
          <section className="panel compact">
            <div className="panel-title">
              <RefreshCcw size={17} />
              <h2>Similar Memory</h2>
            </div>
            {draft.duplicate_report.similar_posts.map((post) => (
              <div className="memory-match" key={post.excerpt}>
                <strong>{Math.round(post.score * 100)}% similar</strong>
                <p>{post.excerpt}</p>
              </div>
            ))}
          </section>
        )}
        {reviewPackage.decision_history.length > 0 && (
          <section className="panel compact">
            <div className="panel-title">
              <ShieldCheck size={17} />
              <h2>Decision History</h2>
            </div>
            {reviewPackage.decision_history.map((decision) => (
              <div className="decision-row" key={decision.id}>
                <strong>{decision.decision}</strong>
                <span>{new Date(decision.created_at).toLocaleString()}</span>
                {decision.reason && <p>{decision.reason}</p>}
              </div>
            ))}
          </section>
        )}
        <section className="panel compact">
          <div className="panel-title">
            <FileText size={17} />
            <h2>Claims</h2>
          </div>
          <div className="claim-list">
            {draft.claims.map((claim) => (
              <div className="claim-row" key={claim.text}>
                <span className={`dot ${claim.support_status}`} />
                <p>{claim.text}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="panel compact">
          <div className="panel-title">
            <Library size={17} />
            <h2>Evidence</h2>
          </div>
          {reviewPackage.source_chunks.slice(0, 4).map((chunk) => (
            <p className="excerpt" key={chunk.id}>
              {chunk.chunk_text}
            </p>
          ))}
        </section>
      </aside>
    </section>
  );
}
