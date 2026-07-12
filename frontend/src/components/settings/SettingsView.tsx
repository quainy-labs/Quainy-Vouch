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
  return (
    <>
      {setupForm && (
        <ProfileSetupPanel
          busy={busy}
          notice={notice}
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

      <TeamSettingsPanel
        busy={busy}
        canManageWorkspace={canManageWorkspace}
        workspacePermissionMessage={workspacePermissionMessage}
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

      <OperationsJobsPanel
        busy={busy}
        canEditContent={canEditContent}
        permissionMessage={knowledgePermissionMessage}
        jobs={recentJobs}
        failedJobCount={failedJobCount}
        onRetryJob={onRetryJob}
      />
    </>
  );
}
