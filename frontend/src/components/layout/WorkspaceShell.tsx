import { CalendarView } from "../calendar/CalendarView";
import { LibraryView } from "../library/LibraryView";
import { OnboardingBanner } from "../onboarding/OnboardingBanner";
import { SettingsView } from "../settings/SettingsView";
import { SourcesView } from "../sources/SourcesView";
import { StrategyView } from "../strategy/StrategyView";
import { StudioView } from "../studio/StudioView";
import { formatAuditTime } from "../../lib/forms";
import type { WorkspaceShellProps } from "./WorkspaceShell.types";
import { AppTopbar } from "./AppTopbar";
import { ViewHero } from "./ViewHero";
import { WorkspaceNav } from "./WorkspaceNav";

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
  studioSectionRequest,
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
  onStudioSectionChange,
  onStudioSectionRequestHandled,
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
  onActivateOrganization,
  onDeactivateOrganization,
  onDeleteOrganization,
  onRetryJob,
  onAddSource,
  onReadinessAction,
  onSelectSourceType,
  onCommitSourceForm,
  onSourceFile,
  onUpdateSourceStatus,
  onUpdateSource,
  onRefreshSource,
  onCalendarEventFormChange,
  onTrendSignalFormChange,
  onAddCalendarEvent,
  onAddTrendSignal,
  onGenerateTrendOpportunities,
  onGenerateOpportunities,
  onCreateBrief,
  onDismissOpportunity,
  onOpenLibraryArtifact,
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
              hasVisibleArtifacts={hasVisibleLibraryArtifacts}
              onStatusFilterChange={onStatusFilterChange}
              onPlatformFilterChange={onPlatformFilterChange}
              onOpenStudio={() => onActiveViewChange("studio")}
              onOpenArtifact={onOpenLibraryArtifact}
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
              organization={bootstrap.organization}
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
              onActivateOrganization={onActivateOrganization}
              onDeactivateOrganization={onDeactivateOrganization}
              onDeleteOrganization={onDeleteOrganization}
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
              sources={bootstrap.sources}
              selectedSourceId={selectedSourceId}
              sourceForm={sourceForm}
              sourceDetail={sourceDetail}
              onAddSource={onAddSource}
              onReadinessAction={onReadinessAction}
              onSelectSourceType={onSelectSourceType}
              onSelectSource={onSelectSource}
              onCommitSourceForm={onCommitSourceForm}
              onSourceFile={onSourceFile}
              onUpdateSourceStatus={onUpdateSourceStatus}
              onUpdateSource={onUpdateSource}
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
              sectionRequest={studioSectionRequest}
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
              onDismissOpportunity={onDismissOpportunity}
              onSectionChange={onStudioSectionChange}
              onSectionRequestHandled={onStudioSectionRequestHandled}
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
