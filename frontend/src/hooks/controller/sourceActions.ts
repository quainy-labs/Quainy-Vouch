import { api } from "../../lib/api";
import { emptySourceFormFor, validateSourceForm } from "../../lib/forms";
import { sourceFormFromFile } from "../../lib/sourceForms";
import type { Source, SourceDetail, SourceForm } from "../../types";
import type { WorkspaceControllerState } from "./useWorkspaceControllerState";

type SourceActionsOptions = {
  canEditKnowledge: boolean;
  knowledgePermissionMessage: string;
  requirePermission: (allowed: boolean, message: string) => boolean;
  refreshCurrentWorkspaceState: () => Promise<unknown>;
  refreshKnowledgeReadiness: (organizationId?: string) => Promise<void>;
  refreshProductSurfaces: (organizationId?: string) => Promise<void>;
};

export function createSourceActions(state: WorkspaceControllerState, options: SourceActionsOptions) {
  function clearContentAfterSourceChange(message: string) {
    state.setOpportunities([]);
    state.setVisibleOpportunityCount(12);
    state.setOpportunityMessage(message);
    state.setSelectedOpportunity(null);
    state.setSelectedBrief(null);
    state.setDrafts([]);
    state.setSelectedDraft(null);
  }

  async function refreshSources(selectedId?: string) {
    if (!state.bootstrap) return;
    const sources = await api<Source[]>(`/organizations/${state.bootstrap.organization.id}/sources`);
    state.setBootstrap({ ...state.bootstrap, sources });
    await options.refreshKnowledgeReadiness(state.bootstrap.organization.id);
    if (selectedId) {
      state.setSelectedSourceId(selectedId);
      state.setSourceDetail(await api<SourceDetail>(`/sources/${selectedId}`));
    }
  }

  function commitSourceForm(nextForm: SourceForm) {
    state.setSourceForm(nextForm);
    state.setSourceDraftsByType((current) => ({ ...current, [nextForm.source_type]: nextForm }));
    state.setSourceErrors([]);
  }

  function selectSourceType(sourceType: string) {
    state.setSourceDraftsByType((current) => ({ ...current, [state.sourceForm.source_type]: state.sourceForm }));
    state.setSourceForm(state.sourceDraftsByType[sourceType] ?? emptySourceFormFor(sourceType));
  }

  async function addSource() {
    if (!state.bootstrap) return;
    if (!options.requirePermission(options.canEditKnowledge, options.knowledgePermissionMessage)) return;
    const errors = validateSourceForm(state.sourceForm);
    state.setSourceErrors(errors);
    if (errors.length > 0) return;
    state.setBusy(true);
    try {
      const addedSourceType = state.sourceForm.source_type;
      const source = await api<Source>(`/organizations/${state.bootstrap.organization.id}/sources`, {
        method: "POST",
        body: JSON.stringify({
          source_type: state.sourceForm.source_type,
          title: state.sourceForm.title,
          uri: state.sourceForm.uri || null,
          raw_text: state.sourceForm.raw_text,
          approval_status: state.sourceForm.approval_status,
          freshness_days: Number(state.sourceForm.freshness_days) || 180,
        }),
      });
      const clearedForm = emptySourceFormFor(addedSourceType);
      state.setSourceForm(clearedForm);
      state.setSourceDraftsByType((current) => ({ ...current, [addedSourceType]: clearedForm }));
      await refreshSources(source.id);
      clearContentAfterSourceChange("Source library changed. Generate opportunities again to use the latest approved knowledge.");
      await options.refreshProductSurfaces();
      await options.refreshCurrentWorkspaceState();
      state.setSourceErrors([]);
      state.setNotice("Source added, ingested, and ready for opportunity generation.");
    } catch (error) {
      state.setSourceErrors((error instanceof Error ? error.message : "Source could not be added.").split("\n"));
      state.setNotice(error instanceof Error ? error.message : "Source could not be added.");
    } finally {
      state.setBusy(false);
    }
  }

  async function updateSourceStatus(sourceId: string, approvalStatus: string) {
    if (!options.requirePermission(options.canEditKnowledge, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api<Source>(`/sources/${sourceId}`, {
        method: "PATCH",
        body: JSON.stringify({ approval_status: approvalStatus }),
      });
      await refreshSources(sourceId);
      clearContentAfterSourceChange("Source availability changed. Generate opportunities again so disabled or archived sources are excluded.");
      await options.refreshProductSurfaces();
      state.setNotice("");
    } finally {
      state.setBusy(false);
    }
  }

  async function refreshSource(sourceId: string) {
    if (!options.requirePermission(options.canEditKnowledge, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api(`/sources/${sourceId}/refresh`, { method: "POST" });
      await refreshSources(sourceId);
      clearContentAfterSourceChange("Source was re-ingested. Generate opportunities again to use the refreshed evidence.");
      await options.refreshProductSurfaces();
      state.setNotice("");
    } finally {
      state.setBusy(false);
    }
  }

  async function updateSource(
    sourceId: string,
    payload: { title?: string; uri?: string | null; raw_text?: string; approval_status?: string; freshness_days?: number },
  ) {
    if (!options.requirePermission(options.canEditKnowledge, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api<Source>(`/sources/${sourceId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      await refreshSources(sourceId);
      clearContentAfterSourceChange("Source changed. Generate opportunities again to use the latest approved knowledge.");
      await options.refreshProductSurfaces();
      state.setNotice("");
    } finally {
      state.setBusy(false);
    }
  }

  async function handleReadinessAction(action: string) {
    if (action === "settings") {
      state.setActiveView("settings");
      return;
    }
    if (action === "refresh_sources") {
      state.setActiveView("sources");
      state.setNotice("Select a stale source and refresh it after confirming the source is still current.");
      return;
    }
    state.setActiveView("sources");
  }

  async function handleSourceFile(file: File | undefined) {
    if (!file) return;
    commitSourceForm(await sourceFormFromFile(file, state.sourceForm));
  }

  return {
    addSource,
    commitSourceForm,
    handleReadinessAction,
    handleSourceFile,
    refreshSource,
    refreshSources,
    selectSourceType,
    updateSource,
    updateSourceStatus,
  };
}
