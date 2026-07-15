import { useState } from "react";
import { ExternalLink, Save, Sparkles } from "lucide-react";
import type {
  AICloudService,
  AIProviderConnectionTest,
  AIProviderKind,
  AIProviderRuntime,
  AIProviderSettings,
  AIProviderSettingsForm,
  LinkedInIntegration,
  PublishingConnection,
  PublishingOAuthStart,
  SetupForm,
  SetupSection,
} from "../../types";
import { api } from "../../lib/api";
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
  publishingConnections?: PublishingConnection[];
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
  { id: "linkedin", label: "Publishing" },
  { id: "ai", label: "AI" },
];

type PublishingProvider = "linkedin" | "reddit" | "instagram";

const publishingConnectors: Array<{ id: PublishingProvider; label: string; scope: string; requiredEnv: string[] }> = [
  {
    id: "linkedin",
    label: "LinkedIn",
    scope: "Read page context and create posts",
    requiredEnv: ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_REDIRECT_URI"],
  },
  {
    id: "reddit",
    label: "Reddit",
    scope: "Read community context and create posts",
    requiredEnv: ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_REDIRECT_URI"],
  },
  {
    id: "instagram",
    label: "Instagram",
    scope: "Read account context and create posts",
    requiredEnv: ["INSTAGRAM_CLIENT_ID", "INSTAGRAM_CLIENT_SECRET", "INSTAGRAM_REDIRECT_URI"],
  },
];

type ProviderField = "generation" | "embedding";

type CloudServicePreset = {
  label: string;
  baseUrl: string;
  baseUrlPlaceholder: string;
  secretReference: string;
  modelPlaceholder: string;
};

type LocalRuntimePreset = {
  label: string;
  baseUrl: string;
  baseUrlPlaceholder: string;
};

const cloudServicePresets: Record<AICloudService, CloudServicePreset> = {
  openai: {
    label: "OpenAI / ChatGPT",
    baseUrl: "https://api.openai.com/v1",
    baseUrlPlaceholder: "https://api.openai.com/v1",
    secretReference: "OPENAI_API_KEY",
    modelPlaceholder: "OpenAI model name",
  },
  grok: {
    label: "Grok",
    baseUrl: "https://api.x.ai/v1",
    baseUrlPlaceholder: "https://api.x.ai/v1",
    secretReference: "XAI_API_KEY",
    modelPlaceholder: "Grok model name",
  },
  claude: {
    label: "Claude",
    baseUrl: "",
    baseUrlPlaceholder: "Claude-compatible gateway base URL",
    secretReference: "ANTHROPIC_API_KEY",
    modelPlaceholder: "Claude model name",
  },
  gemini: {
    label: "Gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/",
    baseUrlPlaceholder: "https://generativelanguage.googleapis.com/v1beta/openai/",
    secretReference: "GEMINI_API_KEY",
    modelPlaceholder: "Gemini model name",
  },
  other: {
    label: "Other cloud LLM",
    baseUrl: "",
    baseUrlPlaceholder: "Provider or gateway base URL",
    secretReference: "",
    modelPlaceholder: "Provider model name",
  },
};

const cloudServiceOptions = Object.entries(cloudServicePresets) as Array<[AICloudService, CloudServicePreset]>;

const localRuntimePresets: Record<AIProviderRuntime, LocalRuntimePreset> = {
  none: {
    label: "None",
    baseUrl: "",
    baseUrlPlaceholder: "Local runtime base URL",
  },
  ollama: {
    label: "Ollama",
    baseUrl: "http://localhost:11434/v1",
    baseUrlPlaceholder: "http://localhost:11434/v1",
  },
  vllm: {
    label: "vLLM",
    baseUrl: "http://localhost:8000/v1",
    baseUrlPlaceholder: "http://localhost:8000/v1",
  },
  lm_studio: {
    label: "LM Studio",
    baseUrl: "http://localhost:1234/v1",
    baseUrlPlaceholder: "http://localhost:1234/v1",
  },
  custom: {
    label: "Custom",
    baseUrl: "",
    baseUrlPlaceholder: "Custom local runtime base URL",
  },
};

const localRuntimeOptions = Object.entries(localRuntimePresets) as Array<[AIProviderRuntime, LocalRuntimePreset]>;

function applyCloudServicePreset(draft: AIProviderSettingsForm, field: ProviderField, service: AICloudService): AIProviderSettingsForm {
  const preset = cloudServicePresets[service];
  if (field === "generation") {
    if (service === "gemini") {
      return {
        ...draft,
        generation_provider: "gemini",
        generation_cloud_service: service,
        generation_base_url: "",
        generation_api_key_env_var: preset.secretReference,
        generation_model: shouldClearProviderModel(draft.generation_model) ? "" : draft.generation_model,
      };
    }
    return {
      ...draft,
      generation_provider: "openai_compatible",
      generation_cloud_service: service,
      generation_base_url: preset.baseUrl,
      generation_api_key_env_var: preset.secretReference,
      generation_model: shouldClearProviderModel(draft.generation_model) ? "" : draft.generation_model,
    };
  }
  return {
    ...draft,
    embedding_provider: "openai_compatible",
    embedding_cloud_service: service,
    embedding_base_url: preset.baseUrl,
    embedding_api_key_env_var: preset.secretReference,
    embedding_model: shouldClearProviderModel(draft.embedding_model) ? "" : draft.embedding_model,
  };
}

function applyProviderChoice(draft: AIProviderSettingsForm, field: ProviderField, provider: AIProviderKind): AIProviderSettingsForm {
  if (provider === "openai_compatible") {
    const service = field === "generation" ? draft.generation_cloud_service : draft.embedding_cloud_service;
    return applyCloudServicePreset(draft, field, service);
  }
  if (provider === "local") {
    const runtime = field === "generation" ? draft.generation_local_runtime : draft.embedding_local_runtime;
    return applyLocalRuntimePreset(draft, field, runtime);
  }
  if (provider === "gemini" && field === "generation") {
    return {
      ...draft,
      generation_provider: "gemini",
      generation_cloud_service: "gemini",
      generation_base_url: "",
      generation_api_key_env_var: "GEMINI_API_KEY",
      generation_model: shouldClearProviderModel(draft.generation_model) ? "" : draft.generation_model,
    };
  }
  if (field === "generation") {
    return {
      ...draft,
      generation_provider: provider,
      generation_model: provider === "deterministic" ? "deterministic-structured-v1" : draft.generation_model,
      generation_base_url: provider === "deterministic" ? "" : draft.generation_base_url,
      generation_api_key_env_var: provider === "deterministic" ? "" : draft.generation_api_key_env_var,
    };
  }
  return {
    ...draft,
    embedding_provider: provider,
    embedding_model: provider === "deterministic" ? "local-hash" : draft.embedding_model,
    embedding_base_url: provider === "deterministic" ? "" : draft.embedding_base_url,
    embedding_api_key_env_var: provider === "deterministic" ? "" : draft.embedding_api_key_env_var,
  };
}

function applyLocalRuntimePreset(draft: AIProviderSettingsForm, field: ProviderField, runtime: AIProviderRuntime): AIProviderSettingsForm {
  const preset = localRuntimePresets[runtime];
  if (field === "generation") {
    return {
      ...draft,
      generation_provider: "local",
      generation_local_runtime: runtime,
      generation_base_url: preset.baseUrl,
      generation_api_key_env_var: "",
      generation_model: shouldClearProviderModel(draft.generation_model) ? "" : draft.generation_model,
    };
  }
  return {
    ...draft,
    embedding_provider: "local",
    embedding_local_runtime: runtime,
    embedding_base_url: preset.baseUrl,
    embedding_api_key_env_var: "",
    embedding_model: shouldClearProviderModel(draft.embedding_model) ? "" : draft.embedding_model,
  };
}

function shouldClearProviderModel(model: string): boolean {
  return ["", "deterministic-structured-v1", "local-hash", "llama3.1", "nomic-embed-text"].includes(model.trim());
}

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
  publishingConnections = [],
  aiProviderSettings,
  aiProviderDraft,
  aiProviderTest,
  onSetupFormChange,
  onSetupSectionChange,
  onAIProviderDraftChange,
  onSaveSetup,
  onSaveAIProviderSettings,
  onTestAIProviderSettings,
}: ProfileSetupPanelProps) {
  const [publishingSetupProvider, setPublishingSetupProvider] = useState<PublishingProvider | null>(null);
  const [publishingSetupMessage, setPublishingSetupMessage] = useState("");
  const visibleSections = allSetupSections.filter((section) => sectionIds.includes(section.id));
  const activeSetupSection = visibleSections.some((section) => section.id === setupSection) ? setupSection : visibleSections[0]?.id ?? "company";
  const publishingOrganizationId = linkedinIntegration?.organization_id;

  async function connectPublishingProvider(provider: PublishingProvider) {
    if (!publishingOrganizationId) return;
    try {
      setPublishingSetupProvider(null);
      setPublishingSetupMessage("");
      const response = await api<PublishingOAuthStart>(`/organizations/${publishingOrganizationId}/publishing-connections/${provider}/oauth/start`, {
        method: "POST",
      });
      const oauthWindow = window.open(response.authorization_url, "_blank", "noopener,noreferrer");
      if (!oauthWindow) {
        setPublishingSetupProvider(provider);
        setPublishingSetupMessage("Your browser blocked the OAuth popup. Allow popups for this site, then click Connect again.");
      }
    } catch (error) {
      setPublishingSetupProvider(provider);
      setPublishingSetupMessage(error instanceof Error ? error.message : "Publishing connection is not configured.");
    }
  }
  const publishingConnectionByProvider = new Map(publishingConnections.map((connection) => [connection.provider, connection]));

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
          <div className="publishing-connectors">
            {publishingConnectors.map((connector) => {
              const connection = publishingConnectionByProvider.get(connector.id);
              const connected =
                connection?.oauth_status === "validated" ||
                (connector.id === "linkedin" && linkedinIntegration.oauth_status === "validated");
              return (
                <article className="publishing-connector" key={connector.id}>
                  <div className="publishing-connector-body">
                    <strong>{connector.label}</strong>
                    <span>{connected ? "Connected" : "Not connected"}</span>
                    <small>{connector.scope}</small>
                    {(connection?.selected_target_name || connection?.account_name) && (
                      <small>{connection.selected_target_name || connection.account_name}</small>
                    )}
                  </div>
                  <button
                    className={connected ? "icon-button" : "icon-button primary"}
                    disabled={busy || !canManageWorkspace}
                    onClick={() => void connectPublishingProvider(connector.id)}
                    title={canManageWorkspace ? `Connect ${connector.label}` : workspacePermissionMessage}
                    type="button"
                  >
                    <ExternalLink size={18} />
                    <span>{connected ? "Reconnect" : "Connect"}</span>
                  </button>
                  {publishingSetupProvider === connector.id && (
                    <div className="publishing-connector-setup">
                      <strong>Backend OAuth setup required</strong>
                      <span>{publishingSetupMessage || `${connector.label} OAuth is not configured.`}</span>
                      <small>Set these environment variables on the backend, restart it, then click Connect again.</small>
                      <div className="publishing-connector-env" aria-label={`${connector.label} OAuth environment variables`}>
                        {connector.requiredEnv.map((envName) => (
                          <code key={envName}>{envName}</code>
                        ))}
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
        {activeSetupSection === "ai" && aiProviderDraft && (
          <>
            <fieldset className="ai-provider-section">
              <legend>Generation</legend>
              <Field label="Provider">
                <select
                  value={aiProviderDraft.generation_provider}
                  onChange={(event) => onAIProviderDraftChange(applyProviderChoice(aiProviderDraft, "generation", event.target.value as AIProviderKind))}
                >
                  <option value="deterministic">Deterministic fallback</option>
                  <option value="gemini">Gemini</option>
                  <option value="local">Local runtime</option>
                  <option value="openai_compatible">Cloud LLM provider</option>
                </select>
              </Field>
              {aiProviderDraft.generation_provider === "openai_compatible" && (
                <Field label="Cloud service">
                  <select
                    value={aiProviderDraft.generation_cloud_service}
                    onChange={(event) => onAIProviderDraftChange(applyCloudServicePreset(aiProviderDraft, "generation", event.target.value as AICloudService))}
                  >
                    {cloudServiceOptions.map(([value, preset]) => (
                      <option key={value} value={value}>
                        {preset.label}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              <Field label="Model">
                <input
                  value={aiProviderDraft.generation_model}
                  onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, generation_model: event.target.value })}
                  placeholder={
                    aiProviderDraft.generation_provider === "openai_compatible"
                      ? cloudServicePresets[aiProviderDraft.generation_cloud_service].modelPlaceholder
                      : aiProviderDraft.generation_provider === "gemini"
                        ? cloudServicePresets.gemini.modelPlaceholder
                      : undefined
                  }
                />
              </Field>
              {aiProviderDraft.generation_provider === "local" && (
                <Field label="Local runtime">
                  <select
                    value={aiProviderDraft.generation_local_runtime}
                    onChange={(event) => onAIProviderDraftChange(applyLocalRuntimePreset(aiProviderDraft, "generation", event.target.value as AIProviderRuntime))}
                  >
                    {localRuntimeOptions.map(([value, preset]) => (
                      <option key={value} value={value}>
                        {preset.label}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              {aiProviderDraft.generation_provider !== "deterministic" && aiProviderDraft.generation_provider !== "gemini" && (
                <Field label="Base URL">
                  <input
                    value={aiProviderDraft.generation_base_url}
                    onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, generation_base_url: event.target.value })}
                    placeholder={
                      aiProviderDraft.generation_provider === "openai_compatible"
                        ? cloudServicePresets[aiProviderDraft.generation_cloud_service].baseUrlPlaceholder
                        : localRuntimePresets[aiProviderDraft.generation_local_runtime].baseUrlPlaceholder
                    }
                  />
                </Field>
              )}
              {aiProviderDraft.generation_provider !== "deterministic" && (
                <Field label="Secret reference">
                  <input
                    value={aiProviderDraft.generation_api_key_env_var}
                    onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, generation_api_key_env_var: event.target.value })}
                    placeholder={
                      aiProviderDraft.generation_provider === "openai_compatible"
                        ? cloudServicePresets[aiProviderDraft.generation_cloud_service].secretReference || "Backend environment variable name"
                        : aiProviderDraft.generation_provider === "gemini"
                          ? cloudServicePresets.gemini.secretReference
                        : "Optional local runtime secret reference"
                    }
                  />
                </Field>
              )}
              {aiProviderTest && (
                <p className={`provider-status ${aiProviderTest.generation.status}`}>
                  {aiProviderTest.generation.status === "succeeded" ? "Generation connected" : "Check generation"}: {aiProviderTest.generation.message}
                </p>
              )}
            </fieldset>
            <fieldset className="ai-provider-section">
              <legend>Embedding</legend>
              <Field label="Provider">
                <select
                  value={aiProviderDraft.embedding_provider}
                  onChange={(event) => onAIProviderDraftChange(applyProviderChoice(aiProviderDraft, "embedding", event.target.value as AIProviderKind))}
                >
                  <option value="deterministic">Deterministic fallback</option>
                  <option value="local">Local runtime</option>
                  <option value="openai_compatible">Cloud LLM provider</option>
                </select>
              </Field>
              {aiProviderDraft.embedding_provider === "openai_compatible" && (
                <Field label="Cloud service">
                  <select
                    value={aiProviderDraft.embedding_cloud_service}
                    onChange={(event) => onAIProviderDraftChange(applyCloudServicePreset(aiProviderDraft, "embedding", event.target.value as AICloudService))}
                  >
                    {cloudServiceOptions.map(([value, preset]) => (
                      <option key={value} value={value}>
                        {preset.label}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              <Field label="Model">
                <input
                  value={aiProviderDraft.embedding_model}
                  onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, embedding_model: event.target.value })}
                  placeholder={
                    aiProviderDraft.embedding_provider === "openai_compatible"
                      ? cloudServicePresets[aiProviderDraft.embedding_cloud_service].modelPlaceholder
                      : undefined
                  }
                />
              </Field>
              {aiProviderDraft.embedding_provider === "local" && (
                <Field label="Local runtime">
                  <select
                    value={aiProviderDraft.embedding_local_runtime}
                    onChange={(event) => onAIProviderDraftChange(applyLocalRuntimePreset(aiProviderDraft, "embedding", event.target.value as AIProviderRuntime))}
                  >
                    {localRuntimeOptions.map(([value, preset]) => (
                      <option key={value} value={value}>
                        {preset.label}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              {aiProviderDraft.embedding_provider !== "deterministic" && (
                <Field label="Base URL">
                  <input
                    value={aiProviderDraft.embedding_base_url}
                    onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, embedding_base_url: event.target.value })}
                    placeholder={
                      aiProviderDraft.embedding_provider === "openai_compatible"
                        ? cloudServicePresets[aiProviderDraft.embedding_cloud_service].baseUrlPlaceholder
                        : localRuntimePresets[aiProviderDraft.embedding_local_runtime].baseUrlPlaceholder
                    }
                  />
                </Field>
              )}
              {aiProviderDraft.embedding_provider !== "deterministic" && (
                <Field label="Secret reference">
                  <input
                    value={aiProviderDraft.embedding_api_key_env_var}
                    onChange={(event) => onAIProviderDraftChange({ ...aiProviderDraft, embedding_api_key_env_var: event.target.value })}
                    placeholder={
                      aiProviderDraft.embedding_provider === "openai_compatible"
                        ? cloudServicePresets[aiProviderDraft.embedding_cloud_service].secretReference || "Backend environment variable name"
                        : "Optional local runtime secret reference"
                    }
                  />
                </Field>
              )}
              {aiProviderTest && (
                <p className={`provider-status ${aiProviderTest.embedding.status}`}>
                  {aiProviderTest.embedding.status === "succeeded" ? "Embedding connected" : "Check embedding"}: {aiProviderTest.embedding.message}
                </p>
              )}
            </fieldset>
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
          </>
        )}
      </div>
      {notice && <p className="notice">{notice}</p>}
    </section>
  );
}
