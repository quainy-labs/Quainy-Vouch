import { CalendarView } from "../calendar/CalendarView";
import { LibraryView } from "../library/LibraryView";
import { OnboardingBanner } from "../onboarding/OnboardingBanner";
import { SettingsView } from "../settings/SettingsView";
import { SourcesView } from "../sources/SourcesView";
import { StrategyView } from "../strategy/StrategyView";
import { StudioView } from "../studio/StudioView";
import { formatAuditTime } from "../../lib/forms";
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
import { AppTopbar } from "./AppTopbar";
import { ViewHero } from "./ViewHero";
import { WorkspaceNav } from "./WorkspaceNav";
import { WorkspaceRail } from "./WorkspaceRail";

type LibraryMetric = {
  label: string;
  value: string | number;
  detail: string;
};

type LibraryStatusOption = {
  id: LibraryStatusFilter;
  label: string;
};

type WorkspaceShellProps = {
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

export function WorkspaceShell({
  bootstrap,
  currentUser,
  onboarding,
  healthLabel,
  busy,
  notice,
  activeView,
  currentView,
  viewItems,
  approvedSources,
  disabledSources,
  archivedSources,
  railSources,
  railSourceOverflow,
  selectedSourceId,
  libraryMetrics,
  statusOptions,
  libraryStatusFilter,
  libraryPlatformFilter,
  availableLibraryPlatforms,
  visibleContentArtifacts,
  hasVisibleLibraryArtifacts,
  canManageWorkspace,
  canEditKnowledge,
  canEditContent,
  canReviewContent,
  workspacePermissionMessage,
  knowledgePermissionMessage,
  reviewPermissionMessage,
  setupForm,
  setupErrors,
  setupSection,
  linkedinIntegration,
  aiProviderSettings,
  aiProviderDraft,
  aiProviderTest,
  users,
  userForm,
  approvalPolicy,
  approvalPolicyDraft,
  recentJobs,
  failedJobCount,
  sourceErrors,
  knowledgeReadiness,
  sourceForm,
  sourceDetail,
  calendarItems,
  calendarEvents,
  trendSignals,
  calendarEventForm,
  trendSignalForm,
  canApproveDraft,
  canExportDraft,
  canScheduleDraft,
  canAttemptLinkedinPublish,
  approvalBlocked,
  publishCapabilityText,
  rankedOpportunities,
  visibleOpportunities,
  hiddenOpportunityCount,
  selectedOpportunity,
  opportunityMessage,
  selectedBrief,
  formatChoice,
  drafts,
  selectedDraft,
  reviewPackage,
  approvalProgress,
  editedBody,
  reviewReason,
  scheduleFor,
  strategyDashboard,
  analyticsDashboard,
  memoryItems,
  metricsForm,
  preferenceSuggestions,
  onSignOut,
  onActiveViewChange,
  onSkipProfile,
  onSelectSource,
  onStatusFilterChange,
  onPlatformFilterChange,
  onSelectDraft,
  onSetupFormChange,
  onSetupSectionChange,
  onLinkedInIntegrationChange,
  onAIProviderDraftChange,
  onUserFormChange,
  onApprovalPolicyDraftChange,
  onSaveSetup,
  onSaveAIProviderSettings,
  onTestAIProviderSettings,
  onAddUser,
  onUpdateUserRole,
  onSaveApprovalPolicy,
  onRetryJob,
  onAddSource,
  onReadinessAction,
  onSelectSourceType,
  onCommitSourceForm,
  onSourceFile,
  onUpdateSourceStatus,
  onRefreshSource,
  onCalendarEventFormChange,
  onTrendSignalFormChange,
  onAddCalendarEvent,
  onAddTrendSignal,
  onGenerateTrendOpportunities,
  onGenerateOpportunities,
  onCreateBrief,
  onShowMoreOpportunities,
  onSelectContentFormat,
  onGenerateDraftsFromBrief,
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
  onMetricsFormChange,
  onImportAnalytics,
  onSaveManualMetrics,
  onGeneratePreferenceSuggestions,
  onDecidePreferenceSuggestion,
}: WorkspaceShellProps) {
  return (
    <main className="app-shell">
      <AppTopbar
        organizationName={bootstrap.organization.name}
        healthLabel={healthLabel}
        pillarCount={bootstrap.profile.content_pillars.length}
        workspaceLabel={onboarding ? `${onboarding.completion_percent}% onboarded` : currentUser?.role ?? "workspace"}
        onSignOut={onSignOut}
      />

      {onboarding && onboarding.completion_percent < 75 && (
        <OnboardingBanner
          onboarding={onboarding}
          busy={busy}
          onOpenSettings={() => onActiveViewChange("settings")}
          onSkipProfile={onSkipProfile}
          onAddSource={() => onActiveViewChange("sources")}
        />
      )}

      <WorkspaceNav activeView={activeView} items={viewItems} onSelectView={onActiveViewChange} />

      <section className="workspace">
        <WorkspaceRail
          approvedCount={approvedSources.length}
          disabledCount={disabledSources.length}
          archivedCount={archivedSources.length}
          sources={railSources}
          selectedSourceId={selectedSourceId}
          sourceOverflow={railSourceOverflow}
          preferredPhrases={bootstrap.profile.preferred_phrases}
          onSelectSource={onSelectSource}
          onShowSources={() => onActiveViewChange("sources")}
        />

        <section className="main-column">
          <ViewHero view={currentView} />

          {activeView === "library" && (
            <LibraryView
              metrics={libraryMetrics}
              statusOptions={statusOptions}
              statusFilter={libraryStatusFilter}
              platformFilter={libraryPlatformFilter}
              availablePlatforms={availableLibraryPlatforms}
              artifacts={visibleContentArtifacts}
              drafts={drafts}
              hasVisibleArtifacts={hasVisibleLibraryArtifacts}
              onStatusFilterChange={onStatusFilterChange}
              onPlatformFilterChange={onPlatformFilterChange}
              onOpenStudio={() => onActiveViewChange("studio")}
              onOpenDraft={(draft) => {
                onSelectDraft(draft);
                onActiveViewChange("studio");
              }}
            />
          )}

          {activeView === "settings" && (
            <SettingsView
              busy={busy}
              notice={notice}
              canManageWorkspace={canManageWorkspace}
              canEditContent={canEditContent}
              workspacePermissionMessage={workspacePermissionMessage}
              knowledgePermissionMessage={knowledgePermissionMessage}
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
              onSetupFormChange={onSetupFormChange}
              onSetupSectionChange={onSetupSectionChange}
              onLinkedInIntegrationChange={onLinkedInIntegrationChange}
              onAIProviderDraftChange={onAIProviderDraftChange}
              onUserFormChange={onUserFormChange}
              onApprovalPolicyDraftChange={onApprovalPolicyDraftChange}
              onSaveSetup={onSaveSetup}
              onSaveAIProviderSettings={onSaveAIProviderSettings}
              onTestAIProviderSettings={onTestAIProviderSettings}
              onAddUser={onAddUser}
              onUpdateUserRole={onUpdateUserRole}
              onSaveApprovalPolicy={onSaveApprovalPolicy}
              onRetryJob={onRetryJob}
            />
          )}

          {activeView === "sources" && (
            <SourcesView
              busy={busy}
              canEditKnowledge={canEditKnowledge}
              permissionMessage={knowledgePermissionMessage}
              sourceErrors={sourceErrors}
              readiness={knowledgeReadiness}
              approvedCount={approvedSources.length}
              disabledCount={disabledSources.length}
              archivedCount={archivedSources.length}
              totalSourceCount={bootstrap.sources.length}
              sourceForm={sourceForm}
              sourceDetail={sourceDetail}
              onAddSource={onAddSource}
              onReadinessAction={onReadinessAction}
              onSelectSourceType={onSelectSourceType}
              onCommitSourceForm={onCommitSourceForm}
              onSourceFile={onSourceFile}
              onUpdateSourceStatus={onUpdateSourceStatus}
              onRefreshSource={onRefreshSource}
              formatAuditTime={formatAuditTime}
            />
          )}

          {activeView === "calendar" && (
            <CalendarView
              busy={busy}
              canEditContent={canEditContent}
              canEditKnowledge={canEditKnowledge}
              permissionMessage={knowledgePermissionMessage}
              calendarItems={calendarItems}
              calendarEvents={calendarEvents}
              trendSignals={trendSignals}
              calendarEventForm={calendarEventForm}
              trendSignalForm={trendSignalForm}
              onCalendarEventFormChange={onCalendarEventFormChange}
              onTrendSignalFormChange={onTrendSignalFormChange}
              onAddCalendarEvent={onAddCalendarEvent}
              onAddTrendSignal={onAddTrendSignal}
              onGenerateTrendOpportunities={onGenerateTrendOpportunities}
            />
          )}

          {activeView === "studio" && (
            <StudioView
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
              approvedSources={approvedSources}
              rankedOpportunities={rankedOpportunities}
              visibleOpportunities={visibleOpportunities}
              hiddenOpportunityCount={hiddenOpportunityCount}
              selectedOpportunity={selectedOpportunity}
              opportunityMessage={opportunityMessage}
              opportunityCount={rankedOpportunities.length}
              selectedBrief={selectedBrief}
              formatChoice={formatChoice}
              drafts={drafts}
              selectedDraft={selectedDraft}
              reviewPackage={reviewPackage}
              approvalPolicy={approvalPolicy}
              approvalProgress={approvalProgress}
              editedBody={editedBody}
              reviewReason={reviewReason}
              scheduleFor={scheduleFor}
              linkedinIntegration={linkedinIntegration}
              onGenerateOpportunities={onGenerateOpportunities}
              onCreateBrief={onCreateBrief}
              onShowMoreOpportunities={onShowMoreOpportunities}
              onSelectContentFormat={onSelectContentFormat}
              onGenerateDraftsFromBrief={onGenerateDraftsFromBrief}
              onSelectDraft={onSelectDraft}
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

          {activeView === "strategy" && (
            <StrategyView
              busy={busy}
              canEditContent={canEditContent}
              permissionMessage={knowledgePermissionMessage}
              strategyDashboard={strategyDashboard}
              analyticsDashboard={analyticsDashboard}
              memoryItems={memoryItems}
              metricsForm={metricsForm}
              preferenceSuggestions={preferenceSuggestions}
              onMetricsFormChange={onMetricsFormChange}
              onImportAnalytics={onImportAnalytics}
              onSaveManualMetrics={onSaveManualMetrics}
              onGeneratePreferenceSuggestions={onGeneratePreferenceSuggestions}
              onDecidePreferenceSuggestion={onDecidePreferenceSuggestion}
            />
          )}
        </section>
      </section>
    </main>
  );
}
