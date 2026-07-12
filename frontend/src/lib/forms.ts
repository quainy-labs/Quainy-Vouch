import type {
  AIProviderSettings,
  AIProviderSettingsForm,
  ApprovalPolicy,
  ApprovalPolicyForm,
  AuthForm,
  Bootstrap,
  CurrentWorkspace,
  Draft,
  FormatChoice,
  MetricsForm,
  Opportunity,
  SetupForm,
  SourceForm,
  TrendSignalForm,
  UserForm,
  CalendarEventForm
} from "../types";

export function listToText(values: string[] | undefined): string {
  return (values ?? []).join("\n");
}

export function textToList(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function validateEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export function validateHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export function validateAuthForm(form: AuthForm, mode: "signup" | "login"): string[] {
  const errors: string[] = [];
  if (!validateEmail(form.email)) errors.push("Enter a valid email address.");
  if (!form.password.trim()) {
    errors.push("Password is required.");
  } else if (mode === "signup" && form.password.trim().length < 8) {
    errors.push("Password must be at least 8 characters.");
  }
  if (mode === "signup") {
    if (!form.name.trim()) errors.push("Your name is required.");
    if (!form.organization_name.trim()) errors.push("Organization name is required.");
    if (form.website_url.trim() && !validateHttpUrl(form.website_url)) errors.push("Website must be a valid http(s) URL.");
  }
  return errors;
}

export function validateSetupForm(form: SetupForm): string[] {
  const errors: string[] = [];
  if (!form.name.trim()) errors.push("Organization name is required.");
  if (!form.default_timezone.trim()) errors.push("Timezone is required.");
  if (form.website_url.trim() && !validateHttpUrl(form.website_url)) errors.push("Website must be a valid http(s) URL.");
  return errors;
}

export function validateSourceForm(form: SourceForm): string[] {
  const errors: string[] = [];
  const rawText = form.raw_text.trim();
  const uri = form.uri.trim();
  if (!form.title.trim()) errors.push("Source title is required.");
  if (rawText.length < 20) errors.push("Source text must contain at least 20 characters.");
  if (Number(form.freshness_days) < 1) errors.push("Freshness window must be at least 1 day.");
  if (form.source_type === "url") {
    if (!uri) errors.push("Public page URL is required.");
    if (uri && !validateHttpUrl(uri)) errors.push("Public page URL must be a valid http(s) URL.");
  }
  if (form.source_type === "github_release") {
    if (!uri) errors.push("GitHub release or repo URL is required.");
    if (uri && (!validateHttpUrl(uri) || new URL(uri).hostname.toLowerCase() !== "github.com")) {
      errors.push("GitHub source must be a valid github.com URL.");
    }
  }
  if (form.source_type === "notion_page") {
    const isNotionProtocol = uri.startsWith("notion://page/");
    const isNotionUrl = validateHttpUrl(uri) && new URL(uri).hostname.endsWith("notion.so");
    if (!uri) errors.push("Notion page URL is required.");
    if (uri && !isNotionProtocol && !isNotionUrl) errors.push("Notion source must be a selected Notion page URL.");
  }
  return errors;
}

export function draftFormatLabel(draft: Draft | null): string {
  if (!draft) return "Draft";
  if (draft.platform === "blog") return "Blog outline";
  if (draft.platform === "newsletter") return "Newsletter email";
  if (draft.platform === "instagram" && draft.content_type === "carousel_outline") return "Instagram carousel";
  if (draft.platform === "instagram") return "Instagram caption";
  return "LinkedIn company post";
}

export function platformDisplayName(platform: string): string {
  if (platform === "linkedin") return "LinkedIn";
  if (platform === "blog") return "Blog";
  if (platform === "newsletter") return "Newsletter";
  if (platform === "instagram") return "Instagram";
  return platform || "Platform";
}

export function contentTypeDisplayName(contentType: string): string {
  return contentType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function auditTimeValue(value: string): number {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function formatAuditTime(value: string): string {
  const parsed = auditTimeValue(value);
  if (!parsed) return value;
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
    timeZoneName: "short",
  }).format(new Date(parsed));
}

export function formatChoiceParams(choice: FormatChoice): string {
  const params: Record<FormatChoice, string> = {
    linkedin_company_post: "?platform=linkedin&content_type=company_post",
    blog_outline: "?platform=blog&content_type=outline",
    newsletter_email: "?platform=newsletter&content_type=email",
    instagram_caption: "?platform=instagram&content_type=caption",
    instagram_carousel_outline: "?platform=instagram&content_type=carousel_outline",
  };
  return params[choice];
}

export function formatChoiceNotice(choice: FormatChoice): string {
  const notices: Record<FormatChoice, string> = {
    linkedin_company_post: "LinkedIn variants generated from the selected brief.",
    blog_outline: "Blog outline variants generated from the selected brief.",
    newsletter_email: "Newsletter email variants generated from the selected brief.",
    instagram_caption: "Instagram caption variants generated from the selected brief.",
    instagram_carousel_outline: "Instagram carousel variants generated from the selected brief.",
  };
  return notices[choice];
}

export function formatChoiceLabel(choice: FormatChoice): string {
  const labels: Record<FormatChoice, string> = {
    linkedin_company_post: "LinkedIn company post",
    blog_outline: "Blog article outline",
    newsletter_email: "Newsletter email",
    instagram_caption: "Instagram caption",
    instagram_carousel_outline: "Instagram carousel outline",
  };
  return labels[choice];
}

export function formatChoicePlatform(choice: FormatChoice): { platform: string; contentType: string } {
  const formats: Record<FormatChoice, { platform: string; contentType: string }> = {
    linkedin_company_post: { platform: "linkedin", contentType: "company_post" },
    blog_outline: { platform: "blog", contentType: "outline" },
    newsletter_email: { platform: "newsletter", contentType: "email" },
    instagram_caption: { platform: "instagram", contentType: "caption" },
    instagram_carousel_outline: { platform: "instagram", contentType: "carousel_outline" },
  };
  return formats[choice];
}

export function summarizeNames(names: string[], limit = 3): string {
  if (names.length === 0) return "";
  const visible = names.slice(0, limit).join(", ");
  const remaining = names.length - limit;
  return remaining > 0 ? `${visible} + ${remaining} more` : visible;
}

export function setupFromBootstrap(data: Bootstrap): SetupForm {
  return {
    name: data.organization.name ?? "",
    website_url: data.organization.website_url ?? "",
    industry: data.organization.industry ?? "",
    description: data.organization.description ?? data.profile.product_summary ?? data.profile.mission ?? "",
    audience_summary: data.organization.audience_summary ?? data.profile.audience ?? "",
    default_timezone: data.organization.default_timezone ?? "UTC",
    one_liner: data.profile.one_liner ?? "",
    voice_rules: listToText(data.profile.voice_rules),
    preferred_phrases: listToText(data.profile.preferred_phrases),
    banned_phrases: listToText(data.profile.banned_phrases),
    approved_claims: listToText(data.profile.approved_claims),
    forbidden_claims: listToText(data.profile.forbidden_claims),
    content_pillars: listToText(data.profile.content_pillars),
    sensitive_topics: listToText(data.profile.sensitive_topics),
  };
}

export function bootstrapFromCurrentWorkspace(workspace: CurrentWorkspace, opportunities: Opportunity[] = []): Bootstrap {
  return {
    organization: workspace.organization,
    profile: workspace.profile,
    sources: workspace.sources,
    opportunities,
  };
}

export const emptySourceForm: SourceForm = {
  source_type: "manual_note",
  title: "",
  uri: "",
  raw_text: "",
  approval_status: "approved",
  freshness_days: "180",
};

export function emptySourceFormFor(sourceType = "manual_note"): SourceForm {
  return { ...emptySourceForm, source_type: sourceType };
}

export const emptyMetricsForm: MetricsForm = {
  memory_id: "",
  impressions: "",
  reactions: "",
  comments: "",
  shares: "",
  clicks: "",
};

export const emptyAuthForm: AuthForm = {
  name: "",
  email: "",
  password: "",
  organization_name: "",
  website_url: "",
  industry: "",
  description: "",
  audience_summary: "",
  default_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
};

export const emptyUserForm: UserForm = {
  name: "",
  email: "",
  role: "viewer",
};

export const emptyCalendarEventForm: CalendarEventForm = {
  title: "",
  event_type: "company",
  starts_at: "",
  ends_at: "",
  description: "",
  relevance_terms: "",
};

export const emptyTrendSignalForm: TrendSignalForm = {
  title: "",
  summary: "",
  source_name: "",
  source_url: "",
  observed_at: "",
  relevance_terms: "",
};

export function opportunityWarnings(opportunity: Opportunity): string[] {
  const warnings = opportunity.metadata?.warnings;
  return Array.isArray(warnings) ? warnings.map(String) : [];
}

export function canBuildBrief(opportunity: Opportunity): boolean {
  return opportunity.status !== "warned" && opportunity.source_ids.length > 0;
}

export function opportunityRecencyValue(opportunity: Opportunity): number {
  const metadataTime = typeof opportunity.metadata?.source_updated_at === "string" ? opportunity.metadata.source_updated_at : "";
  const parsed = Date.parse(metadataTime || opportunity.created_at);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function opportunityRank(opportunity: Opportunity): number {
  const recencyDays = opportunityRecencyValue(opportunity)
    ? Math.max((Date.now() - opportunityRecencyValue(opportunity)) / 86_400_000, 0)
    : 365;
  const recencyScore = Math.max(0, 1 - recencyDays / 90);
  const warningPenalty = opportunity.status === "warned" ? 0.25 : 0;
  return (
    opportunity.relevance_score * 0.42 +
    opportunity.confidence_score * 0.24 +
    opportunity.freshness_score * 0.22 +
    recencyScore * 0.08 +
    Math.min(opportunity.source_ids.length, 4) * 0.01 -
    warningPenalty
  );
}

export function sortOpportunities(opportunitiesToSort: Opportunity[]): Opportunity[] {
  return [...opportunitiesToSort].sort((left, right) => {
    const rankDifference = opportunityRank(right) - opportunityRank(left);
    if (Math.abs(rankDifference) > 0.0001) return rankDifference;
    return opportunityRecencyValue(right) - opportunityRecencyValue(left);
  });
}

export function approvalPolicyForm(policy: ApprovalPolicy): ApprovalPolicyForm {
  return {
    required_reviewer_count: String(policy.required_reviewer_count),
    require_approval_before_export: policy.require_approval_before_export,
    require_approval_before_publish: policy.require_approval_before_publish,
    allow_risk_override: policy.allow_risk_override,
  };
}

export function aiProviderSettingsForm(settings: AIProviderSettings): AIProviderSettingsForm {
  return {
    generation_provider: settings.generation_provider,
    generation_model: settings.generation_model || "deterministic-structured-v1",
    generation_base_url: settings.generation_base_url ?? "",
    generation_api_key_env_var: settings.generation_api_key_env_var ?? "",
    embedding_provider: settings.embedding_provider,
    embedding_model: settings.embedding_model || "local-hash",
    embedding_base_url: settings.embedding_base_url ?? "",
    embedding_api_key_env_var: settings.embedding_api_key_env_var ?? "",
    local_runtime: settings.local_runtime,
    enabled: settings.enabled,
  };
}

export function aiProviderPayload(form: AIProviderSettingsForm) {
  return {
    generation_provider: form.generation_provider,
    generation_model: form.generation_model.trim() || "deterministic-structured-v1",
    generation_base_url: form.generation_base_url.trim() || null,
    generation_api_key_env_var: form.generation_api_key_env_var.trim() || null,
    embedding_provider: form.embedding_provider,
    embedding_model: form.embedding_model.trim() || "local-hash",
    embedding_base_url: form.embedding_base_url.trim() || null,
    embedding_api_key_env_var: form.embedding_api_key_env_var.trim() || null,
    local_runtime: form.local_runtime,
    enabled: form.enabled,
  };
}

export function validateAIProviderForm(form: AIProviderSettingsForm): string[] {
  const errors: string[] = [];
  if (!form.generation_model.trim()) errors.push("Generation model is required.");
  if (!form.embedding_model.trim()) errors.push("Embedding model is required.");
  if (["openai_compatible", "local"].includes(form.generation_provider) && !form.generation_base_url.trim()) {
    errors.push("Generation base URL is required for local or OpenAI-compatible providers.");
  }
  if (["openai_compatible", "local"].includes(form.embedding_provider) && !form.embedding_base_url.trim()) {
    errors.push("Embedding base URL is required for local or OpenAI-compatible providers.");
  }
  const secretPattern = /^[A-Za-z0-9_-]*$/;
  if (!secretPattern.test(form.generation_api_key_env_var) || !secretPattern.test(form.embedding_api_key_env_var)) {
    errors.push("Secret references can only include letters, numbers, underscores, and hyphens.");
  }
  return errors;
}
