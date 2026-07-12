import type {
  ApprovalPolicy,
  ContentBrief,
  Draft,
  FormatChoice,
  LinkedInIntegration,
  Opportunity,
  ReviewerPackage,
  Source,
} from "../../types";
import { FileCheck2, Layers, ListChecks, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import {
  contentTypeDisplayName,
  formatChoiceLabel,
  formatChoicePlatform,
  platformDisplayName,
  summarizeNames,
} from "../../lib/forms";
import { OpportunitiesPanel } from "./OpportunitiesPanel";
import { BriefPanel } from "./BriefPanel";
import { DraftVariantsPanel } from "./DraftVariantsPanel";
import { DraftPreviewPanel } from "./DraftPreviewPanel";
import { ReviewDesk } from "./ReviewDesk";
import { TrustTimelinePanel, type TrustTimelineItem } from "./TrustTimelinePanel";

type StudioViewProps = {
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
  approvedSources: Source[];
  rankedOpportunities: Opportunity[];
  visibleOpportunities: Opportunity[];
  hiddenOpportunityCount: number;
  selectedOpportunity: Opportunity | null;
  opportunityMessage: string;
  opportunityCount: number;
  selectedBrief: ContentBrief | null;
  formatChoice: FormatChoice;
  drafts: Draft[];
  selectedDraft: Draft | null;
  reviewPackage: ReviewerPackage | null;
  approvalPolicy: ApprovalPolicy | null;
  approvalProgress: Record<string, unknown>;
  editedBody: string;
  reviewReason: string;
  scheduleFor: string;
  linkedinIntegration: LinkedInIntegration | null;
  onGenerateOpportunities: () => void | Promise<void>;
  onCreateBrief: (opportunity: Opportunity) => void | Promise<void>;
  onShowMoreOpportunities: () => void;
  onSelectContentFormat: (choice: FormatChoice) => void;
  onGenerateDraftsFromBrief: () => void | Promise<void>;
  onSelectDraft: (draft: Draft) => void;
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

export function StudioView({
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
  approvedSources,
  rankedOpportunities,
  visibleOpportunities,
  hiddenOpportunityCount,
  selectedOpportunity,
  opportunityMessage,
  opportunityCount,
  selectedBrief,
  formatChoice,
  drafts,
  selectedDraft,
  reviewPackage,
  approvalPolicy,
  approvalProgress,
  editedBody,
  reviewReason,
  scheduleFor,
  linkedinIntegration,
  onGenerateOpportunities,
  onCreateBrief,
  onShowMoreOpportunities,
  onSelectContentFormat,
  onGenerateDraftsFromBrief,
  onSelectDraft,
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
}: StudioViewProps) {
  const [activeSection, setActiveSection] = useState<"overview" | "opportunities" | "brief" | "drafts" | "review">("overview");
  const sourceTitleById = new Map(approvedSources.map((source) => [source.id, source.title]));
  const activeSourceSummary = summarizeNames(approvedSources.map((source) => source.title), 3);
  const selectedFormatConfig = formatChoicePlatform(formatChoice);
  const selectedFormatLabel = formatChoiceLabel(formatChoice);
  const selectedDraftMatchesFormat =
    Boolean(selectedDraft) &&
    selectedDraft?.platform === selectedFormatConfig.platform &&
    selectedDraft?.content_type === selectedFormatConfig.contentType;
  const selectedDraftBody = editedBody || selectedDraft?.body || "";
  const previewParagraphs = selectedDraftBody
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
  const selectedBriefOpportunity = selectedBrief
    ? selectedOpportunity?.id === selectedBrief.opportunity_id
      ? selectedOpportunity
      : rankedOpportunities.find((opportunity) => opportunity.id === selectedBrief.opportunity_id) ?? selectedOpportunity
    : null;
  const selectedBriefOpportunityRank = selectedBrief
    ? rankedOpportunities.findIndex((opportunity) => opportunity.id === selectedBrief.opportunity_id)
    : -1;
  const selectedBriefOpportunityLabel =
    selectedBriefOpportunityRank >= 0 ? `Opportunity #${selectedBriefOpportunityRank + 1}` : "Selected opportunity";
  const supportedClaimCount = selectedDraft?.claims.filter((claim) => claim.support_status === "supported").length ?? 0;
  const unsupportedClaimCount = selectedDraft?.claims.filter((claim) => claim.support_status === "unsupported").length ?? 0;
  const duplicateMatchCount = selectedDraft?.duplicate_report.similar_posts.length ?? 0;
  const selectedDraftAdapter = selectedDraft ? String(selectedDraft.generation_metadata.adapter_name ?? `${selectedDraft.platform} adapter`) : "";
  const selectedDraftPromptVersion = selectedDraft ? String(selectedDraft.generation_metadata.prompt_version ?? "prompt tracked") : "";
  const trustTimelineItems: TrustTimelineItem[] = [];

  if (selectedDraft) {
    trustTimelineItems.push({
      step: "Source basis",
      title: approvedSources.length > 0 ? "Approved knowledge is available" : "Approved knowledge is missing",
      detail:
        approvedSources.length > 0
          ? `${approvedSources.length} approved source${approvedSources.length === 1 ? "" : "s"} can support recommendations and claims: ${activeSourceSummary}.`
          : "Add approved company knowledge before relying on recommendations.",
      status: approvedSources.length > 0 ? "complete" : "warning",
    });
  }
  if (selectedDraft && selectedOpportunity) {
    trustTimelineItems.push({
      step: "Opportunity",
      title: selectedOpportunity.title,
      detail: `${Math.round(selectedOpportunity.relevance_score * 100)}% relevance, ${Math.round(
        selectedOpportunity.freshness_score * 100,
      )}% freshness, ${selectedOpportunity.source_ids.length} source${selectedOpportunity.source_ids.length === 1 ? "" : "s"}: ${selectedOpportunity.source_ids
        .map((sourceId) => sourceTitleById.get(sourceId) ?? sourceId)
        .slice(0, 2)
        .join(", ")}.`,
      status: selectedOpportunity.status === "warned" ? "warning" : "complete",
    });
  }
  if (selectedDraft && selectedBrief) {
    trustTimelineItems.push({
      step: "Brief",
      title: selectedBrief.key_message,
      detail: `${selectedBrief.supporting_points.length} supporting points and ${selectedBrief.risks.length} risk guardrail${
        selectedBrief.risks.length === 1 ? "" : "s"
      } carried into generation.`,
      status: "complete",
    });
  }
  if (selectedDraft) {
    trustTimelineItems.push({
      step: "Draft",
      title: `${platformDisplayName(selectedDraft.platform)} ${contentTypeDisplayName(selectedDraft.content_type)}`,
      detail: `${selectedDraftAdapter} generated this artifact with ${selectedDraft.source_ids.length} source${
        selectedDraft.source_ids.length === 1 ? "" : "s"
      } and ${selectedDraftPromptVersion}.`,
      status: "complete",
    });
    trustTimelineItems.push({
      step: "Checks",
      title: unsupportedClaimCount > 0 ? "Review needed before approval" : "Review checks are ready",
      detail: `${supportedClaimCount}/${selectedDraft.claims.length} claims supported, ${selectedDraft.risk_report.length} risk note${
        selectedDraft.risk_report.length === 1 ? "" : "s"
      }, ${duplicateMatchCount} similar memory match${duplicateMatchCount === 1 ? "" : "es"}.`,
      status: unsupportedClaimCount > 0 || selectedDraft.risk_report.length > 0 ? "warning" : "complete",
    });
  }
  if (reviewPackage) {
    trustTimelineItems.push({
      step: "Reviewer action",
      title: reviewPackage.suggested_action,
      detail:
        reviewPackage.decision_history.length > 0
          ? `${reviewPackage.decision_history.length} recorded decision${reviewPackage.decision_history.length === 1 ? "" : "s"}.`
          : "No reviewer decision has been recorded yet.",
      status: reviewPackage.suggested_action.toLowerCase().includes("unsupported") ? "warning" : "pending",
    });
    reviewPackage.decision_history.slice(0, 1).forEach((decision) => {
      trustTimelineItems.push({
        step: "Latest decision",
        title: decision.decision,
        detail: `${new Date(decision.created_at).toLocaleString()}${decision.reason ? ` - ${decision.reason}` : ""}`,
        status: decision.decision === "rejected" ? "warning" : "complete",
      });
    });
  }

  const workflowPanel = (
    <section className="panel band studio-flow-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Studio workflow</p>
          <h2>Opportunity to reviewed artifact</h2>
        </div>
        <span className="hero-badge">{selectedBrief ? "Brief ready" : "No active brief"}</span>
      </div>
      <div className="studio-flow-grid">
        <article className={selectedOpportunity ? "complete" : ""}>
          <span>1</span>
          <strong>Opportunity</strong>
          <p>{selectedOpportunity?.title ?? `${rankedOpportunities.length} ranked angles available`}</p>
        </article>
        <article className={selectedBrief ? "complete" : ""}>
          <span>2</span>
          <strong>Brief</strong>
          <p>{selectedBrief ? selectedBrief.key_message : "Create a brief from one selected angle."}</p>
        </article>
        <article className={drafts.length > 0 ? "complete" : ""}>
          <span>3</span>
          <strong>Drafts</strong>
          <p>{drafts.length > 0 ? `${drafts.length} generated variant${drafts.length === 1 ? "" : "s"}` : "Generate variants only after a brief exists."}</p>
        </article>
        <article className={reviewPackage ? "complete" : ""}>
          <span>4</span>
          <strong>Review</strong>
          <p>{reviewPackage ? reviewPackage.suggested_action : "Approve, reject, edit, export, or schedule from the review desk."}</p>
        </article>
      </div>
    </section>
  );

  const opportunitiesPanel = (
    <OpportunitiesPanel
      busy={busy}
      canEditContent={canEditContent}
      permissionMessage={knowledgePermissionMessage}
      approvedSources={approvedSources}
      rankedOpportunities={rankedOpportunities}
      visibleOpportunities={visibleOpportunities}
      hiddenOpportunityCount={hiddenOpportunityCount}
      selectedOpportunity={selectedOpportunity}
      opportunityMessage={opportunityMessage}
      opportunityCount={opportunityCount}
      onGenerate={onGenerateOpportunities}
      onCreateBrief={async (opportunity) => {
        await onCreateBrief(opportunity);
        setActiveSection("brief");
      }}
      onShowMore={onShowMoreOpportunities}
    />
  );

  const emptyBriefPanel = (
    <section className="panel band">
      <div className="empty-detail">
        <FileCheck2 size={24} />
        <strong>No brief exists yet</strong>
        <p>Create a brief from a selected opportunity before choosing formats or generating draft variants.</p>
      </div>
    </section>
  );

  const emptyDraftPanel = (
    <section className="panel band">
      <div className="empty-detail">
        <Layers size={24} />
        <strong>No drafts generated</strong>
        <p>Draft variants appear after a brief exists and a format has been selected.</p>
      </div>
    </section>
  );

  const emptyReviewPanel = (
    <section className="panel band">
      <div className="empty-detail">
        <ShieldCheck size={24} />
        <strong>No draft selected for review</strong>
        <p>Generate and select a draft to see review checks, decisions, export, publish, and schedule controls.</p>
      </div>
    </section>
  );

  return (
    <section className="section-workspace studio-workspace">
      <aside className="section-sidebar" aria-label="Studio sections">
        <button className={activeSection === "overview" ? "active" : ""} onClick={() => setActiveSection("overview")} type="button">
          <ListChecks size={16} />
          <span>Overview</span>
          <small>{selectedBrief ? "Brief ready" : "No brief"}</small>
        </button>
        <button className={activeSection === "opportunities" ? "active" : ""} onClick={() => setActiveSection("opportunities")} type="button">
          <Sparkles size={16} />
          <span>Opportunities</span>
          <small>{rankedOpportunities.length} ranked</small>
        </button>
        <button className={activeSection === "brief" ? "active" : ""} onClick={() => setActiveSection("brief")} type="button">
          <FileCheck2 size={16} />
          <span>Brief</span>
          <small>{selectedBrief ? `Exists (${selectedBriefOpportunityLabel.replace("Opportunity ", "")})` : "Not created"}</small>
        </button>
        <button className={activeSection === "drafts" ? "active" : ""} onClick={() => setActiveSection("drafts")} type="button">
          <Layers size={16} />
          <span>Drafts</span>
          <small>{drafts.length} variants</small>
        </button>
        <button className={activeSection === "review" ? "active" : ""} onClick={() => setActiveSection("review")} type="button">
          <ShieldCheck size={16} />
          <span>Review</span>
          <small>{reviewPackage ? "Ready" : "Waiting"}</small>
        </button>
      </aside>

      <div className="section-content">
        {activeSection === "overview" && workflowPanel}
        {activeSection === "opportunities" && opportunitiesPanel}
        {activeSection === "brief" &&
          (selectedBrief ? (
            <BriefPanel
              brief={selectedBrief}
              opportunity={selectedBriefOpportunity}
              opportunityLabel={selectedBriefOpportunityLabel}
              selectedFormatLabel={selectedFormatLabel}
              formatChoice={formatChoice}
              busy={busy}
              canEditContent={canEditContent}
              permissionMessage={knowledgePermissionMessage}
              onSelectContentFormat={onSelectContentFormat}
              onGenerateDrafts={async () => {
                await onGenerateDraftsFromBrief();
                setActiveSection("drafts");
              }}
            />
          ) : (
            emptyBriefPanel
          ))}
        {activeSection === "drafts" && (
          <>
            {drafts.length > 0 ? (
              <DraftVariantsPanel
                drafts={drafts}
                selectedDraft={selectedDraft}
                selectedDraftMatchesFormat={selectedDraftMatchesFormat}
                onSelectDraft={onSelectDraft}
                onReviewDraft={(draft) => {
                  onSelectDraft(draft);
                  setActiveSection("review");
                }}
              />
            ) : (
              emptyDraftPanel
            )}
            {selectedDraft && (
              <DraftPreviewPanel
                draft={selectedDraft}
                selectedOpportunity={selectedOpportunity}
                reviewPackage={reviewPackage}
                previewParagraphs={previewParagraphs}
                supportedClaimCount={supportedClaimCount}
                unsupportedClaimCount={unsupportedClaimCount}
                duplicateMatchCount={duplicateMatchCount}
              />
            )}
          </>
        )}
        {activeSection === "review" && (
          <>
            {selectedDraft && <TrustTimelinePanel items={trustTimelineItems} />}
            {reviewPackage && selectedDraft ? (
              <ReviewDesk
                busy={busy}
                canEditContent={canEditContent}
                canReviewContent={canReviewContent}
                canApproveDraft={canApproveDraft}
                canExportDraft={canExportDraft}
                canScheduleDraft={canScheduleDraft}
                canAttemptLinkedinPublish={canAttemptLinkedinPublish}
                knowledgePermissionMessage={knowledgePermissionMessage}
                reviewPermissionMessage={reviewPermissionMessage}
                approvalBlocked={approvalBlocked}
                publishCapabilityText={publishCapabilityText}
                opportunityLabel={selectedBriefOpportunityLabel}
                draft={selectedDraft}
                reviewPackage={reviewPackage}
                approvalPolicy={approvalPolicy}
                approvalProgress={approvalProgress}
                editedBody={editedBody}
                reviewReason={reviewReason}
                scheduleFor={scheduleFor}
                linkedinIntegration={linkedinIntegration}
                onEditedBodyChange={onEditedBodyChange}
                onReviewReasonChange={onReviewReasonChange}
                onSaveDraftEdit={onSaveDraftEdit}
                onApproveDraft={onApproveDraft}
                onRejectDraft={onRejectDraft}
                onExportDraft={onExportDraft}
                onPublishDraftToLinkedIn={onPublishDraftToLinkedIn}
                onRegenerateSelectedDraft={onRegenerateSelectedDraft}
                onScheduleForChange={onScheduleForChange}
                onScheduleDraft={onScheduleDraft}
              />
            ) : (
              emptyReviewPanel
            )}
          </>
        )}
      </div>
    </section>
  );
}
