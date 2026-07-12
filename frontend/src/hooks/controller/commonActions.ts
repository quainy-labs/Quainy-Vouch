import type React from "react";
import { api, AUTH_TOKEN_KEY } from "../../lib/api";
import {
  aiProviderSettingsForm,
  approvalPolicyForm,
  bootstrapFromCurrentWorkspace,
  emptyAuthForm,
  setupFromBootstrap,
  sortOpportunities,
  validateAuthForm,
} from "../../lib/forms";
import type {
  AIProviderSettings,
  AnalyticsDashboard,
  ApprovalPolicy,
  AuthResponse,
  BackgroundJob,
  CalendarEvent,
  ContentArtifact,
  ContentBrief,
  CurrentWorkspace,
  Draft,
  KnowledgeReadiness,
  LinkedInIntegration,
  Opportunity,
  PostMemory,
  PreferenceSuggestion,
  StrategyDashboard,
  TrendSignal,
  WorkspaceUser,
} from "../../types";
import { clearStudioSelection, loadStudioSection, loadStudioSelection, loadWorkspaceView } from "../../lib/studioSelection";
import type { WorkspaceControllerState } from "./useWorkspaceControllerState";

export function createCommonActions(state: WorkspaceControllerState) {
  async function loadWorkspace() {
    state.setBootstrapError("");
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
      state.setAuthRequired(true);
      state.setBootstrap(null);
      return;
    }
    try {
      state.setAuthRequired(false);
      const current = await api<CurrentWorkspace>("/me");
      const opportunities = await api<Opportunity[]>(`/organizations/${current.organization.id}/opportunities`);
      const data = bootstrapFromCurrentWorkspace(current, opportunities);
      state.setCurrentUser(current.user);
      state.setOnboarding(current.onboarding);
      state.setBootstrap(data);
      state.setSetupForm(setupFromBootstrap(data));
      state.setOpportunities(sortOpportunities(data.opportunities));
      state.setVisibleOpportunityCount(12);
      state.setActiveView(loadWorkspaceView(data.organization.id) ?? "studio");
      await loadWorkspaceResources(data.organization.id);
      await restoreStudioSelection(data.organization.id);
    } catch (error) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      state.setAuthRequired(true);
      state.setBootstrap(null);
      state.setBootstrapError(error instanceof Error ? error.message : "Could not load your workspace.");
    }
  }

  async function loadWorkspaceResources(organizationId: string) {
    await Promise.allSettled([
      api<Draft[]>(`/organizations/${organizationId}/calendar`).then(state.setCalendarItems),
      api<LinkedInIntegration>(`/organizations/${organizationId}/linkedin-integration`).then(state.setLinkedinIntegration),
      api<KnowledgeReadiness>(`/organizations/${organizationId}/knowledge-readiness`).then(state.setKnowledgeReadiness),
      api<PostMemory[]>(`/organizations/${organizationId}/memory`).then((memory) => {
        state.setMemoryItems(memory);
        if (memory.length > 0) {
          state.setMetricsForm((current) => ({ ...current, memory_id: memory[0].id }));
        }
      }),
      api<AnalyticsDashboard>(`/organizations/${organizationId}/analytics`).then(state.setAnalyticsDashboard),
      api<ContentArtifact[]>(`/organizations/${organizationId}/content-artifacts`).then(state.setContentArtifacts),
      api<StrategyDashboard>(`/organizations/${organizationId}/strategy`).then(state.setStrategyDashboard),
      api<BackgroundJob[]>(`/organizations/${organizationId}/jobs`).then(state.setJobs),
      api<WorkspaceUser[]>(`/organizations/${organizationId}/users`).then(state.setUsers),
      api<ApprovalPolicy>(`/organizations/${organizationId}/approval-policy`).then((policy) => {
        state.setApprovalPolicy(policy);
        state.setApprovalPolicyDraft(approvalPolicyForm(policy));
      }),
      api<AIProviderSettings>(`/organizations/${organizationId}/ai-provider-settings`).then((settings) => {
        state.setAiProviderSettings(settings);
        state.setAiProviderDraft(aiProviderSettingsForm(settings));
      }),
      api<PreferenceSuggestion[]>(`/organizations/${organizationId}/preference-suggestions`).then(state.setPreferenceSuggestions),
      api<CalendarEvent[]>(`/organizations/${organizationId}/calendar-events`).then(state.setCalendarEvents),
      api<TrendSignal[]>(`/organizations/${organizationId}/trend-signals`).then(state.setTrendSignals),
    ]);
  }

  async function restoreStudioSelection(organizationId: string) {
    const selection = loadStudioSelection(organizationId);
    const savedSection = loadStudioSection(organizationId);
    if (!selection) {
      if (savedSection) {
        state.setStudioSectionRequest({ section: savedSection, requestedAt: Date.now() });
      }
      return;
    }
    try {
      state.setReviewPackage(null);
      state.setEditedBody("");
      state.setReviewReason("");
      state.setScheduleFor("");

      if (selection.kind === "opportunity") {
        const opportunity = await api<Opportunity>(`/opportunities/${selection.id}`);
        if (opportunity.organization_id !== organizationId || opportunity.status === "dismissed") {
          clearStudioSelection(organizationId);
          return;
        }
        state.setOpportunities((current) => {
          const opportunityIds = new Set(current.map((item) => item.id));
          return opportunityIds.has(opportunity.id) ? current : sortOpportunities([opportunity, ...current]);
        });
        state.setSelectedOpportunity(opportunity);
        state.setSelectedBrief(null);
        state.setDrafts([]);
        state.setSelectedDraft(null);
        state.setStudioSectionRequest({ section: savedSection ?? "opportunities", requestedAt: Date.now() });
        return;
      }

      if (selection.kind === "brief") {
        const brief = await api<ContentBrief>(`/briefs/${selection.id}`);
        if (brief.organization_id !== organizationId) {
          clearStudioSelection(organizationId);
          return;
        }
        const opportunity = await api<Opportunity>(`/opportunities/${brief.opportunity_id}`);
        state.setSelectedOpportunity(opportunity);
        state.setSelectedBrief(brief);
        state.setDrafts([]);
        state.setSelectedDraft(null);
        state.setStudioSectionRequest({ section: savedSection ?? "brief", requestedAt: Date.now() });
        return;
      }

      const draft = await api<Draft>(`/drafts/${selection.id}`);
      if (draft.organization_id !== organizationId) {
        clearStudioSelection(organizationId);
        return;
      }
      const brief = await api<ContentBrief>(`/briefs/${draft.content_brief_id}`);
      const opportunity = await api<Opportunity>(`/opportunities/${brief.opportunity_id}`);
      const restoredDrafts = selection.draft_ids?.length ? await Promise.all(selection.draft_ids.map((draftId) => api<Draft>(`/drafts/${draftId}`))) : [draft];
      const validDrafts = restoredDrafts.filter((item) => item.organization_id === organizationId && item.content_brief_id === draft.content_brief_id);
      const orderedDrafts = validDrafts.some((item) => item.id === draft.id) ? validDrafts : [draft, ...validDrafts];
      state.setSelectedOpportunity(opportunity);
      state.setSelectedBrief(brief);
      state.setDrafts(orderedDrafts);
      state.setSelectedDraft(draft);
      state.setStudioSectionRequest({ section: savedSection ?? "drafts", requestedAt: Date.now() });
    } catch {
      clearStudioSelection(organizationId);
    }
  }

  async function submitAuth(event: React.FormEvent) {
    event.preventDefault();
    const authForm = state.authMode === "signup" ? state.signupAuthForm : state.loginAuthForm;
    const errors = validateAuthForm(authForm, state.authMode);
    state.setAuthErrors(errors);
    if (errors.length > 0) return;
    state.setBusy(true);
    state.setBootstrapError("");
    try {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      const response =
        state.authMode === "signup"
          ? await api<AuthResponse>("/auth/signup", {
              method: "POST",
              body: JSON.stringify({
                name: authForm.name,
                email: authForm.email,
                password: authForm.password,
                organization_name: authForm.organization_name,
                website_url: authForm.website_url || null,
                industry: authForm.industry || null,
                description: authForm.description || null,
                audience_summary: authForm.audience_summary || null,
                default_timezone: authForm.default_timezone || "UTC",
              }),
            })
          : await api<AuthResponse>("/auth/login", {
              method: "POST",
              body: JSON.stringify({
                email: authForm.email,
                password: authForm.password,
              }),
            });
      localStorage.setItem(AUTH_TOKEN_KEY, response.token);
      state.setAuthRequired(false);
      const opportunities = await api<Opportunity[]>(`/organizations/${response.workspace.organization.id}/opportunities`);
      const data = bootstrapFromCurrentWorkspace(response.workspace, opportunities);
      state.setCurrentUser(response.workspace.user);
      state.setOnboarding(response.workspace.onboarding);
      state.setBootstrap(data);
      state.setSetupForm(setupFromBootstrap(data));
      state.setOpportunities(sortOpportunities(opportunities));
      state.setVisibleOpportunityCount(12);
      state.setActiveView(loadWorkspaceView(response.workspace.organization.id) ?? (response.workspace.sources.length > 0 ? "studio" : "sources"));
      await loadWorkspaceResources(response.workspace.organization.id);
      await restoreStudioSelection(response.workspace.organization.id);
      state.setSignupAuthForm(emptyAuthForm);
      state.setLoginAuthForm(emptyAuthForm);
      state.setAuthErrors([]);
      state.setBootstrapError("");
      state.setNotice(state.authMode === "signup" ? "Organization created. Add your first approved source when you are ready." : "Welcome back.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Authentication failed.";
      state.setBootstrapError(message);
      state.setAuthErrors(message.split("\n"));
    } finally {
      state.setBusy(false);
    }
  }

  function signOut() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    state.setCurrentUser(null);
    state.setOnboarding(null);
    state.setBootstrap(null);
    state.setJobs([]);
    state.setSignupAuthForm(emptyAuthForm);
    state.setLoginAuthForm(emptyAuthForm);
    state.setAuthErrors([]);
    state.setBootstrapError("");
    state.setAuthMode("login");
    state.setAuthRequired(true);
    state.setNotice("");
  }

  async function refreshProductSurfaces(organizationId = state.bootstrap?.organization.id) {
    if (!organizationId) return;
    await Promise.allSettled([
      api<ContentArtifact[]>(`/organizations/${organizationId}/content-artifacts`).then(state.setContentArtifacts),
      api<StrategyDashboard>(`/organizations/${organizationId}/strategy`).then(state.setStrategyDashboard),
      api<BackgroundJob[]>(`/organizations/${organizationId}/jobs`).then(state.setJobs),
    ]);
  }

  async function refreshKnowledgeReadiness(organizationId = state.bootstrap?.organization.id) {
    if (!organizationId) return;
    state.setKnowledgeReadiness(await api<KnowledgeReadiness>(`/organizations/${organizationId}/knowledge-readiness`));
  }

  async function refreshJobs(organizationId = state.bootstrap?.organization.id) {
    if (!organizationId) return;
    state.setJobs(await api<BackgroundJob[]>(`/organizations/${organizationId}/jobs`));
  }

  async function refreshCurrentWorkspaceState() {
    const current = await api<CurrentWorkspace>("/me");
    state.setCurrentUser(current.user);
    state.setOnboarding(current.onboarding);
    return current;
  }

  function requirePermission(allowed: boolean, message: string): boolean {
    if (allowed) return true;
    state.setNotice(message);
    return false;
  }

  return {
    loadWorkspace,
    submitAuth,
    signOut,
    refreshProductSurfaces,
    refreshKnowledgeReadiness,
    refreshJobs,
    refreshCurrentWorkspaceState,
    requirePermission,
  };
}
