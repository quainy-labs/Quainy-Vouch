import { useEffect } from "react";
import type { ComponentProps } from "react";
import type { AuthScreen } from "../components/auth/AuthScreen";
import type { LoadingScreen } from "../components/layout/LoadingScreen";
import type { WorkspaceShell } from "../components/layout/WorkspaceShell";
import { api } from "../lib/api";
import { saveStudioSection, saveWorkspaceView } from "../lib/studioSelection";
import { buildWorkspaceModel } from "../lib/workspaceModel";
import { createCalendarStrategyActions } from "./controller/calendarStrategyActions";
import { createCommonActions } from "./controller/commonActions";
import { createSettingsActions } from "./controller/settingsActions";
import { createSourceActions } from "./controller/sourceActions";
import { createStudioActions } from "./controller/studioActions";
import { useWorkspaceControllerState } from "./controller/useWorkspaceControllerState";

type AuthScreenProps = ComponentProps<typeof AuthScreen>;
type LoadingScreenProps = ComponentProps<typeof LoadingScreen>;
type WorkspaceShellProps = ComponentProps<typeof WorkspaceShell>;

type QuainyWorkspaceController =
  | { screen: "auth"; authProps: AuthScreenProps }
  | { screen: "loading"; loadingProps: LoadingScreenProps }
  | { screen: "workspace"; workspaceProps: WorkspaceShellProps };

const OAUTH_RESULT_STORAGE_KEY = "quainy_vouch_oauth_result";

export function useQuainyWorkspaceController(): QuainyWorkspaceController {
  const state = useWorkspaceControllerState();
  const commonActions = createCommonActions(state);

  useEffect(() => {
    async function initializeWorkspace() {
      await commonActions.loadWorkspace();
      const params = new URLSearchParams(window.location.search);
      const oauthProvider = params.get("oauth_provider");
      const oauthStatus = params.get("oauth_status");
      const oauthMessage = params.get("oauth_message");
      if (!oauthProvider || !oauthStatus) return;
      state.setActiveView("settings");
      state.setSetupSection("linkedin");
      state.setNotice(oauthMessage || `${oauthProvider} ${oauthStatus}.`);
      localStorage.setItem(
        OAUTH_RESULT_STORAGE_KEY,
        JSON.stringify({ provider: oauthProvider, status: oauthStatus, message: oauthMessage, completedAt: Date.now() }),
      );
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    void initializeWorkspace();
  }, []);

  useEffect(() => {
    function handleOAuthResult(event: StorageEvent) {
      if (event.key !== OAUTH_RESULT_STORAGE_KEY) return;
      let message = "Publishing connection updated.";
      try {
        const payload = JSON.parse(event.newValue || "{}") as { message?: string; provider?: string; status?: string };
        message = payload.message || (payload.provider && payload.status ? `${payload.provider} ${payload.status}.` : message);
      } catch {
        // Ignore malformed cross-tab notifications; the refresh is still useful.
      }
      state.setActiveView("settings");
      state.setSetupSection("linkedin");
      state.setNotice(message);
      void commonActions.refreshPublishingConnections();
    }

    window.addEventListener("storage", handleOAuthResult);
    return () => window.removeEventListener("storage", handleOAuthResult);
  }, [state.bootstrap?.organization.id]);

  useEffect(() => {
    function refreshPublishingOnReturn() {
      if (document.visibilityState !== "visible") return;
      void commonActions.refreshPublishingConnections();
    }

    window.addEventListener("focus", refreshPublishingOnReturn);
    document.addEventListener("visibilitychange", refreshPublishingOnReturn);
    return () => {
      window.removeEventListener("focus", refreshPublishingOnReturn);
      document.removeEventListener("visibilitychange", refreshPublishingOnReturn);
    };
  }, [state.bootstrap?.organization.id]);

  if (state.authRequired && !state.bootstrap) {
    return {
      screen: "auth",
      authProps: {
        authMode: state.authMode,
        authForm: state.authMode === "signup" ? state.signupAuthForm : state.loginAuthForm,
        authErrors: state.authErrors,
        bootstrapError: state.bootstrapError,
        busy: state.busy,
        onAuthModeChange: (mode) => {
          state.setAuthMode(mode);
          state.setAuthErrors([]);
          state.setBootstrapError("");
        },
        onAuthFormChange: state.authMode === "signup" ? state.setSignupAuthForm : state.setLoginAuthForm,
        onSubmit: commonActions.submitAuth,
      },
    };
  }

  if (!state.bootstrap) {
    return { screen: "loading", loadingProps: { error: state.bootstrapError, onRetry: commonActions.loadWorkspace } };
  }

  const model = buildWorkspaceModel({
    bootstrap: state.bootstrap,
    knowledgeReadiness: state.knowledgeReadiness,
    currentUser: state.currentUser,
    reviewPackage: state.reviewPackage,
    selectedDraft: state.selectedDraft,
    busy: state.busy,
    linkedinIntegration: state.linkedinIntegration,
    publishingConnections: state.publishingConnections,
    jobs: state.jobs,
    drafts: state.drafts,
    memoryItems: state.memoryItems,
    calendarItems: state.calendarItems,
    analyticsDashboard: state.analyticsDashboard,
    users: state.users,
    activeView: state.activeView,
    contentArtifacts: state.contentArtifacts,
    libraryStatusFilter: state.libraryStatusFilter,
    libraryPlatformFilter: state.libraryPlatformFilter,
    opportunities: state.opportunities,
    selectedOpportunity: state.selectedOpportunity,
    visibleOpportunityCount: state.visibleOpportunityCount,
  });

  const sourceActions = createSourceActions(state, {
    canEditKnowledge: model.canEditKnowledge,
    knowledgePermissionMessage: model.knowledgePermissionMessage,
    requirePermission: commonActions.requirePermission,
    refreshCurrentWorkspaceState: commonActions.refreshCurrentWorkspaceState,
    refreshKnowledgeReadiness: commonActions.refreshKnowledgeReadiness,
    refreshProductSurfaces: commonActions.refreshProductSurfaces,
  });

  const calendarStrategyActions = createCalendarStrategyActions(state, {
    canEditContent: model.canEditContent,
    canEditKnowledge: model.canEditKnowledge,
    knowledgePermissionMessage: model.knowledgePermissionMessage,
    requirePermission: commonActions.requirePermission,
    refreshProductSurfaces: commonActions.refreshProductSurfaces,
  });

  const studioActions = createStudioActions(state, {
    canEditContent: model.canEditContent,
    canReviewContent: model.canReviewContent,
    knowledgePermissionMessage: model.knowledgePermissionMessage,
    reviewPermissionMessage: model.reviewPermissionMessage,
    requirePermission: commonActions.requirePermission,
    refreshCalendar: calendarStrategyActions.refreshCalendar,
    refreshCurrentWorkspaceState: commonActions.refreshCurrentWorkspaceState,
    refreshMemoryAndAnalytics: calendarStrategyActions.refreshMemoryAndAnalytics,
    refreshProductSurfaces: commonActions.refreshProductSurfaces,
  });

  const settingsActions = createSettingsActions(state, {
    canManageWorkspace: model.canManageWorkspace,
    workspacePermissionMessage: model.workspacePermissionMessage,
    requirePermission: commonActions.requirePermission,
    refreshCurrentWorkspaceState: commonActions.refreshCurrentWorkspaceState,
    refreshKnowledgeReadiness: commonActions.refreshKnowledgeReadiness,
  });

  async function retryJob(jobId: string) {
    if (!commonActions.requirePermission(model.canEditContent, model.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await fetchJobRetry(jobId);
      await commonActions.refreshJobs();
      await commonActions.refreshProductSurfaces();
      await sourceActions.refreshSources();
      await calendarStrategyActions.refreshMemoryAndAnalytics();
      state.setNotice("Job retried successfully.");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Job retry failed.");
    } finally {
      state.setBusy(false);
    }
  }

  return {
    screen: "workspace",
    workspaceProps: {
      bootstrap: state.bootstrap,
      currentUser: state.currentUser,
      onboarding: state.onboarding,
      healthLabel: model.healthLabel,
      busy: state.busy,
      notice: state.notice,
      activeView: state.activeView,
      currentView: model.currentView,
      viewItems: model.viewItems,
      approvedSources: model.approvedSources,
      disabledSources: model.disabledSources,
      archivedSources: model.archivedSources,
      selectedSourceId: state.selectedSourceId,
      libraryMetrics: model.libraryMetrics,
      statusOptions: model.statusOptions,
      libraryStatusFilter: state.libraryStatusFilter,
      libraryPlatformFilter: state.libraryPlatformFilter,
      availableLibraryPlatforms: model.availableLibraryPlatforms,
      visibleContentArtifacts: model.visibleContentArtifacts,
      hasVisibleLibraryArtifacts: model.hasVisibleLibraryArtifacts,
      canManageWorkspace: model.canManageWorkspace,
      canEditKnowledge: model.canEditKnowledge,
      canEditContent: model.canEditContent,
      canReviewContent: model.canReviewContent,
      workspacePermissionMessage: model.workspacePermissionMessage,
      knowledgePermissionMessage: model.knowledgePermissionMessage,
      reviewPermissionMessage: model.reviewPermissionMessage,
      setupForm: state.setupForm,
      setupErrors: state.setupErrors,
      setupSection: state.setupSection,
      linkedinIntegration: state.linkedinIntegration,
      publishingConnections: state.publishingConnections,
      aiProviderSettings: state.aiProviderSettings,
      aiProviderDraft: state.aiProviderDraft,
      aiProviderTest: state.aiProviderTest,
      users: state.users,
      userForm: state.userForm,
      approvalPolicy: state.approvalPolicy,
      approvalPolicyDraft: state.approvalPolicyDraft,
      recentJobs: model.recentJobs,
      failedJobCount: model.failedJobCount,
      sourceErrors: state.sourceErrors,
      knowledgeReadiness: state.knowledgeReadiness,
      sourceForm: state.sourceForm,
      sourceDetail: state.sourceDetail,
      calendarItems: state.calendarItems,
      calendarEvents: state.calendarEvents,
      trendSignals: state.trendSignals,
      calendarEventForm: state.calendarEventForm,
      trendSignalForm: state.trendSignalForm,
      canApproveDraft: model.canApproveDraft,
      canExportDraft: model.canExportDraft,
      canScheduleDraft: model.canScheduleDraft,
      canAttemptLinkedinPublish: model.canAttemptLinkedinPublish,
      approvalBlocked: model.approvalBlocked,
      publishCapabilityText: model.publishCapabilityText,
      rankedOpportunities: model.rankedOpportunities,
      visibleOpportunities: model.visibleOpportunities,
      hiddenOpportunityCount: model.hiddenOpportunityCount,
      selectedOpportunity: state.selectedOpportunity,
      opportunityMessage: state.opportunityMessage,
      selectedBrief: state.selectedBrief,
      studioSectionRequest: state.studioSectionRequest,
      redditCommunity: state.redditCommunity,
      formatChoice: state.formatChoice,
      drafts: state.drafts,
      selectedDraft: state.selectedDraft,
      reviewPackage: state.reviewPackage,
      approvalProgress: model.approvalProgress,
      editedBody: state.editedBody,
      reviewReason: state.reviewReason,
      scheduleFor: state.scheduleFor,
      strategyDashboard: state.strategyDashboard,
      analyticsDashboard: state.analyticsDashboard,
      memoryItems: state.memoryItems,
      metricsForm: state.metricsForm,
      preferenceSuggestions: state.preferenceSuggestions,
      onSignOut: commonActions.signOut,
      onActiveViewChange: (view) => {
        state.setActiveView(view);
        if (state.bootstrap) {
          saveWorkspaceView(state.bootstrap.organization.id, view);
        }
      },
      onSkipProfile: settingsActions.skipProfileForNow,
      onSelectSource: state.setSelectedSourceId,
      onStatusFilterChange: state.setLibraryStatusFilter,
      onPlatformFilterChange: state.setLibraryPlatformFilter,
      onSelectDraft: studioActions.selectDraft,
      onStudioSectionChange: (section) => {
        if (state.bootstrap) {
          saveStudioSection(state.bootstrap.organization.id, section);
        }
      },
      onStudioSectionRequestHandled: () => state.setStudioSectionRequest(null),
      onSetupFormChange: state.setSetupForm,
      onSetupSectionChange: state.setSetupSection,
      onLinkedInIntegrationChange: state.setLinkedinIntegration,
      onAIProviderDraftChange: state.setAiProviderDraft,
      onUserFormChange: state.setUserForm,
      onApprovalPolicyDraftChange: state.setApprovalPolicyDraft,
      onSaveSetup: settingsActions.saveSetup,
      onSaveAIProviderSettings: settingsActions.saveAIProviderSettings,
      onTestAIProviderSettings: settingsActions.testAIProviderSettings,
      onAddUser: settingsActions.addUser,
      onUpdateUserRole: settingsActions.updateUserRole,
      onSaveApprovalPolicy: settingsActions.saveApprovalPolicy,
      onActivateOrganization: settingsActions.activateOrganization,
      onDeactivateOrganization: settingsActions.deactivateOrganization,
      onDeleteOrganization: settingsActions.deleteOrganization,
      onRetryJob: retryJob,
      onAddSource: sourceActions.addSource,
      onReadinessAction: sourceActions.handleReadinessAction,
      onSelectSourceType: sourceActions.selectSourceType,
      onCommitSourceForm: sourceActions.commitSourceForm,
      onSourceFile: sourceActions.handleSourceFile,
      onUpdateSourceStatus: sourceActions.updateSourceStatus,
      onUpdateSource: sourceActions.updateSource,
      onRefreshSource: sourceActions.refreshSource,
      onCalendarEventFormChange: state.setCalendarEventForm,
      onTrendSignalFormChange: state.setTrendSignalForm,
      onAddCalendarEvent: calendarStrategyActions.addCalendarEvent,
      onAddTrendSignal: calendarStrategyActions.addTrendSignal,
      onGenerateTrendOpportunities: calendarStrategyActions.generateTrendOpportunities,
      onGenerateOpportunities: studioActions.generateOpportunities,
      onCreateBrief: studioActions.createBrief,
      onDismissOpportunity: studioActions.dismissOpportunity,
      onOpenLibraryArtifact: studioActions.openLibraryArtifact,
      onShowMoreOpportunities: () => state.setVisibleOpportunityCount((current) => current + 12),
      onSelectContentFormat: studioActions.selectContentFormat,
      onRedditCommunityChange: state.setRedditCommunity,
      onGenerateDraftsFromBrief: studioActions.generateDraftsFromBrief,
      onEditedBodyChange: state.setEditedBody,
      onReviewReasonChange: state.setReviewReason,
      onSaveDraftEdit: studioActions.saveDraftEdit,
      onApproveDraft: studioActions.approveDraft,
      onRejectDraft: studioActions.rejectDraft,
      onExportDraft: studioActions.exportDraft,
      onPublishDraftToLinkedIn: studioActions.publishDraftToLinkedin,
      onRegenerateSelectedDraft: studioActions.regenerateSelectedDraft,
      onScheduleForChange: state.setScheduleFor,
      onScheduleDraft: studioActions.scheduleDraft,
      onMetricsFormChange: state.setMetricsForm,
      onImportAnalytics: calendarStrategyActions.importAnalytics,
      onSaveManualMetrics: calendarStrategyActions.saveManualMetrics,
      onGeneratePreferenceSuggestions: calendarStrategyActions.generatePreferenceSuggestions,
      onDecidePreferenceSuggestion: calendarStrategyActions.decidePreferenceSuggestion,
    },
  };
}

async function fetchJobRetry(jobId: string) {
  await api(`/jobs/${jobId}/retry`, { method: "POST" });
}
