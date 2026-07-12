import { useState } from "react";
import { useReviewerPackage } from "../useReviewerPackage";
import { useSourceDetail } from "../useSourceDetail";
import type {
  AIProviderConnectionTest,
  AIProviderSettings,
  AIProviderSettingsForm,
  AnalyticsDashboard,
  ApprovalPolicy,
  ApprovalPolicyForm,
  AuthForm,
  BackgroundJob,
  Bootstrap,
  CalendarEvent,
  CalendarEventForm,
  ContentArtifact,
  ContentBrief,
  Draft,
  FormatChoice,
  KnowledgeReadiness,
  LibraryPlatformFilter,
  LibraryStatusFilter,
  LinkedInIntegration,
  MetricsForm,
  OnboardingState,
  Opportunity,
  PostMemory,
  PreferenceSuggestion,
  SetupForm,
  SetupSection,
  SourceForm,
  StrategyDashboard,
  TrendSignal,
  TrendSignalForm,
  UserForm,
  WorkspaceUser,
  WorkspaceView,
} from "../../types";
import {
  emptyAuthForm,
  emptyCalendarEventForm,
  emptyMetricsForm,
  emptySourceForm,
  emptyTrendSignalForm,
  emptyUserForm,
} from "../../lib/forms";

export function useWorkspaceControllerState() {
  const [currentUser, setCurrentUser] = useState<WorkspaceUser | null>(null);
  const [onboarding, setOnboarding] = useState<OnboardingState | null>(null);
  const [authMode, setAuthMode] = useState<"signup" | "login">("signup");
  const [signupAuthForm, setSignupAuthForm] = useState<AuthForm>(emptyAuthForm);
  const [loginAuthForm, setLoginAuthForm] = useState<AuthForm>(emptyAuthForm);
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
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [visibleOpportunityCount, setVisibleOpportunityCount] = useState(12);
  const [opportunityMessage, setOpportunityMessage] = useState("");
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);
  const [selectedBrief, setSelectedBrief] = useState<ContentBrief | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<Draft | null>(null);
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
  const [formatChoice, setFormatChoice] = useState<FormatChoice>("linkedin_post");
  const [activeView, setActiveView] = useState<WorkspaceView>("studio");
  const [setupSection, setSetupSection] = useState<SetupSection>("company");
  const [libraryStatusFilter, setLibraryStatusFilter] = useState<LibraryStatusFilter>("all");
  const [libraryPlatformFilter, setLibraryPlatformFilter] = useState<LibraryPlatformFilter>("all");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const { sourceDetail, setSourceDetail } = useSourceDetail(selectedSourceId);
  const { reviewPackage, setReviewPackage } = useReviewerPackage({
    selectedDraft,
    onBodyLoaded: setEditedBody,
    onReasonReset: setReviewReason,
  });

  return {
    currentUser,
    setCurrentUser,
    onboarding,
    setOnboarding,
    authMode,
    setAuthMode,
    signupAuthForm,
    setSignupAuthForm,
    loginAuthForm,
    setLoginAuthForm,
    authErrors,
    setAuthErrors,
    authRequired,
    setAuthRequired,
    bootstrap,
    setBootstrap,
    bootstrapError,
    setBootstrapError,
    setupForm,
    setSetupForm,
    setupErrors,
    setSetupErrors,
    sourceForm,
    setSourceForm,
    sourceErrors,
    setSourceErrors,
    sourceDraftsByType,
    setSourceDraftsByType,
    selectedSourceId,
    setSelectedSourceId,
    sourceDetail,
    setSourceDetail,
    opportunities,
    setOpportunities,
    visibleOpportunityCount,
    setVisibleOpportunityCount,
    opportunityMessage,
    setOpportunityMessage,
    selectedOpportunity,
    setSelectedOpportunity,
    selectedBrief,
    setSelectedBrief,
    drafts,
    setDrafts,
    selectedDraft,
    setSelectedDraft,
    reviewPackage,
    setReviewPackage,
    editedBody,
    setEditedBody,
    reviewReason,
    setReviewReason,
    scheduleFor,
    setScheduleFor,
    calendarItems,
    setCalendarItems,
    linkedinIntegration,
    setLinkedinIntegration,
    knowledgeReadiness,
    setKnowledgeReadiness,
    memoryItems,
    setMemoryItems,
    analyticsDashboard,
    setAnalyticsDashboard,
    contentArtifacts,
    setContentArtifacts,
    strategyDashboard,
    setStrategyDashboard,
    jobs,
    setJobs,
    metricsForm,
    setMetricsForm,
    users,
    setUsers,
    userForm,
    setUserForm,
    approvalPolicy,
    setApprovalPolicy,
    approvalPolicyDraft,
    setApprovalPolicyDraft,
    aiProviderSettings,
    setAiProviderSettings,
    aiProviderDraft,
    setAiProviderDraft,
    aiProviderTest,
    setAiProviderTest,
    preferenceSuggestions,
    setPreferenceSuggestions,
    calendarEvents,
    setCalendarEvents,
    trendSignals,
    setTrendSignals,
    calendarEventForm,
    setCalendarEventForm,
    trendSignalForm,
    setTrendSignalForm,
    formatChoice,
    setFormatChoice,
    activeView,
    setActiveView,
    setupSection,
    setSetupSection,
    libraryStatusFilter,
    setLibraryStatusFilter,
    libraryPlatformFilter,
    setLibraryPlatformFilter,
    busy,
    setBusy,
    notice,
    setNotice,
  };
}

export type WorkspaceControllerState = ReturnType<typeof useWorkspaceControllerState>;
