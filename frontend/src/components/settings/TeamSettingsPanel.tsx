import { Plus, Save, ShieldCheck } from "lucide-react";
import type { ApprovalPolicy, ApprovalPolicyForm, UserForm, WorkspaceUser } from "../../types";

type TeamSettingsPanelProps = {
  busy: boolean;
  canManageWorkspace: boolean;
  workspacePermissionMessage: string;
  users: WorkspaceUser[];
  userForm: UserForm;
  approvalPolicy: ApprovalPolicy | null;
  approvalPolicyDraft: ApprovalPolicyForm | null;
  onUserFormChange: (form: UserForm) => void;
  onApprovalPolicyDraftChange: (form: ApprovalPolicyForm) => void;
  onAddUser: () => void | Promise<void>;
  onUpdateUserRole: (userId: string, role: WorkspaceUser["role"]) => void | Promise<void>;
  onSaveApprovalPolicy: () => void | Promise<void>;
};

export function TeamSettingsPanel({
  busy,
  canManageWorkspace,
  workspacePermissionMessage,
  users,
  userForm,
  approvalPolicy,
  approvalPolicyDraft,
  onUserFormChange,
  onApprovalPolicyDraftChange,
  onAddUser,
  onUpdateUserRole,
  onSaveApprovalPolicy,
}: TeamSettingsPanelProps) {
  return (
    <section className="panel band team-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Team</p>
          <h2>Users and roles</h2>
        </div>
        <button
          className="icon-button primary"
          onClick={() => void onAddUser()}
          disabled={busy || !canManageWorkspace || !userForm.name.trim()}
          title={canManageWorkspace ? "Add user" : workspacePermissionMessage}
        >
          <Plus size={18} />
          <span>Add user</span>
        </button>
      </div>
      <div className="team-form">
        <input value={userForm.name} onChange={(event) => onUserFormChange({ ...userForm, name: event.target.value })} placeholder="Name" />
        <input value={userForm.email} onChange={(event) => onUserFormChange({ ...userForm, email: event.target.value })} placeholder="Email" />
        <select value={userForm.role} onChange={(event) => onUserFormChange({ ...userForm, role: event.target.value as WorkspaceUser["role"] })}>
          <option value="viewer">Viewer</option>
          <option value="editor">Editor</option>
          <option value="reviewer">Reviewer</option>
          <option value="owner">Owner</option>
        </select>
      </div>
      <div className="team-list">
        {users.map((user) => (
          <article className="team-row" key={user.id}>
            <div>
              <strong>{user.name}</strong>
              <span>{user.email || user.id}</span>
            </div>
            <select
              value={user.role}
              onChange={(event) => void onUpdateUserRole(user.id, event.target.value as WorkspaceUser["role"])}
              disabled={busy || !canManageWorkspace || user.id === "local_user"}
            >
              <option value="viewer">Viewer</option>
              <option value="editor">Editor</option>
              <option value="reviewer">Reviewer</option>
              <option value="owner">Owner</option>
            </select>
          </article>
        ))}
      </div>
      {approvalPolicy && approvalPolicyDraft && (
        <div className="approval-policy-box">
          <div className="panel-title">
            <ShieldCheck size={17} />
            <h2>Approval policy</h2>
          </div>
          <div className="policy-grid">
            <label>
              <span>Required reviewers</span>
              <input
                value={approvalPolicyDraft.required_reviewer_count}
                onChange={(event) => onApprovalPolicyDraftChange({ ...approvalPolicyDraft, required_reviewer_count: event.target.value })}
                inputMode="numeric"
              />
            </label>
            <label className="check-field">
              <input
                type="checkbox"
                checked={approvalPolicyDraft.require_approval_before_export}
                onChange={(event) => onApprovalPolicyDraftChange({ ...approvalPolicyDraft, require_approval_before_export: event.target.checked })}
              />
              <span>Require approval before export</span>
            </label>
            <label className="check-field">
              <input
                type="checkbox"
                checked={approvalPolicyDraft.require_approval_before_publish}
                onChange={(event) => onApprovalPolicyDraftChange({ ...approvalPolicyDraft, require_approval_before_publish: event.target.checked })}
              />
              <span>Require approval before publish</span>
            </label>
            <label className="check-field">
              <input
                type="checkbox"
                checked={approvalPolicyDraft.allow_risk_override}
                onChange={(event) => onApprovalPolicyDraftChange({ ...approvalPolicyDraft, allow_risk_override: event.target.checked })}
              />
              <span>Allow logged risk override</span>
            </label>
          </div>
          <button
            className="icon-button"
            onClick={() => void onSaveApprovalPolicy()}
            disabled={busy || !canManageWorkspace}
            title={canManageWorkspace ? "Save approval policy" : workspacePermissionMessage}
          >
            <Save size={18} />
            <span>Save policy</span>
          </button>
        </div>
      )}
    </section>
  );
}
