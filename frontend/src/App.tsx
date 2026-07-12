import { useEffect, useState } from "react";
import type React from "react";
import { RefreshCcw } from "lucide-react";
import { AuthScreen } from "./components/auth/AuthScreen";
import { WorkspaceShell } from "./components/layout/WorkspaceShell";
import { api, AUTH_TOKEN_KEY } from "./lib/api";
import { buildWorkspaceModel } from "./lib/workspaceModel";

import type {
  Organization,
  Profile,
  Source,
  SourceDetail,
  KnowledgeReadiness,
  Opportunity,
  ContentBrief,
  Draft,
  LinkedInIntegration,
  PublishResult,
  PostMemory,
  AnalyticsDashboard,
  ContentArtifact,
  BackgroundJob,
  StrategyDashboard,
  WorkspaceUser,
  OnboardingState,
  ApprovalPolicy,
  ApprovalPolicyForm,
  AIProviderSettings,
  AIProviderConnectionTest,
  AIProviderSettingsForm,
  PreferenceSuggestion,
  CalendarEvent,
  TrendSignal,
  ReviewerPackage,
  Bootstrap,
  CurrentWorkspace,
  AuthResponse,
  AuthForm,
  SetupForm,
  SourceForm,
  MetricsForm,
  UserForm,
  CalendarEventForm,
  TrendSignalForm,
  FormatChoice,
  WorkspaceView,
  SetupSection,
  LibraryStatusFilter,
  LibraryPlatformFilter,
} from "./types";
import {
  textToList,
  validateAuthForm,
  validateSetupForm,
  validateSourceForm,
  formatChoiceParams,
  formatChoiceNotice,
  formatChoiceLabel,
  setupFromBootstrap,
  bootstrapFromCurrentWorkspace,
  emptySourceForm,
  emptySourceFormFor,
  emptyMetricsForm,
  emptyAuthForm,
  emptyUserForm,
  emptyCalendarEventForm,
  emptyTrendSignalForm,
  canBuildBrief,
  sortOpportunities,
  approvalPolicyForm,
  aiProviderSettingsForm,
  aiProviderPayload
} from "./lib/forms";

export default function App() {
  const [currentUser, setCurrentUser] = useState<WorkspaceUser | null>(null);
  const [onboarding, setOnboarding] = useState<OnboardingState | null>(null);
  const [authMode, setAuthMode] = useState<"signup" | "login">("signup");
  const [authForm, setAuthForm] = useState<AuthForm>(emptyAuthForm);
  const [authErrors, setAuthErrors] = useState<string[]>([]);
  const [authRequired, setAuthRequired] = useState(false);
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [bootstrapError, setBootstrapError] = useState("");
  const [setupForm, setSetupForm] = useState<SetupForm | null>(null);
  const [setupErrors, setSetupErrors] = useState<string[]>([]);
  const [sourceForm, setSourceForm] = useState<SourceForm>(emptySourceForm);
  const [sourceErrors, setSourceErrors] = useState<string[]>([]);
  const [sourceDraftsByType, setSourceDraftsByType] = useState<Record<string, SourceForm>>({});
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [sourceDetail, setSourceDetail] = useState<SourceDetail | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [visibleOpportunityCount, setVisibleOpportunityCount] = useState(12);
  const [opportunityMessage, setOpportunityMessage] = useState("");
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);
  const [selectedBrief, setSelectedBrief] = useState<ContentBrief | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<Draft | null>(null);
  const [reviewPackage, setReviewPackage] = useState<ReviewerPackage | null>(null);
  const [editedBody, setEditedBody] = useState("");
  const [reviewReason, setReviewReason] = useState("");
  const [scheduleFor, setScheduleFor] = useState("");
  const [calendarItems, setCalendarItems] = useState<Draft[]>([]);
  const [linkedinIntegration, setLinkedinIntegration] = useState<LinkedInIntegration | null>(null);
  const [knowledgeReadiness, setKnowledgeReadiness] = useState<KnowledgeReadiness | null>(null);
  const [memoryItems, setMemoryItems] = useState<PostMemory[]>([]);
  const [analyticsDashboard, setAnalyticsDashboard] = useState<AnalyticsDashboard | null>(null);
  const [contentArtifacts, setContentArtifacts] = useState<ContentArtifact[]>([]);
  const [strategyDashboard, setStrategyDashboard] = useState<StrategyDashboard | null>(null);
  const [jobs, setJobs] = useState<BackgroundJob[]>([]);
  const [metricsForm, setMetricsForm] = useState<MetricsForm>(emptyMetricsForm);
  const [users, setUsers] = useState<WorkspaceUser[]>([]);
  const [userForm, setUserForm] = useState<UserForm>(emptyUserForm);
  const [approvalPolicy, setApprovalPolicy] = useState<ApprovalPolicy | null>(null);
  const [approvalPolicyDraft, setApprovalPolicyDraft] = useState<ApprovalPolicyForm | null>(null);
  const [aiProviderSettings, setAiProviderSettings] = useState<AIProviderSettings | null>(null);
  const [aiProviderDraft, setAiProviderDraft] = useState<AIProviderSettingsForm | null>(null);
  const [aiProviderTest, setAiProviderTest] = useState<AIProviderConnectionTest | null>(null);
  const [preferenceSuggestions, setPreferenceSuggestions] = useState<PreferenceSuggestion[]>([]);
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [trendSignals, setTrendSignals] = useState<TrendSignal[]>([]);
  const [calendarEventForm, setCalendarEventForm] = useState<CalendarEventForm>(emptyCalendarEventForm);
  const [trendSignalForm, setTrendSignalForm] = useState<TrendSignalForm>(emptyTrendSignalForm);
  const [formatChoice, setFormatChoice] = useState<FormatChoice>("linkedin_company_post");
  const [activeView, setActiveView] = useState<WorkspaceView>("studio");
  const [setupSection, setSetupSection] = useState<SetupSection>("company");
  const [libraryStatusFilter, setLibraryStatusFilter] = useState<LibraryStatusFilter>("all");
  const [libraryPlatformFilter, setLibraryPlatformFilter] = useState<LibraryPlatformFilter>("all");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  async function loadWorkspace() {
    setBootstrapError("");
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
      setAuthRequired(true);
      setBootstrap(null);
      return;
    }
    try {
      setAuthRequired(false);
      const current = await api<CurrentWorkspace>("/me");
      const opportunities = await api<Opportunity[]>(`/organizations/${current.organization.id}/opportunities`);
      const data = bootstrapFromCurrentWorkspace(current, opportunities);
      setCurrentUser(current.user);
      setOnboarding(current.onboarding);
      setBootstrap(data);
      setSetupForm(setupFromBootstrap(data));
      setOpportunities(sortOpportunities(data.opportunities));
      setVisibleOpportunityCount(12);
      await Promise.allSettled([
        api<Draft[]>(`/organizations/${data.organization.id}/calendar`).then(setCalendarItems),
        api<LinkedInIntegration>(`/organizations/${data.organization.id}/linkedin-integration`).then(setLinkedinIntegration),
        api<KnowledgeReadiness>(`/organizations/${data.organization.id}/knowledge-readiness`).then(setKnowledgeReadiness),
        api<PostMemory[]>(`/organizations/${data.organization.id}/memory`).then((memory) => {
          setMemoryItems(memory);
          if (memory.length > 0) {
            setMetricsForm((current) => ({ ...current, memory_id: memory[0].id }));
          }
        }),
        api<AnalyticsDashboard>(`/organizations/${data.organization.id}/analytics`).then(setAnalyticsDashboard),
        api<ContentArtifact[]>(`/organizations/${data.organization.id}/content-artifacts`).then(setContentArtifacts),
        api<StrategyDashboard>(`/organizations/${data.organization.id}/strategy`).then(setStrategyDashboard),
        api<BackgroundJob[]>(`/organizations/${data.organization.id}/jobs`).then(setJobs),
        api<WorkspaceUser[]>(`/organizations/${data.organization.id}/users`).then(setUsers),
        api<ApprovalPolicy>(`/organizations/${data.organization.id}/approval-policy`).then((policy) => {
          setApprovalPolicy(policy);
          setApprovalPolicyDraft(approvalPolicyForm(policy));
        }),
        api<AIProviderSettings>(`/organizations/${data.organization.id}/ai-provider-settings`).then((settings) => {
          setAiProviderSettings(settings);
          setAiProviderDraft(aiProviderSettingsForm(settings));
        }),
        api<PreferenceSuggestion[]>(`/organizations/${data.organization.id}/preference-suggestions`).then(setPreferenceSuggestions),
        api<CalendarEvent[]>(`/organizations/${data.organization.id}/calendar-events`).then(setCalendarEvents),
        api<TrendSignal[]>(`/organizations/${data.organization.id}/trend-signals`).then(setTrendSignals),
      ]);
    } catch (error) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      setAuthRequired(true);
      setBootstrap(null);
      setBootstrapError(error instanceof Error ? error.message : "Could not load your workspace.");
    }
  }

  useEffect(() => {
    void loadWorkspace();
  }, []);

  useEffect(() => {
    if (!selectedDraft) {
      setReviewPackage(null);
      return;
    }
    api<ReviewerPackage>(`/drafts/${selectedDraft.id}/reviewer-package`).then((pkg) => {
      setReviewPackage(pkg);
      setEditedBody(pkg.draft.body);
      setReviewReason("");
    });
  }, [selectedDraft]);

  useEffect(() => {
    if (!selectedSourceId) {
      setSourceDetail(null);
      return;
    }
    api<SourceDetail>(`/sources/${selectedSourceId}`).then(setSourceDetail);
  }, [selectedSourceId]);

  async function refreshProductSurfaces(organizationId = bootstrap?.organization.id) {
    if (!organizationId) return;
    await Promise.allSettled([
      api<ContentArtifact[]>(`/organizations/${organizationId}/content-artifacts`).then(setContentArtifacts),
      api<StrategyDashboard>(`/organizations/${organizationId}/strategy`).then(setStrategyDashboard),
      api<BackgroundJob[]>(`/organizations/${organizationId}/jobs`).then(setJobs),
    ]);
  }

  async function refreshKnowledgeReadiness(organizationId = bootstrap?.organization.id) {
    if (!organizationId) return;
    setKnowledgeReadiness(await api<KnowledgeReadiness>(`/organizations/${organizationId}/knowledge-readiness`));
  }

  async function refreshJobs(organizationId = bootstrap?.organization.id) {
    if (!organizationId) return;
    setJobs(await api<BackgroundJob[]>(`/organizations/${organizationId}/jobs`));
  }

  async function retryJob(jobId: string) {
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      await api(`/jobs/${jobId}/retry`, { method: "POST" });
      await refreshJobs();
      await refreshProductSurfaces();
      if (bootstrap) {
        await refreshSources();
        await refreshMemoryAndAnalytics();
      }
      setNotice("Job retried successfully.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Job retry failed.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshCurrentWorkspaceState() {
    const current = await api<CurrentWorkspace>("/me");
    setCurrentUser(current.user);
    setOnboarding(current.onboarding);
    return current;
  }

  function requirePermission(allowed: boolean, message: string): boolean {
    if (allowed) return true;
    setNotice(message);
    return false;
  }
  function selectContentFormat(choice: FormatChoice) {
    setFormatChoice(choice);
    setDrafts([]);
    setSelectedDraft(null);
    setReviewPackage(null);
    setEditedBody("");
    setReviewReason("");
    setScheduleFor("");
    setNotice(`Draft format set to ${formatChoiceLabel(choice)}. Generate fresh drafts from the selected brief.`);
  }

  async function generateOpportunities() {
    if (!bootstrap) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      const result = await api<{ opportunities: Opportunity[]; message?: string }>(
        `/organizations/${bootstrap.organization.id}/opportunities/generate`,
        { method: "POST" },
      );
      const ranked = sortOpportunities(result.opportunities);
      setOpportunities(ranked);
      setVisibleOpportunityCount(12);
      setOpportunityMessage(result.message ?? (result.opportunities.length ? "Opportunities generated from approved source context." : ""));
      setSelectedOpportunity(ranked[0] ?? null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshProductSurfaces();
      await refreshCurrentWorkspaceState();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Opportunity generation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitAuth(event: React.FormEvent) {
    event.preventDefault();
    const errors = validateAuthForm(authForm, authMode);
    setAuthErrors(errors);
    if (errors.length > 0) return;
    setBusy(true);
    setBootstrapError("");
    try {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      const response =
        authMode === "signup"
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
      setAuthRequired(false);
      const opportunities = await api<Opportunity[]>(`/organizations/${response.workspace.organization.id}/opportunities`);
      const data = bootstrapFromCurrentWorkspace(response.workspace, opportunities);
      setCurrentUser(response.workspace.user);
      setOnboarding(response.workspace.onboarding);
      setBootstrap(data);
      setSetupForm(setupFromBootstrap(data));
      setOpportunities(sortOpportunities(opportunities));
      setVisibleOpportunityCount(12);
      setActiveView(response.workspace.sources.length > 0 ? "studio" : "sources");
      await Promise.allSettled([
        api<Draft[]>(`/organizations/${response.workspace.organization.id}/calendar`).then(setCalendarItems),
        api<LinkedInIntegration>(`/organizations/${response.workspace.organization.id}/linkedin-integration`).then(setLinkedinIntegration),
        api<KnowledgeReadiness>(`/organizations/${response.workspace.organization.id}/knowledge-readiness`).then(setKnowledgeReadiness),
        api<PostMemory[]>(`/organizations/${response.workspace.organization.id}/memory`).then(setMemoryItems),
        api<AnalyticsDashboard>(`/organizations/${response.workspace.organization.id}/analytics`).then(setAnalyticsDashboard),
        api<ContentArtifact[]>(`/organizations/${response.workspace.organization.id}/content-artifacts`).then(setContentArtifacts),
        api<StrategyDashboard>(`/organizations/${response.workspace.organization.id}/strategy`).then(setStrategyDashboard),
        api<BackgroundJob[]>(`/organizations/${response.workspace.organization.id}/jobs`).then(setJobs),
        api<WorkspaceUser[]>(`/organizations/${response.workspace.organization.id}/users`).then(setUsers),
        api<ApprovalPolicy>(`/organizations/${response.workspace.organization.id}/approval-policy`).then((policy) => {
          setApprovalPolicy(policy);
          setApprovalPolicyDraft(approvalPolicyForm(policy));
        }),
        api<AIProviderSettings>(`/organizations/${response.workspace.organization.id}/ai-provider-settings`).then((settings) => {
          setAiProviderSettings(settings);
          setAiProviderDraft(aiProviderSettingsForm(settings));
        }),
        api<PreferenceSuggestion[]>(`/organizations/${response.workspace.organization.id}/preference-suggestions`).then(setPreferenceSuggestions),
        api<CalendarEvent[]>(`/organizations/${response.workspace.organization.id}/calendar-events`).then(setCalendarEvents),
        api<TrendSignal[]>(`/organizations/${response.workspace.organization.id}/trend-signals`).then(setTrendSignals),
      ]);
      setAuthForm(emptyAuthForm);
      setAuthErrors([]);
      setBootstrapError("");
      setNotice(authMode === "signup" ? "Organization created. Add your first approved source when you are ready." : "Welcome back.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Authentication failed.";
      setBootstrapError(message);
      setAuthErrors(message.split("\n"));
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    setCurrentUser(null);
    setOnboarding(null);
    setBootstrap(null);
    setJobs([]);
    setAuthForm(emptyAuthForm);
    setAuthErrors([]);
    setBootstrapError("");
    setAuthMode("login");
    setAuthRequired(true);
    setNotice("");
  }

  async function skipProfileForNow() {
    if (!bootstrap) return;
    setBusy(true);
    try {
      const state = await api<OnboardingState>(`/organizations/${bootstrap.organization.id}/onboarding/profile`, {
        method: "POST",
        body: JSON.stringify({ skip_profile: true }),
      });
      setOnboarding(state);
      setActiveView("sources");
      setNotice("Profile setup skipped for now. Add an approved source to improve recommendations.");
    } finally {
      setBusy(false);
    }
  }

  if (authRequired && !bootstrap) {
    return (
      <AuthScreen
        authMode={authMode}
        authForm={authForm}
        authErrors={authErrors}
        bootstrapError={bootstrapError}
        busy={busy}
        onAuthModeChange={setAuthMode}
        onAuthFormChange={setAuthForm}
        onSubmit={submitAuth}
      />
    );
  }

  if (!bootstrap) {
    return (
      <main className="loading">
        <section className="connection-card">
          <p className="eyebrow">Quainy Vouch</p>
          <h1>{bootstrapError ? "Workspace service is unavailable" : "Loading workspace"}</h1>
          <p>
            {bootstrapError ||
              "Preparing your workspace. If this takes more than a moment, check that the app services are running."}
          </p>
          {bootstrapError && (
            <div className="connection-actions">
              <button className="icon-button primary" onClick={loadWorkspace} title="Retry connection">
                <RefreshCcw size={18} />
                <span>Retry</span>
              </button>
              <span>Check the app services, then retry.</span>
            </div>
          )}
        </section>
      </main>
    );
  }

  const {
    healthLabel,
    canManageWorkspace,
    canEditKnowledge,
    canEditContent,
    canReviewContent,
    workspacePermissionMessage,
    knowledgePermissionMessage,
    reviewPermissionMessage,
    approvalBlocked,
    approvalProgress,
    canApproveDraft,
    canExportDraft,
    canScheduleDraft,
    canAttemptLinkedinPublish,
    publishCapabilityText,
    recentJobs,
    failedJobCount,
    viewItems,
    currentView,
    approvedSources,
    disabledSources,
    archivedSources,
    railSources,
    railSourceOverflow,
    availableLibraryPlatforms,
    statusOptions,
    rankedOpportunities,
    visibleOpportunities,
    hiddenOpportunityCount,
    visibleContentArtifacts,
    hasVisibleLibraryArtifacts,
    libraryMetrics,
  } = buildWorkspaceModel({
    bootstrap,
    knowledgeReadiness,
    currentUser,
    reviewPackage,
    selectedDraft,
    busy,
    linkedinIntegration,
    jobs,
    drafts,
    memoryItems,
    calendarItems,
    analyticsDashboard,
    users,
    activeView,
    contentArtifacts,
    libraryStatusFilter,
    libraryPlatformFilter,
    opportunities,
    visibleOpportunityCount,
  });

  async function saveSetup() {
    if (!bootstrap || !setupForm) return;
    if (!requirePermission(canManageWorkspace, workspacePermissionMessage)) return;
    const errors = validateSetupForm(setupForm);
    setSetupErrors(errors);
    if (errors.length > 0) return;
    setBusy(true);
    try {
      const organization = await api<Organization>(`/organizations/${bootstrap.organization.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: setupForm.name,
          website_url: setupForm.website_url || null,
          industry: setupForm.industry || null,
          description: setupForm.description || null,
          audience_summary: setupForm.audience_summary || null,
          default_timezone: setupForm.default_timezone || "UTC",
        }),
      });
      const profile = await api<Profile>(`/organizations/${bootstrap.organization.id}/profile`, {
        method: "PATCH",
        body: JSON.stringify({
          one_liner: setupForm.one_liner,
          mission: setupForm.description,
          product_summary: setupForm.description,
          audience: setupForm.audience_summary,
          voice_rules: textToList(setupForm.voice_rules),
          preferred_phrases: textToList(setupForm.preferred_phrases),
          banned_phrases: textToList(setupForm.banned_phrases),
          approved_claims: textToList(setupForm.approved_claims),
          forbidden_claims: textToList(setupForm.forbidden_claims),
          content_pillars: textToList(setupForm.content_pillars),
          sensitive_topics: textToList(setupForm.sensitive_topics),
        }),
      });
      if (linkedinIntegration) {
        setLinkedinIntegration(
          await api<LinkedInIntegration>(`/organizations/${bootstrap.organization.id}/linkedin-integration`, {
            method: "PATCH",
            body: JSON.stringify({
              selected_page_urn: linkedinIntegration.selected_page_urn || null,
              selected_page_name: linkedinIntegration.selected_page_name || null,
              oauth_status: linkedinIntegration.oauth_status || "not_connected",
              permissions: linkedinIntegration.permissions,
              publishing_enabled: linkedinIntegration.publishing_enabled,
            }),
          }),
        );
      }
      const nextBootstrap = { ...bootstrap, organization, profile };
      setBootstrap(nextBootstrap);
      setSetupForm(setupFromBootstrap(nextBootstrap));
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshKnowledgeReadiness(bootstrap.organization.id);
      await refreshCurrentWorkspaceState();
      setSetupErrors([]);
      setNotice("Workspace and voice profile saved.");
    } catch (error) {
      setSetupErrors((error instanceof Error ? error.message : "Workspace setup failed.").split("\n"));
      setNotice(error instanceof Error ? error.message : "Workspace setup failed.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshSources(selectedId?: string) {
    if (!bootstrap) return;
    const sources = await api<Source[]>(`/organizations/${bootstrap.organization.id}/sources`);
    setBootstrap({ ...bootstrap, sources });
    await refreshKnowledgeReadiness(bootstrap.organization.id);
    if (selectedId) {
      setSelectedSourceId(selectedId);
      setSourceDetail(await api<SourceDetail>(`/sources/${selectedId}`));
    }
  }

  function commitSourceForm(nextForm: SourceForm) {
    setSourceForm(nextForm);
    setSourceDraftsByType((current) => ({ ...current, [nextForm.source_type]: nextForm }));
  }

  function selectSourceType(sourceType: string) {
    setSourceDraftsByType((current) => ({ ...current, [sourceForm.source_type]: sourceForm }));
    setSourceForm(sourceDraftsByType[sourceType] ?? emptySourceFormFor(sourceType));
  }

  async function addSource() {
    if (!bootstrap) return;
    if (!requirePermission(canEditKnowledge, knowledgePermissionMessage)) return;
    const errors = validateSourceForm(sourceForm);
    setSourceErrors(errors);
    if (errors.length > 0) return;
    setBusy(true);
    try {
      const addedSourceType = sourceForm.source_type;
      const source = await api<Source>(`/organizations/${bootstrap.organization.id}/sources`, {
        method: "POST",
        body: JSON.stringify({
          source_type: sourceForm.source_type,
          title: sourceForm.title,
          uri: sourceForm.uri || null,
          raw_text: sourceForm.raw_text,
          approval_status: sourceForm.approval_status,
          freshness_days: Number(sourceForm.freshness_days) || 180,
        }),
      });
      const clearedForm = emptySourceFormFor(addedSourceType);
      setSourceForm(clearedForm);
      setSourceDraftsByType((current) => ({ ...current, [addedSourceType]: clearedForm }));
      await refreshSources(source.id);
      setOpportunities([]);
      setVisibleOpportunityCount(12);
      setOpportunityMessage("Source library changed. Generate opportunities again to use the latest approved knowledge.");
      setSelectedOpportunity(null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshProductSurfaces();
      await refreshCurrentWorkspaceState();
      setSourceErrors([]);
      setNotice("Source added, ingested, and ready for opportunity generation.");
    } catch (error) {
      setSourceErrors((error instanceof Error ? error.message : "Source could not be added.").split("\n"));
      setNotice(error instanceof Error ? error.message : "Source could not be added.");
    } finally {
      setBusy(false);
    }
  }

  async function updateSourceStatus(sourceId: string, approvalStatus: string) {
    if (!requirePermission(canEditKnowledge, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      await api<Source>(`/sources/${sourceId}`, {
        method: "PATCH",
        body: JSON.stringify({ approval_status: approvalStatus }),
      });
      await refreshSources(sourceId);
      setOpportunities([]);
      setVisibleOpportunityCount(12);
      setOpportunityMessage("Source availability changed. Generate opportunities again so disabled or archived sources are excluded.");
      setSelectedOpportunity(null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshProductSurfaces();
      setNotice(`Source marked ${approvalStatus}.`);
    } finally {
      setBusy(false);
    }
  }

  async function refreshSource(sourceId: string) {
    if (!requirePermission(canEditKnowledge, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      await api(`/sources/${sourceId}/refresh`, { method: "POST" });
      await refreshSources(sourceId);
      setOpportunities([]);
      setVisibleOpportunityCount(12);
      setOpportunityMessage("Source was re-ingested. Generate opportunities again to use the refreshed evidence.");
      setSelectedOpportunity(null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshProductSurfaces();
      setNotice("Source refreshed and re-ingested.");
    } finally {
      setBusy(false);
    }
  }

  async function handleReadinessAction(action: string) {
    if (action === "settings") {
      setActiveView("settings");
      return;
    }
    if (action === "refresh_sources") {
      setActiveView("sources");
      setNotice("Select a stale source and refresh it after confirming the source is still current.");
      return;
    }
    setActiveView("sources");
  }

  async function handleSourceFile(file: File | undefined) {
    if (!file) return;
    const rawText = await file.text();
    const lowerName = file.name.toLowerCase();
    const extension = lowerName.endsWith(".md") || lowerName.endsWith(".markdown") ? "markdown" : "text";
    const title = file.name.replace(/\.[^/.]+$/, "");
    commitSourceForm({
      ...emptySourceFormFor(extension),
      approval_status: sourceForm.approval_status,
      freshness_days: sourceForm.freshness_days,
      source_type: extension,
      title,
      uri: file.name,
      raw_text: rawText,
    });
  }

  async function createBrief(opportunity: Opportunity) {
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    if (!canBuildBrief(opportunity)) {
      setSelectedOpportunity(opportunity);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      setNotice("This trend needs approved company context before a brief can be created.");
      return;
    }
    setBusy(true);
    try {
      setSelectedOpportunity(opportunity);
      setDrafts([]);
      setSelectedDraft(null);
      const brief = await api<ContentBrief>(`/opportunities/${opportunity.id}/briefs`, { method: "POST" });
      setSelectedBrief(brief);
      setActiveView("studio");
      await refreshProductSurfaces();
      await refreshCurrentWorkspaceState();
      setNotice("Brief created from approved source context.");
    } finally {
      setBusy(false);
    }
  }

  async function addCalendarEvent() {
    if (!bootstrap || !calendarEventForm.title.trim() || !calendarEventForm.starts_at) return;
    if (!requirePermission(canEditKnowledge, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      await api<CalendarEvent>(`/organizations/${bootstrap.organization.id}/calendar-events`, {
        method: "POST",
        body: JSON.stringify({
          title: calendarEventForm.title,
          event_type: calendarEventForm.event_type,
          starts_at: new Date(calendarEventForm.starts_at).toISOString(),
          ends_at: calendarEventForm.ends_at ? new Date(calendarEventForm.ends_at).toISOString() : null,
          description: calendarEventForm.description || null,
          relevance_terms: textToList(calendarEventForm.relevance_terms),
        }),
      });
      setCalendarEventForm(emptyCalendarEventForm);
      setCalendarEvents(await api<CalendarEvent[]>(`/organizations/${bootstrap.organization.id}/calendar-events`));
      setNotice("Calendar event added for trend relevance checks.");
    } finally {
      setBusy(false);
    }
  }

  async function addTrendSignal() {
    if (!bootstrap || !trendSignalForm.title.trim() || trendSignalForm.summary.trim().length < 10) return;
    if (!requirePermission(canEditKnowledge, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      await api<TrendSignal>(`/organizations/${bootstrap.organization.id}/trend-signals`, {
        method: "POST",
        body: JSON.stringify({
          title: trendSignalForm.title,
          summary: trendSignalForm.summary,
          source_name: trendSignalForm.source_name || "Manual trend research",
          source_url: trendSignalForm.source_url || null,
          observed_at: trendSignalForm.observed_at ? new Date(trendSignalForm.observed_at).toISOString() : null,
          relevance_terms: textToList(trendSignalForm.relevance_terms),
        }),
      });
      setTrendSignalForm(emptyTrendSignalForm);
      setTrendSignals(await api<TrendSignal[]>(`/organizations/${bootstrap.organization.id}/trend-signals`));
      setNotice("Trend signal added. Generate trend opportunities when company context is ready.");
    } finally {
      setBusy(false);
    }
  }

  async function generateTrendOpportunities() {
    if (!bootstrap) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      const result = await api<{ opportunities: Opportunity[] }>(`/organizations/${bootstrap.organization.id}/trend-opportunities/generate`, {
        method: "POST",
      });
      const ranked = sortOpportunities(result.opportunities);
      setOpportunities(ranked);
      setVisibleOpportunityCount(12);
      setOpportunityMessage(
        result.opportunities.some((opportunity) => opportunity.status === "warned")
          ? "Trend opportunities generated with warnings for items missing company context."
          : "Trend opportunities generated from calendar and approved company context.",
      );
      setSelectedOpportunity(ranked[0] ?? null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshProductSurfaces();
    } finally {
      setBusy(false);
    }
  }

  async function generateDraftsFromBrief() {
    if (!selectedBrief) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      const params = formatChoiceParams(formatChoice);
      const result = await api<{ drafts: Draft[] }>(`/briefs/${selectedBrief.id}/drafts${params}`, { method: "POST" });
      setDrafts(result.drafts);
      setSelectedDraft(result.drafts[0] ?? null);
      setActiveView("studio");
      await refreshProductSurfaces();
      await refreshCurrentWorkspaceState();
      setNotice(formatChoiceNotice(formatChoice));
    } finally {
      setBusy(false);
    }
  }

  async function regenerateSelectedDraft() {
    if (!selectedDraft) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      const result = await api<{ drafts: Draft[] }>(`/drafts/${selectedDraft.id}/regenerate`, { method: "POST" });
      setDrafts(result.drafts);
      setSelectedDraft(result.drafts[0] ?? null);
      await refreshProductSurfaces();
      setNotice("Drafts regenerated from the same brief and adapter.");
    } finally {
      setBusy(false);
    }
  }

  async function approveDraft() {
    if (!selectedDraft) return;
    if (!requirePermission(canReviewContent, reviewPermissionMessage)) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/approve`, {
        method: "POST",
        body: JSON.stringify({
          edited_body: editedBody,
          reason: reviewReason || "Approved in review desk",
        }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      const pkg = await api<ReviewerPackage>(`/drafts/${selectedDraft.id}/reviewer-package`);
      setSelectedDraft(updated);
      setReviewPackage(pkg);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      await refreshMemoryAndAnalytics();
      await refreshProductSurfaces();
      await refreshCurrentWorkspaceState();
      setNotice(updated.status === "pending_approval" ? "Approval recorded. More reviewer approval is required." : "Approved and stored in memory.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Approval failed.");
    } finally {
      setBusy(false);
    }
  }

  async function rejectDraft() {
    if (!selectedDraft) return;
    if (!requirePermission(canReviewContent, reviewPermissionMessage)) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ edited_body: editedBody, reason: reviewReason }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshProductSurfaces();
      setNotice("Rejected with review signal.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Rejection failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDraftEdit() {
    if (!selectedDraft) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`, {
        method: "PATCH",
        body: JSON.stringify({ body: editedBody }),
      });
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshProductSurfaces();
      setNotice("Draft edit saved and review checks refreshed.");
    } finally {
      setBusy(false);
    }
  }

  async function exportDraft() {
    if (!selectedDraft) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/export`, { method: "POST" });
      let copied = false;
      try {
        await navigator.clipboard?.writeText(editedBody);
        copied = true;
      } catch {
        copied = false;
      }
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      await refreshMemoryAndAnalytics();
      await refreshProductSurfaces();
      setNotice(copied ? "Exported and copied." : "Exported. Clipboard permission was unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function scheduleDraft() {
    if (!selectedDraft || !scheduleFor) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/schedule`, {
        method: "POST",
        body: JSON.stringify({
          scheduled_for: new Date(scheduleFor).toISOString(),
          reason: reviewReason || "Manual queue intent",
        }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      await refreshProductSurfaces();
      setNotice("Scheduled intent saved to the queue.");
    } finally {
      setBusy(false);
    }
  }

  async function publishDraftToLinkedin() {
    if (!selectedDraft || !linkedinIntegration) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      const result = await api<PublishResult>(`/drafts/${selectedDraft.id}/publish/linkedin`, {
        method: "POST",
        body: JSON.stringify({
          page_urn: linkedinIntegration.selected_page_urn || null,
          page_name: linkedinIntegration.selected_page_name || null,
          reason: reviewReason || "Publish approved LinkedIn post",
        }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      await refreshMemoryAndAnalytics();
      await refreshProductSurfaces();
      setNotice(
        result.status === "published"
          ? `Published to ${result.page_name || result.page_urn}.`
          : result.failure_reason || "Publishing failed; approved content was preserved.",
      );
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Publishing failed.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshCalendar() {
    if (!bootstrap) return;
    setCalendarItems(await api<Draft[]>(`/organizations/${bootstrap.organization.id}/calendar`));
  }

  async function refreshMemoryAndAnalytics() {
    if (!bootstrap) return;
    const [memory, analytics] = await Promise.all([
      api<PostMemory[]>(`/organizations/${bootstrap.organization.id}/memory`),
      api<AnalyticsDashboard>(`/organizations/${bootstrap.organization.id}/analytics`),
    ]);
    setMemoryItems(memory);
    setAnalyticsDashboard(analytics);
    if (!metricsForm.memory_id && memory.length > 0) {
      setMetricsForm((current) => ({ ...current, memory_id: memory[0].id }));
    }
  }

  async function importAnalytics() {
    if (!bootstrap) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      await api<PostMemory[]>(`/organizations/${bootstrap.organization.id}/analytics/import`, { method: "POST" });
      await refreshMemoryAndAnalytics();
      await refreshProductSurfaces();
      setNotice("Analytics imported for published LinkedIn memory.");
    } finally {
      setBusy(false);
    }
  }

  async function saveManualMetrics() {
    if (!metricsForm.memory_id) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      await api<PostMemory>(`/memory/${metricsForm.memory_id}/performance`, {
        method: "POST",
        body: JSON.stringify({
          impressions: Number(metricsForm.impressions) || 0,
          reactions: Number(metricsForm.reactions) || 0,
          comments: Number(metricsForm.comments) || 0,
          shares: Number(metricsForm.shares) || 0,
          clicks: Number(metricsForm.clicks) || 0,
          source: "manual",
        }),
      });
      setMetricsForm({ ...metricsForm, impressions: "", reactions: "", comments: "", shares: "", clicks: "" });
      await refreshMemoryAndAnalytics();
      await refreshProductSurfaces();
      setNotice("Manual performance metrics saved.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshUsers() {
    if (!bootstrap) return;
    setUsers(await api<WorkspaceUser[]>(`/organizations/${bootstrap.organization.id}/users`));
  }

  async function addUser() {
    if (!bootstrap || !userForm.name.trim()) return;
    if (!requirePermission(canManageWorkspace, workspacePermissionMessage)) return;
    setBusy(true);
    try {
      await api<WorkspaceUser>(`/organizations/${bootstrap.organization.id}/users`, {
        method: "POST",
        body: JSON.stringify({
          name: userForm.name,
          email: userForm.email || null,
          role: userForm.role,
        }),
      });
      setUserForm(emptyUserForm);
      await refreshUsers();
      setNotice("Team user added.");
    } finally {
      setBusy(false);
    }
  }

  async function updateUserRole(userId: string, role: WorkspaceUser["role"]) {
    if (!bootstrap) return;
    if (!requirePermission(canManageWorkspace, workspacePermissionMessage)) return;
    setBusy(true);
    try {
      await api<WorkspaceUser>(`/organizations/${bootstrap.organization.id}/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      await refreshUsers();
      setNotice("User role updated.");
    } finally {
      setBusy(false);
    }
  }

  async function saveApprovalPolicy() {
    if (!bootstrap || !approvalPolicyDraft) return;
    if (!requirePermission(canManageWorkspace, workspacePermissionMessage)) return;
    setBusy(true);
    try {
      const policy = await api<ApprovalPolicy>(`/organizations/${bootstrap.organization.id}/approval-policy`, {
        method: "PATCH",
        body: JSON.stringify({
          required_reviewer_count: Number(approvalPolicyDraft.required_reviewer_count) || 1,
          require_approval_before_export: approvalPolicyDraft.require_approval_before_export,
          require_approval_before_publish: approvalPolicyDraft.require_approval_before_publish,
          allow_risk_override: approvalPolicyDraft.allow_risk_override,
        }),
      });
      setApprovalPolicy(policy);
      setApprovalPolicyDraft(approvalPolicyForm(policy));
      setNotice("Approval policy saved.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Approval policy update failed.");
    } finally {
      setBusy(false);
    }
  }

  function validateAIProviderForm(form: AIProviderSettingsForm): string[] {
    const errors: string[] = [];
    if (!form.generation_model.trim()) errors.push("Generation model is required.");
    if (!form.embedding_model.trim()) errors.push("Embedding model is required.");
    if (["openai_compatible", "local"].includes(form.generation_provider) && !form.generation_base_url.trim()) {
      errors.push("Generation base URL is required for local or OpenAI-compatible providers.");
    }
    if (["openai_compatible", "local"].includes(form.embedding_provider) && !form.embedding_base_url.trim()) {
      errors.push("Embedding base URL is required for local or OpenAI-compatible providers.");
    }
    const secretPattern = /^[A-Za-z0-9_-]*$/;
    if (!secretPattern.test(form.generation_api_key_env_var) || !secretPattern.test(form.embedding_api_key_env_var)) {
      errors.push("Secret references can only include letters, numbers, underscores, and hyphens.");
    }
    return errors;
  }

  async function saveAIProviderSettings() {
    if (!bootstrap || !aiProviderDraft) return;
    if (!requirePermission(canManageWorkspace, workspacePermissionMessage)) return;
    const errors = validateAIProviderForm(aiProviderDraft);
    if (errors.length > 0) {
      setNotice(errors.join("\n"));
      return;
    }
    setBusy(true);
    try {
      const settings = await api<AIProviderSettings>(`/organizations/${bootstrap.organization.id}/ai-provider-settings`, {
        method: "PATCH",
        body: JSON.stringify(aiProviderPayload(aiProviderDraft)),
      });
      setAiProviderSettings(settings);
      setAiProviderDraft(aiProviderSettingsForm(settings));
      setNotice("AI provider settings saved.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "AI provider settings update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function testAIProviderSettings() {
    if (!bootstrap || !aiProviderDraft) return;
    const errors = validateAIProviderForm(aiProviderDraft);
    if (errors.length > 0) {
      setNotice(errors.join("\n"));
      return;
    }
    setBusy(true);
    try {
      const savedSettings = await api<AIProviderSettings>(`/organizations/${bootstrap.organization.id}/ai-provider-settings`, {
        method: "PATCH",
        body: JSON.stringify(aiProviderPayload(aiProviderDraft)),
      });
      setAiProviderSettings(savedSettings);
      setAiProviderDraft(aiProviderSettingsForm(savedSettings));
      const result = await api<AIProviderConnectionTest>(`/organizations/${bootstrap.organization.id}/ai-provider-settings/test`, {
        method: "POST",
      });
      setAiProviderTest(result);
      setNotice(result.message);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "AI provider test failed.");
    } finally {
      setBusy(false);
    }
  }

  async function generatePreferenceSuggestions() {
    if (!bootstrap) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      const suggestions = await api<PreferenceSuggestion[]>(
        `/organizations/${bootstrap.organization.id}/preference-suggestions/generate`,
        { method: "POST" },
      );
      setPreferenceSuggestions(suggestions);
      setNotice(suggestions.length ? "Preference suggestions generated from review signals." : "No repeated preference signal yet.");
    } finally {
      setBusy(false);
    }
  }

  async function decidePreferenceSuggestion(suggestionId: string, action: "approve" | "dismiss") {
    if (!bootstrap) return;
    if (!requirePermission(canEditContent, knowledgePermissionMessage)) return;
    setBusy(true);
    try {
      await api<PreferenceSuggestion>(`/preference-suggestions/${suggestionId}/${action}`, {
        method: "POST",
        body: JSON.stringify({ reason: action === "approve" ? "Approved from preference panel." : "Dismissed from preference panel." }),
      });
      setPreferenceSuggestions(await api<PreferenceSuggestion[]>(`/organizations/${bootstrap.organization.id}/preference-suggestions`));
      const profile = await api<Profile>(`/organizations/${bootstrap.organization.id}/profile`);
      const nextBootstrap = { ...bootstrap, profile };
      setBootstrap(nextBootstrap);
      setSetupForm(setupFromBootstrap(nextBootstrap));
      setNotice(action === "approve" ? "Preference suggestion applied to profile." : "Preference suggestion dismissed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkspaceShell
      bootstrap={bootstrap}
      currentUser={currentUser}
      onboarding={onboarding}
      healthLabel={healthLabel}
      busy={busy}
      notice={notice}
      activeView={activeView}
      currentView={currentView}
      viewItems={viewItems}
      approvedSources={approvedSources}
      disabledSources={disabledSources}
      archivedSources={archivedSources}
      railSources={railSources}
      railSourceOverflow={railSourceOverflow}
      selectedSourceId={selectedSourceId}
      libraryMetrics={libraryMetrics}
      statusOptions={statusOptions}
      libraryStatusFilter={libraryStatusFilter}
      libraryPlatformFilter={libraryPlatformFilter}
      availableLibraryPlatforms={availableLibraryPlatforms}
      visibleContentArtifacts={visibleContentArtifacts}
      hasVisibleLibraryArtifacts={hasVisibleLibraryArtifacts}
      canManageWorkspace={canManageWorkspace}
      canEditKnowledge={canEditKnowledge}
      canEditContent={canEditContent}
      canReviewContent={canReviewContent}
      workspacePermissionMessage={workspacePermissionMessage}
      knowledgePermissionMessage={knowledgePermissionMessage}
      reviewPermissionMessage={reviewPermissionMessage}
      setupForm={setupForm}
      setupErrors={setupErrors}
      setupSection={setupSection}
      linkedinIntegration={linkedinIntegration}
      aiProviderSettings={aiProviderSettings}
      aiProviderDraft={aiProviderDraft}
      aiProviderTest={aiProviderTest}
      users={users}
      userForm={userForm}
      approvalPolicy={approvalPolicy}
      approvalPolicyDraft={approvalPolicyDraft}
      recentJobs={recentJobs}
      failedJobCount={failedJobCount}
      sourceErrors={sourceErrors}
      knowledgeReadiness={knowledgeReadiness}
      sourceForm={sourceForm}
      sourceDetail={sourceDetail}
      calendarItems={calendarItems}
      calendarEvents={calendarEvents}
      trendSignals={trendSignals}
      calendarEventForm={calendarEventForm}
      trendSignalForm={trendSignalForm}
      canApproveDraft={canApproveDraft}
      canExportDraft={canExportDraft}
      canScheduleDraft={canScheduleDraft}
      canAttemptLinkedinPublish={canAttemptLinkedinPublish}
      approvalBlocked={approvalBlocked}
      publishCapabilityText={publishCapabilityText}
      rankedOpportunities={rankedOpportunities}
      visibleOpportunities={visibleOpportunities}
      hiddenOpportunityCount={hiddenOpportunityCount}
      selectedOpportunity={selectedOpportunity}
      opportunityMessage={opportunityMessage}
      selectedBrief={selectedBrief}
      formatChoice={formatChoice}
      drafts={drafts}
      selectedDraft={selectedDraft}
      reviewPackage={reviewPackage}
      approvalProgress={approvalProgress}
      editedBody={editedBody}
      reviewReason={reviewReason}
      scheduleFor={scheduleFor}
      strategyDashboard={strategyDashboard}
      analyticsDashboard={analyticsDashboard}
      memoryItems={memoryItems}
      metricsForm={metricsForm}
      preferenceSuggestions={preferenceSuggestions}
      onSignOut={signOut}
      onActiveViewChange={setActiveView}
      onSkipProfile={skipProfileForNow}
      onSelectSource={setSelectedSourceId}
      onStatusFilterChange={setLibraryStatusFilter}
      onPlatformFilterChange={setLibraryPlatformFilter}
      onSelectDraft={setSelectedDraft}
      onSetupFormChange={setSetupForm}
      onSetupSectionChange={setSetupSection}
      onLinkedInIntegrationChange={setLinkedinIntegration}
      onAIProviderDraftChange={setAiProviderDraft}
      onUserFormChange={setUserForm}
      onApprovalPolicyDraftChange={setApprovalPolicyDraft}
      onSaveSetup={saveSetup}
      onSaveAIProviderSettings={saveAIProviderSettings}
      onTestAIProviderSettings={testAIProviderSettings}
      onAddUser={addUser}
      onUpdateUserRole={updateUserRole}
      onSaveApprovalPolicy={saveApprovalPolicy}
      onRetryJob={retryJob}
      onAddSource={addSource}
      onReadinessAction={handleReadinessAction}
      onSelectSourceType={selectSourceType}
      onCommitSourceForm={commitSourceForm}
      onSourceFile={handleSourceFile}
      onUpdateSourceStatus={updateSourceStatus}
      onRefreshSource={refreshSource}
      onCalendarEventFormChange={setCalendarEventForm}
      onTrendSignalFormChange={setTrendSignalForm}
      onAddCalendarEvent={addCalendarEvent}
      onAddTrendSignal={addTrendSignal}
      onGenerateTrendOpportunities={generateTrendOpportunities}
      onGenerateOpportunities={generateOpportunities}
      onCreateBrief={createBrief}
      onShowMoreOpportunities={() => setVisibleOpportunityCount((current) => current + 12)}
      onSelectContentFormat={selectContentFormat}
      onGenerateDraftsFromBrief={generateDraftsFromBrief}
      onEditedBodyChange={setEditedBody}
      onReviewReasonChange={setReviewReason}
      onSaveDraftEdit={saveDraftEdit}
      onApproveDraft={approveDraft}
      onRejectDraft={rejectDraft}
      onExportDraft={exportDraft}
      onPublishDraftToLinkedIn={publishDraftToLinkedin}
      onRegenerateSelectedDraft={regenerateSelectedDraft}
      onScheduleForChange={setScheduleFor}
      onScheduleDraft={scheduleDraft}
      onMetricsFormChange={setMetricsForm}
      onImportAnalytics={importAnalytics}
      onSaveManualMetrics={saveManualMetrics}
      onGeneratePreferenceSuggestions={generatePreferenceSuggestions}
      onDecidePreferenceSuggestion={decidePreferenceSuggestion}
    />
  );
}
