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
    reviewPackage.decision_history.slice(0, 3).forEach((decision) => {
      trustTimelineItems.push({
        step: "Decision",
        title: decision.decision,
        detail: `${new Date(decision.created_at).toLocaleString()}${decision.reason ? ` - ${decision.reason}` : ""}`,
        status: decision.decision === "rejected" ? "warning" : "complete",
      });
    });
  }

  return (
    <>
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
        onCreateBrief={onCreateBrief}
        onShowMore={onShowMoreOpportunities}
      />

      {selectedBrief && (
        <BriefPanel
          brief={selectedBrief}
          selectedFormatLabel={selectedFormatLabel}
          formatChoice={formatChoice}
          busy={busy}
          canEditContent={canEditContent}
          permissionMessage={knowledgePermissionMessage}
          onSelectContentFormat={onSelectContentFormat}
          onGenerateDrafts={onGenerateDraftsFromBrief}
        />
      )}

      {drafts.length > 0 && (
        <DraftVariantsPanel
          drafts={drafts}
          selectedDraft={selectedDraft}
          selectedDraftMatchesFormat={selectedDraftMatchesFormat}
          onSelectDraft={onSelectDraft}
        />
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
          selectedDraftAdapter={selectedDraftAdapter}
          selectedDraftPromptVersion={selectedDraftPromptVersion}
        />
      )}

      {selectedDraft && <TrustTimelinePanel items={trustTimelineItems} />}

      {reviewPackage && selectedDraft && (
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
      )}
    </>
  );
}
