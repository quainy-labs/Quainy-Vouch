import type {
  AIProviderConnectionTest,
  AIProviderSettings,
  AIProviderSettingsForm,
  AnalyticsDashboard,
  ApprovalPolicy,
  ApprovalPolicyForm,
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
  ReviewerPackage,
  SetupForm,
  SetupSection,
  Source,
  SourceDetail,
  SourceForm,
  StrategyDashboard,
  TrendSignal,
  TrendSignalForm,
  UserForm,
  ViewItem,
  WorkspaceUser,
  WorkspaceView,
} from "../../types";

type LibraryMetric = {
  label: string;
  value: string | number;
  detail: string;
};

type LibraryStatusOption = {
  id: LibraryStatusFilter;
  label: string;
};

export type WorkspaceShellProps = {
  bootstrap: Bootstrap;
  currentUser: WorkspaceUser | null;
  onboarding: OnboardingState | null;
  healthLabel: string;
  busy: boolean;
  notice: string;
  activeView: WorkspaceView;
  currentView: ViewItem;
  viewItems: ViewItem[];
  approvedSources: Source[];
  disabledSources: Source[];
  archivedSources: Source[];
  railSources: Source[];
  railSourceOverflow: number;
  selectedSourceId: string | null;
  libraryMetrics: LibraryMetric[];
  statusOptions: LibraryStatusOption[];
  libraryStatusFilter: LibraryStatusFilter;
  libraryPlatformFilter: LibraryPlatformFilter;
  availableLibraryPlatforms: string[];
  visibleContentArtifacts: ContentArtifact[];
  hasVisibleLibraryArtifacts: boolean;
  canManageWorkspace: boolean;
  canEditKnowledge: boolean;
  canEditContent: boolean;
  canReviewContent: boolean;
  workspacePermissionMessage: string;
  knowledgePermissionMessage: string;
  reviewPermissionMessage: string;
  setupForm: SetupForm | null;
  setupErrors: string[];
  setupSection: SetupSection;
  linkedinIntegration: LinkedInIntegration | null;
  aiProviderSettings: AIProviderSettings | null;
  aiProviderDraft: AIProviderSettingsForm | null;
  aiProviderTest: AIProviderConnectionTest | null;
  users: WorkspaceUser[];
  userForm: UserForm;
  approvalPolicy: ApprovalPolicy | null;
  approvalPolicyDraft: ApprovalPolicyForm | null;
  recentJobs: BackgroundJob[];
  failedJobCount: number;
  sourceErrors: string[];
  knowledgeReadiness: KnowledgeReadiness | null;
  sourceForm: SourceForm;
  sourceDetail: SourceDetail | null;
  calendarItems: Draft[];
  calendarEvents: CalendarEvent[];
  trendSignals: TrendSignal[];
  calendarEventForm: CalendarEventForm;
  trendSignalForm: TrendSignalForm;
  canApproveDraft: boolean;
  canExportDraft: boolean;
  canScheduleDraft: boolean;
  canAttemptLinkedinPublish: boolean;
  approvalBlocked: boolean;
  publishCapabilityText: string;
  rankedOpportunities: Opportunity[];
  visibleOpportunities: Opportunity[];
  hiddenOpportunityCount: number;
  selectedOpportunity: Opportunity | null;
  opportunityMessage: string;
  selectedBrief: ContentBrief | null;
  formatChoice: FormatChoice;
  drafts: Draft[];
  selectedDraft: Draft | null;
  reviewPackage: ReviewerPackage | null;
  approvalProgress: Record<string, unknown>;
  editedBody: string;
  reviewReason: string;
  scheduleFor: string;
  strategyDashboard: StrategyDashboard | null;
  analyticsDashboard: AnalyticsDashboard | null;
  memoryItems: PostMemory[];
  metricsForm: MetricsForm;
  preferenceSuggestions: PreferenceSuggestion[];
  onSignOut: () => void;
  onActiveViewChange: (view: WorkspaceView) => void;
  onSkipProfile: () => void | Promise<void>;
  onSelectSource: (sourceId: string | null) => void;
  onStatusFilterChange: (status: LibraryStatusFilter) => void;
  onPlatformFilterChange: (platform: LibraryPlatformFilter) => void;
  onSelectDraft: (draft: Draft) => void;
  onSetupFormChange: (form: SetupForm) => void;
  onSetupSectionChange: (section: SetupSection) => void;
  onLinkedInIntegrationChange: (integration: LinkedInIntegration) => void;
  onAIProviderDraftChange: (draft: AIProviderSettingsForm) => void;
  onUserFormChange: (form: UserForm) => void;
  onApprovalPolicyDraftChange: (form: ApprovalPolicyForm) => void;
  onSaveSetup: () => void | Promise<void>;
  onSaveAIProviderSettings: () => void | Promise<void>;
  onTestAIProviderSettings: () => void | Promise<void>;
  onAddUser: () => void | Promise<void>;
  onUpdateUserRole: (userId: string, role: WorkspaceUser["role"]) => void | Promise<void>;
  onSaveApprovalPolicy: () => void | Promise<void>;
  onRetryJob: (jobId: string) => void | Promise<void>;
  onAddSource: () => void | Promise<void>;
  onReadinessAction: (action: string) => void | Promise<void>;
  onSelectSourceType: (sourceType: string) => void;
  onCommitSourceForm: (form: SourceForm) => void;
  onSourceFile: (file: File | undefined) => void | Promise<void>;
  onUpdateSourceStatus: (sourceId: string, approvalStatus: string) => void | Promise<void>;
  onRefreshSource: (sourceId: string) => void | Promise<void>;
  onCalendarEventFormChange: (form: CalendarEventForm) => void;
  onTrendSignalFormChange: (form: TrendSignalForm) => void;
  onAddCalendarEvent: () => void | Promise<void>;
  onAddTrendSignal: () => void | Promise<void>;
  onGenerateTrendOpportunities: () => void | Promise<void>;
  onGenerateOpportunities: () => void | Promise<void>;
  onCreateBrief: (opportunity: Opportunity) => void | Promise<void>;
  onShowMoreOpportunities: () => void;
  onSelectContentFormat: (choice: FormatChoice) => void;
  onGenerateDraftsFromBrief: () => void | Promise<void>;
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
  onMetricsFormChange: (form: MetricsForm) => void;
  onImportAnalytics: () => void | Promise<void>;
  onSaveManualMetrics: () => void | Promise<void>;
  onGeneratePreferenceSuggestions: () => void | Promise<void>;
  onDecidePreferenceSuggestion: (suggestionId: string, action: "approve" | "dismiss") => void | Promise<void>;
};
