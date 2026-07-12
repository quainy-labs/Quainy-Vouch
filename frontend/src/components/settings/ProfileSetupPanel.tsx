import { Save, Sparkles } from "lucide-react";
import type {
  AIProviderConnectionTest,
  AIProviderKind,
  AIProviderRuntime,
  AIProviderSettings,
  AIProviderSettingsForm,
  LinkedInIntegration,
  SetupForm,
  SetupSection,
} from "../../types";
import { listToText, textToList } from "../../lib/forms";
import { ErrorList } from "../ui/ErrorList";
import { Field } from "../ui/Field";

type ProfileSetupPanelProps = {
  busy: boolean;
  notice: string;
  canManageWorkspace: boolean;
  workspacePermissionMessage: string;
  eyebrow?: string;
  title?: string;
  saveLabel?: string;
  showPrimaryAction?: boolean;
  sectionIds?: SetupSection[];
  setupForm: SetupForm;
  setupErrors: string[];
  setupSection: SetupSection;
  linkedinIntegration: LinkedInIntegration | null;
  aiProviderSettings: AIProviderSettings | null;
  aiProviderDraft: AIProviderSettingsForm | null;
  aiProviderTest: AIProviderConnectionTest | null;
  onSetupFormChange: (form: SetupForm) => void;
  onSetupSectionChange: (section: SetupSection) => void;
  onLinkedInIntegrationChange: (integration: LinkedInIntegration) => void;
  onAIProviderDraftChange: (draft: AIProviderSettingsForm) => void;
  onSaveSetup: () => void | Promise<void>;
  onSaveAIProviderSettings: () => void | Promise<void>;
  onTestAIProviderSettings: () => void | Promise<void>;
};

const allSetupSections: Array<{ id: SetupSection; label: string }> = [
  { id: "company", label: "Company" },
  { id: "voice", label: "Voice" },
  { id: "claims", label: "Claims" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "ai", label: "AI" },
];

export function ProfileSetupPanel({
  busy,
  notice,
  canManageWorkspace,
  workspacePermissionMessage,
  eyebrow = "Setup",
  title = "Organization and voice profile",
  saveLabel = "Save setup",
  showPrimaryAction = true,
  sectionIds = ["company", "voice", "claims"],
  setupForm,
  setupErrors,
  setupSection,
  linkedinIntegration,
  aiProviderSettings,
  aiProviderDraft,
  aiProviderTest,
  onSetupFormChange,
  onSetupSectionChange,
  onLinkedInIntegrationChange,
  onAIProviderDraftChange,
  onSaveSetup,
  onSaveAIProviderSettings,
  onTestAIProviderSettings,
}: ProfileSetupPanelProps) {
  const visibleSections = allSetupSections.filter((section) => sectionIds.includes(section.id));
  const activeSetupSection = visibleSections.some((section) => section.id === setupSection) ? setupSection : visibleSections[0]?.id ?? "company";

  return (
    <section className="panel band setup-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        {showPrimaryAction && (
          <div className="setup-actions">
            <button
              className="icon-button primary"
              onClick={() => void onSaveSetup()}
              disabled={busy || !canManageWorkspace}
              title={canManageWorkspace ? "Save setup" : workspacePermissionMessage}
            >
              <Save size={18} />
              <span>{saveLabel}</span>
            </button>
          </div>
        )}
      </div>
      <ErrorList errors={setupErrors} />
      {visibleSections.length > 1 && (
        <div className="section-tabs" role="tablist" aria-label="Profile sections">
          {visibleSections.map((section) => (
          <button
            className={activeSetupSection === section.id ? "active" : ""}
            key={section.id}
            onClick={() => onSetupSectionChange(section.id)}
            type="button"
          >
            {section.label}
          </button>
          ))}
        </div>
      )}
      <div className={`setup-grid setup-${activeSetupSection}`}>
        {activeSetupSection === "company" && (
          <>
            <Field label="Organization name">
              <input value={setupForm.name} onChange={(event) => onSetupFormChange({ ...setupForm, name: event.target.value })} />
            </Field>
            <Field label="Website">
              <input
                value={setupForm.website_url}
                onChange={(event) => onSetupFormChange({ ...setupForm, website_url: event.target.value })}
              />
            </Field>
            <Field label="Industry">
              <input value={setupForm.industry} onChange={(event) => onSetupFormChange({ ...setupForm, industry: event.target.value })} />
            </Field>
            <Field label="Timezone">
              <input
                value={setupForm.default_timezone}
                onChange={(event) => onSetupFormChange({ ...setupForm, default_timezone: event.target.value })}
              />
            </Field>
            <Field label="One-liner" wide>
              <input
                value={setupForm.one_liner}
                onChange={(event) => onSetupFormChange({ ...setupForm, one_liner: event.target.value })}
              />
            </Field>
            <Field label="Description" wide>
              <textarea
                className="small-textarea"
                value={setupForm.description}
                onChange={(event) => onSetupFormChange({ ...setupForm, description: event.target.value })}
              />
            </Field>
            <Field label="Audience" wide>
              <textarea
                className="small-textarea"
                value={setupForm.audience_summary}
                onChange={(event) => onSetupFormChange({ ...setupForm, audience_summary: event.target.value })}
              />
            </Field>
          </>
        )}
        {activeSetupSection === "voice" && (
          <>
            <Field label="Content pillars" wide>
              <textarea
                className="list-textarea"
                value={setupForm.content_pillars}
                onChange={(event) => onSetupFormChange({ ...setupForm, content_pillars: event.target.value })}
              />
            </Field>
            <Field label="Voice rules" wide>
              <textarea
                className="list-textarea"
                value={setupForm.voice_rules}
                onChange={(event) => onSetupFormChange({ ...setupForm, voice_rules: event.target.value })}
              />
            </Field>
            <Field label="Preferred phrases">
              <textarea
                className="list-textarea"
                value={setupForm.preferred_phrases}
                onChange={(event) => onSetupFormChange({ ...setupForm, preferred_phrases: event.target.value })}
              />
            </Field>
            <Field label="Banned phrases">
              <textarea
                className="list-textarea"
                value={setupForm.banned_phrases}
                onChange={(event) => onSetupFormChange({ ...setupForm, banned_phrases: event.target.value })}
              />
            </Field>
            <Field label="Sensitive topics" wide>
              <textarea
                className="list-textarea"
                value={setupForm.sensitive_topics}
                onChange={(event) => onSetupFormChange({ ...setupForm, sensitive_topics: event.target.value })}
              />
            </Field>
          </>
        )}
        {activeSetupSection === "claims" && (
          <>
            <Field label="Approved claims" wide>
              <textarea
                className="list-textarea"
                value={setupForm.approved_claims}
                onChange={(event) => onSetupFormChange({ ...setupForm, approved_claims: event.target.value })}
              />
            </Field>
            <Field label="Forbidden claims" wide>
              <textarea
                className="list-textarea"
                value={setupForm.forbidden_claims}
                onChange={(event) => onSetupFormChange({ ...setupForm, forbidden_claims: event.target.value })}
              />
            </Field>
          </>
        )}
        {activeSetupSection === "linkedin" && linkedinIntegration && (
          <>
            <Field label="LinkedIn page URN">
              <input
                value={linkedinIntegration.selected_page_urn ?? ""}
                onChange={(event) => onLinkedInIntegrationChange({ ...linkedinIntegration, selected_page_urn: event.target.value })}
              />
            </Field>
            <Field label="LinkedIn page name">
              <input
                value={linkedinIntegration.selected_page_name ?? ""}
                onChange={(event) => onLinkedInIntegrationChange({ ...linkedinIntegration, selected_page_name: event.target.value })}
              />
            </Field>
            <Field label="LinkedIn OAuth status">
              <select
                value={linkedinIntegration.oauth_status}
                onChange={(event) => onLinkedInIntegrationChange({ ...linkedinIntegration, oauth_status: event.target.value })}
              >
                <option value="not_connected">Not connected</option>
                <option value="validated">Validated</option>
              </select>
            </Field>
            <Field label="LinkedIn permissions" wide>
              <textarea
                className="list-textarea"
                value={listToText(linkedinIntegration.permissions)}
                onChange={(event) => onLinkedInIntegrationChange({ ...linkedinIntegration, permissions: textToList(event.target.value) })}
              />
            </Field>
          </>
        )}
        {activeSetupSection === "ai" && aiProviderDraft && (
          <>
            <Field label="Generation provider">
              <select
                value={aiProviderDraft.generation_provider}
                onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, generation_provider: event.target.value as AIProviderKind })}
              >
                <option value="deterministic">Deterministic fallback</option>
                <option value="openai">OpenAI</option>
                <option value="openai_compatible">OpenAI-compatible</option>
                <option value="local">Local runtime</option>
              </select>
            </Field>
            <Field label="Generation model">
              <input
                value={aiProviderDraft.generation_model}
                onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, generation_model: event.target.value })}
              />
            </Field>
            <Field label="Generation base URL">
              <input
                value={aiProviderDraft.generation_base_url}
                onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, generation_base_url: event.target.value })}
                placeholder="Required for local or compatible providers"
              />
            </Field>
            <Field label="Generation secret reference">
              <input
                value={aiProviderDraft.generation_api_key_env_var}
                onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, generation_api_key_env_var: event.target.value })}
                placeholder="Backend environment variable name"
              />
            </Field>
            <Field label="Embedding provider">
              <select
                value={aiProviderDraft.embedding_provider}
                onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, embedding_provider: event.target.value as AIProviderKind })}
              >
                <option value="deterministic">Local hash</option>
                <option value="openai">OpenAI</option>
                <option value="openai_compatible">OpenAI-compatible</option>
                <option value="local">Local runtime</option>
              </select>
            </Field>
            <Field label="Embedding model">
              <input
                value={aiProviderDraft.embedding_model}
                onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, embedding_model: event.target.value })}
              />
            </Field>
            <Field label="Embedding base URL">
              <input
                value={aiProviderDraft.embedding_base_url}
                onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, embedding_base_url: event.target.value })}
                placeholder="Required for local or compatible providers"
              />
            </Field>
            <Field label="Embedding secret reference">
              <input
                value={aiProviderDraft.embedding_api_key_env_var}
                onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, embedding_api_key_env_var: event.target.value })}
                placeholder="Backend environment variable name"
              />
            </Field>
            <Field label="Local runtime">
              <select
                value={aiProviderDraft.local_runtime}
                onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, local_runtime: event.target.value as AIProviderRuntime })}
              >
                <option value="none">None</option>
                <option value="ollama">Ollama</option>
                <option value="vllm">vLLM</option>
                <option value="lm_studio">LM Studio</option>
                <option value="custom">Custom</option>
              </select>
            </Field>
            <label className="check-field provider-enabled">
              <input
                type="checkbox"
                checked={aiProviderDraft.enabled}
                onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, enabled: event.target.checked })}
              />
              <span>Use these settings for organization reasoning</span>
            </label>
            <div className="provider-actions">
              <button
                className="icon-button"
                onClick={() => void onSaveAIProviderSettings()}
                disabled={busy || !canManageWorkspace}
                title={canManageWorkspace ? "Save AI provider settings" : workspacePermissionMessage}
                type="button"
              >
                <Save size={18} />
                <span>Save AI</span>
              </button>
              <button
                className="icon-button"
                onClick={() => void onTestAIProviderSettings()}
                disabled={busy || !canManageWorkspace}
                title={canManageWorkspace ? "Test AI provider" : workspacePermissionMessage}
                type="button"
              >
                <Sparkles size={18} />
                <span>Test</span>
              </button>
            </div>
            {aiProviderSettings && (
              <p className="provider-status">
                Generation secret {aiProviderSettings.generation_api_key_configured ? "referenced" : "not referenced"}. Embedding secret{" "}
                {aiProviderSettings.embedding_api_key_configured ? "referenced" : "not referenced"}.
              </p>
            )}
            {aiProviderTest && (
              <p className={`provider-status ${aiProviderTest.status}`}>
                {aiProviderTest.status === "succeeded" ? "Connected" : "Check configuration"}: {aiProviderTest.message}
              </p>
            )}
          </>
        )}
      </div>
      {notice && <p className="notice">{notice}</p>}
    </section>
  );
}
