import { Activity, AlertTriangle, Bot, Building2, ShieldCheck, Users } from "lucide-react";
import { useState } from "react";
import type {
  AIProviderConnectionTest,
  AIProviderSettings,
  AIProviderSettingsForm,
  ApprovalPolicy,
  ApprovalPolicyForm,
  BackgroundJob,
  LinkedInIntegration,
  SetupForm,
  SetupSection,
  UserForm,
  WorkspaceUser,
} from "../../types";
import { ProfileSetupPanel } from "./ProfileSetupPanel";
import { TeamSettingsPanel } from "./TeamSettingsPanel";
import { OperationsJobsPanel } from "./OperationsJobsPanel";

type SettingsViewProps = {
  busy: boolean;
  notice: string;
  canManageWorkspace: boolean;
  canEditContent: boolean;
  workspacePermissionMessage: string;
  knowledgePermissionMessage: string;
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
};

export function SettingsView({
  busy,
  notice,
  canManageWorkspace,
  canEditContent,
  workspacePermissionMessage,
  knowledgePermissionMessage,
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
}: SettingsViewProps) {
  const [activeSection, setActiveSection] = useState<"profile" | "publishing" | "ai" | "team" | "approval" | "operations" | "lifecycle">("profile");
  const settingsNotice = /workspace|profile|provider|approval|policy|team|user|linkedin|publishing|configuration/i.test(notice) ? notice : "";

  return (
    <section className="section-workspace settings-workspace">
      <aside className="section-sidebar" aria-label="Settings sections">
        <button className={activeSection === "profile" ? "active" : ""} onClick={() => setActiveSection("profile")} type="button">
          <Building2 size={16} />
          <span>Profile</span>
          <small>Company, voice, claims</small>
        </button>
        <button className={activeSection === "publishing" ? "active" : ""} onClick={() => setActiveSection("publishing")} type="button">
          <ShieldCheck size={16} />
          <span>Publishing</span>
          <small>LinkedIn settings</small>
        </button>
        <button className={activeSection === "ai" ? "active" : ""} onClick={() => setActiveSection("ai")} type="button">
          <Bot size={16} />
          <span>AI provider</span>
          <small>Models and runtime</small>
        </button>
        <button className={activeSection === "team" ? "active" : ""} onClick={() => setActiveSection("team")} type="button">
          <Users size={16} />
          <span>Team</span>
          <small>{users.length} users</small>
        </button>
        <button className={activeSection === "approval" ? "active" : ""} onClick={() => setActiveSection("approval")} type="button">
          <ShieldCheck size={16} />
          <span>Approval</span>
          <small>{approvalPolicy?.required_reviewer_count ?? 0} reviewers</small>
        </button>
        <button className={activeSection === "operations" ? "active" : ""} onClick={() => setActiveSection("operations")} type="button">
          <Activity size={16} />
          <span>Operations</span>
          <small>{failedJobCount > 0 ? `${failedJobCount} failed` : `${recentJobs.length} recent`}</small>
        </button>
        <button className={activeSection === "lifecycle" ? "active" : ""} onClick={() => setActiveSection("lifecycle")} type="button">
          <AlertTriangle size={16} />
          <span>Organization</span>
          <small>Lifecycle</small>
        </button>
      </aside>

      <div className="section-content">
        {setupForm && activeSection === "profile" && (
          <ProfileSetupPanel
            busy={busy}
            notice={settingsNotice}
            canManageWorkspace={canManageWorkspace}
            workspacePermissionMessage={workspacePermissionMessage}
            setupForm={setupForm}
            setupErrors={setupErrors}
            setupSection={setupSection}
            linkedinIntegration={linkedinIntegration}
            aiProviderSettings={aiProviderSettings}
            aiProviderDraft={aiProviderDraft}
            aiProviderTest={aiProviderTest}
            onSetupFormChange={onSetupFormChange}
            onSetupSectionChange={onSetupSectionChange}
            onLinkedInIntegrationChange={onLinkedInIntegrationChange}
            onAIProviderDraftChange={onAIProviderDraftChange}
            onSaveSetup={onSaveSetup}
            onSaveAIProviderSettings={onSaveAIProviderSettings}
            onTestAIProviderSettings={onTestAIProviderSettings}
          />
        )}

        {setupForm && activeSection === "publishing" && (
          <ProfileSetupPanel
            busy={busy}
            notice={settingsNotice}
            canManageWorkspace={canManageWorkspace}
            workspacePermissionMessage={workspacePermissionMessage}
            eyebrow="Publishing"
            title="LinkedIn publishing connection"
            saveLabel="Save publishing"
            sectionIds={["linkedin"]}
            setupForm={setupForm}
            setupErrors={setupErrors}
            setupSection={setupSection}
            linkedinIntegration={linkedinIntegration}
            aiProviderSettings={aiProviderSettings}
            aiProviderDraft={aiProviderDraft}
            aiProviderTest={aiProviderTest}
            onSetupFormChange={onSetupFormChange}
            onSetupSectionChange={onSetupSectionChange}
            onLinkedInIntegrationChange={onLinkedInIntegrationChange}
            onAIProviderDraftChange={onAIProviderDraftChange}
            onSaveSetup={onSaveSetup}
            onSaveAIProviderSettings={onSaveAIProviderSettings}
            onTestAIProviderSettings={onTestAIProviderSettings}
          />
        )}

        {setupForm && activeSection === "ai" && (
          <ProfileSetupPanel
            busy={busy}
            notice={settingsNotice}
            canManageWorkspace={canManageWorkspace}
            workspacePermissionMessage={workspacePermissionMessage}
            eyebrow="AI provider"
            title="Reasoning and embedding runtime"
            saveLabel="Save setup"
            showPrimaryAction={false}
            sectionIds={["ai"]}
            setupForm={setupForm}
            setupErrors={setupErrors}
            setupSection={setupSection}
            linkedinIntegration={linkedinIntegration}
            aiProviderSettings={aiProviderSettings}
            aiProviderDraft={aiProviderDraft}
            aiProviderTest={aiProviderTest}
            onSetupFormChange={onSetupFormChange}
            onSetupSectionChange={onSetupSectionChange}
            onLinkedInIntegrationChange={onLinkedInIntegrationChange}
            onAIProviderDraftChange={onAIProviderDraftChange}
            onSaveSetup={onSaveSetup}
            onSaveAIProviderSettings={onSaveAIProviderSettings}
            onTestAIProviderSettings={onTestAIProviderSettings}
          />
        )}

        {activeSection === "team" && (
          <TeamSettingsPanel
            busy={busy}
            canManageWorkspace={canManageWorkspace}
            workspacePermissionMessage={workspacePermissionMessage}
            panel="team"
            users={users}
            userForm={userForm}
            approvalPolicy={approvalPolicy}
            approvalPolicyDraft={approvalPolicyDraft}
            onUserFormChange={onUserFormChange}
            onApprovalPolicyDraftChange={onApprovalPolicyDraftChange}
            onAddUser={onAddUser}
            onUpdateUserRole={onUpdateUserRole}
            onSaveApprovalPolicy={onSaveApprovalPolicy}
          />
        )}

        {activeSection === "approval" && (
          <TeamSettingsPanel
            busy={busy}
            canManageWorkspace={canManageWorkspace}
            workspacePermissionMessage={workspacePermissionMessage}
            panel="approval"
            users={users}
            userForm={userForm}
            approvalPolicy={approvalPolicy}
            approvalPolicyDraft={approvalPolicyDraft}
            onUserFormChange={onUserFormChange}
            onApprovalPolicyDraftChange={onApprovalPolicyDraftChange}
            onAddUser={onAddUser}
            onUpdateUserRole={onUpdateUserRole}
            onSaveApprovalPolicy={onSaveApprovalPolicy}
          />
        )}

        {activeSection === "operations" && (
          recentJobs.length > 0 ? (
            <OperationsJobsPanel
              busy={busy}
              canEditContent={canEditContent}
              permissionMessage={knowledgePermissionMessage}
              jobs={recentJobs}
              failedJobCount={failedJobCount}
              onRetryJob={onRetryJob}
            />
          ) : (
            <section className="panel band operations-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Operations</p>
                  <h2>Background jobs</h2>
                </div>
                <span className="review-status">All clear</span>
              </div>
              <div className="empty-detail">
                <Activity size={24} />
                <strong>No recent jobs</strong>
                <p>Background work will appear here when sources are ingested, content is refreshed, or failed jobs need attention.</p>
              </div>
            </section>
          )
        )}

        {activeSection === "lifecycle" && (
          <section className="panel band danger-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Organization</p>
                <h2>Lifecycle controls</h2>
              </div>
              <span className="status-pill archived">Owner only</span>
            </div>
            <div className="lifecycle-grid">
              <article>
                <strong>Deactivate workspace</strong>
                <p>Pause generation, publishing, and background jobs while preserving audit history and stored sources.</p>
                <button className="icon-button" disabled title="Backend lifecycle endpoint is not implemented yet" type="button">
                  Deactivate
                </button>
              </article>
              <article>
                <strong>Delete organization</strong>
                <p>Permanent deletion needs a dedicated backend flow with confirmation, export, and audit safeguards.</p>
                <button className="icon-button" disabled title="Backend deletion endpoint is not implemented yet" type="button">
                  Delete
                </button>
              </article>
            </div>
          </section>
        )}
      </div>
    </section>
  );
}
