import { api } from "../../lib/api";
import {
  aiProviderPayload,
  aiProviderSettingsForm,
  approvalPolicyForm,
  setupFromBootstrap,
  textToList,
  validateAIProviderForm,
  validateSetupForm,
} from "../../lib/forms";
import { saveWorkspaceView } from "../../lib/studioSelection";
import type {
  AIProviderConnectionTest,
  AIProviderSettings,
  ApprovalPolicy,
  DeletionReceipt,
  LinkedInIntegration,
  OnboardingState,
  Organization,
  Profile,
  WorkspaceUser,
} from "../../types";
import type { WorkspaceControllerState } from "./useWorkspaceControllerState";

type SettingsActionsOptions = {
  canManageWorkspace: boolean;
  workspacePermissionMessage: string;
  requirePermission: (allowed: boolean, message: string) => boolean;
  refreshCurrentWorkspaceState: () => Promise<unknown>;
  refreshKnowledgeReadiness: (organizationId?: string) => Promise<void>;
};

export function createSettingsActions(state: WorkspaceControllerState, options: SettingsActionsOptions) {
  function setWorkspaceView(view: "settings" | "sources") {
    state.setActiveView(view);
    if (state.bootstrap) {
      saveWorkspaceView(state.bootstrap.organization.id, view);
    }
  }

  function clearWorkspaceAfterLifecycleAction() {
    state.setCurrentUser(null);
    state.setOnboarding(null);
    state.setBootstrap(null);
    state.setOpportunities([]);
    state.setSelectedOpportunity(null);
    state.setSelectedBrief(null);
    state.setDrafts([]);
    state.setSelectedDraft(null);
    state.setContentArtifacts([]);
    state.setJobs([]);
    state.setAuthMode("login");
    state.setAuthRequired(true);
    state.setActiveView("settings");
  }

  async function skipProfileForNow() {
    if (!state.bootstrap) return;
    state.setBusy(true);
    try {
      const onboarding = await api<OnboardingState>(`/organizations/${state.bootstrap.organization.id}/onboarding/profile`, {
        method: "POST",
        body: JSON.stringify({ skip_profile: true }),
      });
      state.setOnboarding(onboarding);
      setWorkspaceView("sources");
      state.setNotice("Profile setup skipped for now. Add an approved source to improve recommendations.");
    } finally {
      state.setBusy(false);
    }
  }

  async function saveSetup() {
    if (!state.bootstrap || !state.setupForm) return;
    if (!options.requirePermission(options.canManageWorkspace, options.workspacePermissionMessage)) return;
    const errors = validateSetupForm(state.setupForm);
    state.setSetupErrors(errors);
    if (errors.length > 0) return;
    state.setBusy(true);
    try {
      const organization = await api<Organization>(`/organizations/${state.bootstrap.organization.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: state.setupForm.name,
          website_url: state.setupForm.website_url || null,
          industry: state.setupForm.industry || null,
          description: state.setupForm.description || null,
          audience_summary: state.setupForm.audience_summary || null,
          default_timezone: state.setupForm.default_timezone || "UTC",
        }),
      });
      const profile = await api<Profile>(`/organizations/${state.bootstrap.organization.id}/profile`, {
        method: "PATCH",
        body: JSON.stringify({
          one_liner: state.setupForm.one_liner,
          mission: state.setupForm.description,
          product_summary: state.setupForm.description,
          audience: state.setupForm.audience_summary,
          voice_rules: textToList(state.setupForm.voice_rules),
          preferred_phrases: textToList(state.setupForm.preferred_phrases),
          banned_phrases: textToList(state.setupForm.banned_phrases),
          approved_claims: textToList(state.setupForm.approved_claims),
          forbidden_claims: textToList(state.setupForm.forbidden_claims),
          content_pillars: textToList(state.setupForm.content_pillars),
          sensitive_topics: textToList(state.setupForm.sensitive_topics),
        }),
      });
      if (state.linkedinIntegration) {
        state.setLinkedinIntegration(
          await api<LinkedInIntegration>(`/organizations/${state.bootstrap.organization.id}/linkedin-integration`, {
            method: "PATCH",
            body: JSON.stringify({
              selected_page_urn: state.linkedinIntegration.selected_page_urn || null,
              selected_page_name: state.linkedinIntegration.selected_page_name || null,
              oauth_status: state.linkedinIntegration.oauth_status || "not_connected",
              permissions: state.linkedinIntegration.permissions,
              publishing_enabled: state.linkedinIntegration.publishing_enabled,
            }),
          }),
        );
      }
      const nextBootstrap = { ...state.bootstrap, organization, profile };
      state.setBootstrap(nextBootstrap);
      state.setSetupForm(setupFromBootstrap(nextBootstrap));
      state.setSelectedBrief(null);
      state.setDrafts([]);
      state.setSelectedDraft(null);
      await options.refreshKnowledgeReadiness(state.bootstrap.organization.id);
      await options.refreshCurrentWorkspaceState();
      state.setSetupErrors([]);
      state.setNotice("Workspace and voice profile saved.");
    } catch (error) {
      state.setSetupErrors((error instanceof Error ? error.message : "Workspace setup failed.").split("\n"));
      state.setNotice(error instanceof Error ? error.message : "Workspace setup failed.");
    } finally {
      state.setBusy(false);
    }
  }

  async function refreshUsers() {
    if (!state.bootstrap) return;
    state.setUsers(await api<WorkspaceUser[]>(`/organizations/${state.bootstrap.organization.id}/users`));
  }

  async function addUser() {
    if (!state.bootstrap || !state.userForm.name.trim()) return;
    if (!options.requirePermission(options.canManageWorkspace, options.workspacePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api<WorkspaceUser>(`/organizations/${state.bootstrap.organization.id}/users`, {
        method: "POST",
        body: JSON.stringify({
          name: state.userForm.name,
          email: state.userForm.email || null,
          role: state.userForm.role,
        }),
      });
      state.setUserForm({ name: "", email: "", role: "viewer" });
      await refreshUsers();
      state.setNotice("Team user added.");
    } finally {
      state.setBusy(false);
    }
  }

  async function updateUserRole(userId: string, role: WorkspaceUser["role"]) {
    if (!state.bootstrap) return;
    if (!options.requirePermission(options.canManageWorkspace, options.workspacePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api<WorkspaceUser>(`/organizations/${state.bootstrap.organization.id}/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      await refreshUsers();
      state.setNotice("User role updated.");
    } finally {
      state.setBusy(false);
    }
  }

  async function saveApprovalPolicy() {
    if (!state.bootstrap || !state.approvalPolicyDraft) return;
    if (!options.requirePermission(options.canManageWorkspace, options.workspacePermissionMessage)) return;
    state.setBusy(true);
    try {
      const policy = await api<ApprovalPolicy>(`/organizations/${state.bootstrap.organization.id}/approval-policy`, {
        method: "PATCH",
        body: JSON.stringify({
          required_reviewer_count: Number(state.approvalPolicyDraft.required_reviewer_count) || 1,
          require_approval_before_export: state.approvalPolicyDraft.require_approval_before_export,
          require_approval_before_publish: state.approvalPolicyDraft.require_approval_before_publish,
          allow_risk_override: state.approvalPolicyDraft.allow_risk_override,
        }),
      });
      state.setApprovalPolicy(policy);
      state.setApprovalPolicyDraft(approvalPolicyForm(policy));
      state.setNotice("Approval policy saved.");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Approval policy update failed.");
    } finally {
      state.setBusy(false);
    }
  }

  async function saveAIProviderSettings() {
    if (!state.bootstrap || !state.aiProviderDraft) return;
    if (!options.requirePermission(options.canManageWorkspace, options.workspacePermissionMessage)) return;
    const errors = validateAIProviderForm(state.aiProviderDraft);
    if (errors.length > 0) {
      state.setNotice(errors.join("\n"));
      return;
    }
    state.setBusy(true);
    try {
      const settings = await api<AIProviderSettings>(`/organizations/${state.bootstrap.organization.id}/ai-provider-settings`, {
        method: "PATCH",
        body: JSON.stringify(aiProviderPayload(state.aiProviderDraft)),
      });
      state.setAiProviderSettings(settings);
      state.setAiProviderDraft(aiProviderSettingsForm(settings));
      state.setNotice("AI provider settings saved.");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "AI provider settings update failed.");
    } finally {
      state.setBusy(false);
    }
  }

  async function testAIProviderSettings() {
    if (!state.bootstrap || !state.aiProviderDraft) return;
    const errors = validateAIProviderForm(state.aiProviderDraft);
    if (errors.length > 0) {
      state.setNotice(errors.join("\n"));
      return;
    }
    state.setBusy(true);
    try {
      const savedSettings = await api<AIProviderSettings>(`/organizations/${state.bootstrap.organization.id}/ai-provider-settings`, {
        method: "PATCH",
        body: JSON.stringify(aiProviderPayload(state.aiProviderDraft)),
      });
      state.setAiProviderSettings(savedSettings);
      state.setAiProviderDraft(aiProviderSettingsForm(savedSettings));
      const result = await api<AIProviderConnectionTest>(`/organizations/${state.bootstrap.organization.id}/ai-provider-settings/test`, {
        method: "POST",
      });
      state.setAiProviderTest(result);
      state.setNotice(result.message);
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "AI provider test failed.");
    } finally {
      state.setBusy(false);
    }
  }

  async function deactivateOrganization() {
    if (!state.bootstrap) return;
    if (!options.requirePermission(options.canManageWorkspace, options.workspacePermissionMessage)) return;
    state.setBusy(true);
    try {
      const organization = await api<Organization>(`/organizations/${state.bootstrap.organization.id}/deactivate`, { method: "POST" });
      state.setBootstrap((current) => (current ? { ...current, organization } : current));
      state.setNotice("Organization deactivated.");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Organization deactivation failed.");
    } finally {
      state.setBusy(false);
    }
  }

  async function activateOrganization() {
    if (!state.bootstrap) return;
    if (!options.requirePermission(options.canManageWorkspace, options.workspacePermissionMessage)) return;
    state.setBusy(true);
    try {
      const organization = await api<Organization>(`/organizations/${state.bootstrap.organization.id}/activate`, { method: "POST" });
      state.setBootstrap((current) => (current ? { ...current, organization } : current));
      state.setNotice("Organization activated.");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Organization activation failed.");
    } finally {
      state.setBusy(false);
    }
  }

  async function deleteOrganization() {
    if (!state.bootstrap) return;
    if (!options.requirePermission(options.canManageWorkspace, options.workspacePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api<DeletionReceipt>(`/organizations/${state.bootstrap.organization.id}`, { method: "DELETE" });
      clearWorkspaceAfterLifecycleAction();
      state.setNotice("Organization deleted.");
    } catch (error) {
      state.setNotice(error instanceof Error ? error.message : "Organization deletion failed.");
    } finally {
      state.setBusy(false);
    }
  }

  return {
    activateOrganization,
    addUser,
    deactivateOrganization,
    deleteOrganization,
    refreshUsers,
    saveAIProviderSettings,
    saveApprovalPolicy,
    saveSetup,
    skipProfileForNow,
    testAIProviderSettings,
    updateUserRole,
  };
}
