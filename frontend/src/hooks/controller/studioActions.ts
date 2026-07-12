import { api } from "../../lib/api";
import { canBuildBrief, formatChoiceLabel, formatChoiceNotice, formatChoiceParams, sortOpportunities } from "../../lib/forms";
import type { ContentBrief, Draft, FormatChoice, Opportunity, PublishResult, ReviewerPackage } from "../../types";
import type { WorkspaceControllerState } from "./useWorkspaceControllerState";

type StudioActionsOptions = {
  canEditContent: boolean;
  canReviewContent: boolean;
  knowledgePermissionMessage: string;
  reviewPermissionMessage: string;
  requirePermission: (allowed: boolean, message: string) => boolean;
  refreshCalendar: () => Promise<void>;
  refreshCurrentWorkspaceState: () => Promise<unknown>;
  refreshMemoryAndAnalytics: () => Promise<void>;
  refreshProductSurfaces: (organizationId?: string) => Promise<void>;
};

export function createStudioActions(state: WorkspaceControllerState, options: StudioActionsOptions) {
  function resetSelectedWork() {
    state.setSelectedBrief(null);
    state.setDrafts([]);
    state.setSelectedDraft(null);
  }

  function selectContentFormat(choice: FormatChoice) {
    if (state.busy) return;
    state.setFormatChoice(choice);
    state.setDrafts([]);
    state.setSelectedDraft(null);
    state.setReviewPackage(null);
    state.setEditedBody("");
    state.setReviewReason("");
    state.setScheduleFor("");
    state.setNotice(`Draft format set to ${formatChoiceLabel(choice)}. Generate fresh drafts from the selected brief.`);
  }

  async function generateOpportunities() {
    if (!state.bootstrap) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      const result = await api<{ opportunities: Opportunity[]; message?: string }>(
        `/organizations/${state.bootstrap.organization.id}/opportunities/generate`,
        { method: "POST" },
      );
      const ranked = sortOpportunities(result.opportunities);
      state.setOpportunities(ranked);
      state.setVisibleOpportunityCount(12);
      state.setOpportunityMessage(result.message ?? (result.opportunities.length ? "Opportunities generated from approved source context." : ""));
      state.setSelectedOpportunity(ranked[0] ?? null);
      resetSelectedWork();
      await options.refreshProductSurfaces();
      await options.refreshCurrentWorkspaceState();
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Opportunity generation failed.");
    } finally {
      state.setBusy(false);
    }
  }

  async function createBrief(opportunity: Opportunity) {
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    if (!canBuildBrief(opportunity)) {
      state.setSelectedOpportunity(opportunity);
      resetSelectedWork();
      state.setNotice("This trend needs approved company context before a brief can be created.");
      return;
    }
    state.setBusy(true);
    try {
      state.setSelectedOpportunity(opportunity);
      state.setDrafts([]);
      state.setSelectedDraft(null);
      const brief = await api<ContentBrief>(`/opportunities/${opportunity.id}/briefs`, { method: "POST" });
      state.setSelectedBrief(brief);
      state.setActiveView("studio");
      await options.refreshProductSurfaces();
      await options.refreshCurrentWorkspaceState();
      state.setNotice("Brief created from approved source context.");
    } finally {
      state.setBusy(false);
    }
  }

  async function generateDraftsFromBrief() {
    if (!state.selectedBrief) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      const params = formatChoiceParams(state.formatChoice);
      const result = await api<{ drafts: Draft[] }>(`/briefs/${state.selectedBrief.id}/drafts${params}`, { method: "POST" });
      state.setDrafts(result.drafts);
      state.setSelectedDraft(result.drafts[0] ?? null);
      state.setActiveView("studio");
      await options.refreshProductSurfaces();
      await options.refreshCurrentWorkspaceState();
      state.setNotice(formatChoiceNotice(state.formatChoice));
    } finally {
      state.setBusy(false);
    }
  }

  async function regenerateSelectedDraft() {
    if (!state.selectedDraft) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      const result = await api<{ drafts: Draft[] }>(`/drafts/${state.selectedDraft.id}/regenerate`, { method: "POST" });
      state.setDrafts(result.drafts);
      state.setSelectedDraft(result.drafts[0] ?? null);
      await options.refreshProductSurfaces();
      state.setNotice("Drafts regenerated from the same brief and adapter.");
    } finally {
      state.setBusy(false);
    }
  }

  async function approveDraft() {
    if (!state.selectedDraft) return;
    if (!options.requirePermission(options.canReviewContent, options.reviewPermissionMessage)) return;
    state.setBusy(true);
    try {
      await api(`/drafts/${state.selectedDraft.id}/approve`, {
        method: "POST",
        body: JSON.stringify({
          edited_body: state.editedBody,
          reason: state.reviewReason || "Approved in review desk",
        }),
      });
      const updated = await api<Draft>(`/drafts/${state.selectedDraft.id}`);
      const pkg = await api<ReviewerPackage>(`/drafts/${state.selectedDraft.id}/reviewer-package`);
      state.setSelectedDraft(updated);
      state.setReviewPackage(pkg);
      state.setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await options.refreshCalendar();
      await options.refreshMemoryAndAnalytics();
      await options.refreshProductSurfaces();
      await options.refreshCurrentWorkspaceState();
      state.setNotice(updated.status === "pending_approval" ? "Approval recorded. More reviewer approval is required." : "Approved and stored in memory.");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Approval failed.");
    } finally {
      state.setBusy(false);
    }
  }

  async function rejectDraft() {
    if (!state.selectedDraft) return;
    if (!options.requirePermission(options.canReviewContent, options.reviewPermissionMessage)) return;
    state.setBusy(true);
    try {
      await api(`/drafts/${state.selectedDraft.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ edited_body: state.editedBody, reason: state.reviewReason }),
      });
      const updated = await api<Draft>(`/drafts/${state.selectedDraft.id}`);
      state.setSelectedDraft(updated);
      state.setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await options.refreshProductSurfaces();
      state.setNotice("Rejected with review signal.");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Rejection failed.");
    } finally {
      state.setBusy(false);
    }
  }

  async function saveDraftEdit() {
    if (!state.selectedDraft) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      const updated = await api<Draft>(`/drafts/${state.selectedDraft.id}`, {
        method: "PATCH",
        body: JSON.stringify({ body: state.editedBody }),
      });
      state.setSelectedDraft(updated);
      state.setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await options.refreshProductSurfaces();
      state.setNotice("Draft edit saved and review checks refreshed.");
    } finally {
      state.setBusy(false);
    }
  }

  async function exportDraft() {
    if (!state.selectedDraft) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api(`/drafts/${state.selectedDraft.id}/export`, { method: "POST" });
      let copied = false;
      try {
        await navigator.clipboard?.writeText(state.editedBody);
        copied = true;
      } catch {
        copied = false;
      }
      const updated = await api<Draft>(`/drafts/${state.selectedDraft.id}`);
      state.setSelectedDraft(updated);
      state.setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await options.refreshCalendar();
      await options.refreshMemoryAndAnalytics();
      await options.refreshProductSurfaces();
      state.setNotice(copied ? "Exported and copied." : "Exported. Clipboard permission was unavailable.");
    } finally {
      state.setBusy(false);
    }
  }

  async function scheduleDraft() {
    if (!state.selectedDraft || !state.scheduleFor) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api(`/drafts/${state.selectedDraft.id}/schedule`, {
        method: "POST",
        body: JSON.stringify({
          scheduled_for: new Date(state.scheduleFor).toISOString(),
          reason: state.reviewReason || "Manual queue intent",
        }),
      });
      const updated = await api<Draft>(`/drafts/${state.selectedDraft.id}`);
      state.setSelectedDraft(updated);
      state.setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await options.refreshCalendar();
      await options.refreshProductSurfaces();
      state.setNotice("Scheduled intent saved to the queue.");
    } finally {
      state.setBusy(false);
    }
  }

  async function publishDraftToLinkedin() {
    if (!state.selectedDraft || !state.linkedinIntegration) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      const result = await api<PublishResult>(`/drafts/${state.selectedDraft.id}/publish/linkedin`, {
        method: "POST",
        body: JSON.stringify({
          page_urn: state.linkedinIntegration.selected_page_urn || null,
          page_name: state.linkedinIntegration.selected_page_name || null,
          reason: state.reviewReason || "Publish approved LinkedIn post",
        }),
      });
      const updated = await api<Draft>(`/drafts/${state.selectedDraft.id}`);
      state.setSelectedDraft(updated);
      state.setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await options.refreshCalendar();
      await options.refreshMemoryAndAnalytics();
      await options.refreshProductSurfaces();
      state.setNotice(
        result.status === "published"
          ? `Published to ${result.page_name || result.page_urn}.`
          : result.failure_reason || "Publishing failed; approved content was preserved.",
      );
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Publishing failed.");
    } finally {
      state.setBusy(false);
    }
  }

  return {
    approveDraft,
    createBrief,
    exportDraft,
    generateDraftsFromBrief,
    generateOpportunities,
    publishDraftToLinkedin,
    regenerateSelectedDraft,
    rejectDraft,
    saveDraftEdit,
    scheduleDraft,
    selectContentFormat,
  };
}
