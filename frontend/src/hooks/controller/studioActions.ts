import { api } from "../../lib/api";
import { canBuildBrief, formatChoiceLabel, formatChoiceNotice, formatChoiceParams, sortOpportunities } from "../../lib/forms";
import { clearStudioSelection, saveStudioSelection, saveWorkspaceView } from "../../lib/studioSelection";
import type { ContentArtifact, ContentBrief, Draft, FormatChoice, Opportunity, PublishResult, ReviewerPackage } from "../../types";
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
  function setWorkspaceViewToStudio(organizationId: string) {
    state.setActiveView("studio");
    saveWorkspaceView(organizationId, "studio");
  }

  function saveDraftSelection(selectedDraft: Draft, drafts = state.drafts) {
    saveStudioSelection(selectedDraft.organization_id, {
      kind: "draft",
      id: selectedDraft.id,
      draft_ids: drafts.map((draft) => draft.id),
    });
  }

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

  function selectDraft(draft: Draft) {
    state.setSelectedDraft(draft);
    saveDraftSelection(draft);
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
      const generatedIds = new Set(result.opportunities.map((opportunity) => opportunity.id));
      const ranked = sortOpportunities([...result.opportunities, ...state.opportunities.filter((opportunity) => !generatedIds.has(opportunity.id))]);
      const rankedGenerated = sortOpportunities(result.opportunities);
      state.setOpportunities(ranked);
      state.setVisibleOpportunityCount(12);
      state.setOpportunityMessage(result.message ?? (result.opportunities.length ? "Opportunities generated from approved source context." : ""));
      const selected = rankedGenerated[0] ?? ranked[0] ?? null;
      state.setSelectedOpportunity(selected);
      resetSelectedWork();
      if (selected) {
        saveStudioSelection(selected.organization_id, { kind: "opportunity", id: selected.id });
      }
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
      setWorkspaceViewToStudio(brief.organization_id);
      saveStudioSelection(brief.organization_id, { kind: "brief", id: brief.id });
      await options.refreshProductSurfaces();
      await options.refreshCurrentWorkspaceState();
      state.setNotice("Brief created from approved source context.");
    } finally {
      state.setBusy(false);
    }
  }

  async function dismissOpportunity(opportunity: Opportunity) {
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      const shouldClearSelection = state.selectedOpportunity?.id === opportunity.id || state.selectedBrief?.opportunity_id === opportunity.id;
      await api<Opportunity>(`/opportunities/${opportunity.id}/dismiss`, {
        method: "POST",
        body: JSON.stringify({ reason: "Marked not relevant from opportunities card." }),
      });
      const remaining = sortOpportunities(state.opportunities.filter((item) => item.id !== opportunity.id));
      state.setOpportunities(remaining);
      state.setSelectedOpportunity((selected) => (selected?.id === opportunity.id ? (remaining[0] ?? null) : selected));
      if (state.selectedBrief?.opportunity_id === opportunity.id) {
        resetSelectedWork();
      }
      if (shouldClearSelection) {
        clearStudioSelection(opportunity.organization_id);
      }
      await options.refreshProductSurfaces();
      await options.refreshCurrentWorkspaceState();
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Could not mark opportunity as not relevant.");
    } finally {
      state.setBusy(false);
    }
  }

  async function openLibraryArtifact(artifact: ContentArtifact) {
    if (state.busy) return;
    state.setBusy(true);
    try {
      state.setReviewPackage(null);
      state.setEditedBody("");
      state.setReviewReason("");
      state.setScheduleFor("");

      if (artifact.kind === "opportunity") {
        const opportunity = await api<Opportunity>(`/opportunities/${artifact.id}`);
        if (opportunity.status === "dismissed") {
          state.setNotice("Not relevant opportunities stay in Library and cannot be opened in Studio.");
          return;
        }
        const opportunityIds = new Set(state.opportunities.map((item) => item.id));
        if (!opportunityIds.has(opportunity.id)) {
          state.setOpportunities(sortOpportunities([opportunity, ...state.opportunities]));
        }
        state.setSelectedOpportunity(opportunity);
        state.setSelectedBrief(null);
        state.setDrafts([]);
        state.setSelectedDraft(null);
        state.setStudioSectionRequest({ section: "opportunities", requestedAt: Date.now() });
        setWorkspaceViewToStudio(opportunity.organization_id);
        saveStudioSelection(opportunity.organization_id, { kind: "opportunity", id: opportunity.id });
        state.setNotice("Opened opportunity from library.");
        return;
      }

      if (artifact.kind === "brief") {
        const brief = await api<ContentBrief>(`/briefs/${artifact.id}`);
        const opportunity = await api<Opportunity>(`/opportunities/${brief.opportunity_id}`);
        state.setSelectedOpportunity(opportunity);
        state.setSelectedBrief(brief);
        state.setDrafts([]);
        state.setSelectedDraft(null);
        state.setStudioSectionRequest({ section: "brief", requestedAt: Date.now() });
        setWorkspaceViewToStudio(brief.organization_id);
        saveStudioSelection(brief.organization_id, { kind: "brief", id: brief.id });
        state.setNotice("Opened brief from library.");
        return;
      }

      if (artifact.kind === "draft") {
        const draft = await api<Draft>(`/drafts/${artifact.id}`);
        const brief = await api<ContentBrief>(`/briefs/${draft.content_brief_id}`);
        const opportunity = await api<Opportunity>(`/opportunities/${brief.opportunity_id}`);
        state.setSelectedOpportunity(opportunity);
        state.setSelectedBrief(brief);
        state.setDrafts([draft]);
        state.setSelectedDraft(draft);
        state.setStudioSectionRequest({ section: "drafts", requestedAt: Date.now() });
        setWorkspaceViewToStudio(draft.organization_id);
        saveDraftSelection(draft, [draft]);
        state.setNotice("Opened draft from library.");
        return;
      }

      state.setNotice("This library item is available as reference memory, but it does not open in Studio yet.");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Could not open the library item.");
    } finally {
      state.setBusy(false);
    }
  }

  async function generateDraftsFromBrief() {
    if (!state.selectedBrief) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    if (state.formatChoice === "reddit_post" && !state.redditCommunity.trim()) {
      state.setNotice("Add the target Reddit community before generating Reddit drafts.");
      return;
    }
    state.setBusy(true);
    try {
      const params = formatChoiceParams(state.formatChoice, {
        redditCommunity: state.redditCommunity,
      });
      const result = await api<{ drafts: Draft[] }>(`/briefs/${state.selectedBrief.id}/drafts${params}`, { method: "POST" });
      state.setDrafts(result.drafts);
      state.setSelectedDraft(result.drafts[0] ?? null);
      setWorkspaceViewToStudio(state.selectedBrief.organization_id);
      if (result.drafts[0]) {
        saveDraftSelection(result.drafts[0], result.drafts);
      } else {
        saveStudioSelection(state.selectedBrief.organization_id, { kind: "brief", id: state.selectedBrief.id });
      }
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
      if (result.drafts[0]) {
        saveDraftSelection(result.drafts[0], result.drafts);
      }
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
    dismissOpportunity,
    exportDraft,
    generateDraftsFromBrief,
    generateOpportunities,
    openLibraryArtifact,
    publishDraftToLinkedin,
    regenerateSelectedDraft,
    rejectDraft,
    saveDraftEdit,
    scheduleDraft,
    selectContentFormat,
    selectDraft,
  };
}
