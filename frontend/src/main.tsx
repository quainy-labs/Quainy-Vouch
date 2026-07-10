import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive,
  CalendarClock,
  Check,
  Clipboard,
  FileText,
  FileCheck2,
  Library,
  Plus,
  RefreshCcw,
  Save,
  Send,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import "./styles.css";

const API_BASES = Array.from(
  new Set([import.meta.env.VITE_API_BASE, "http://127.0.0.1:8000", "http://127.0.0.1:8001"].filter(Boolean) as string[]),
);
let resolvedApiBase: string | null = null;
const AUTH_TOKEN_KEY = "quainy_vouch_auth_token";

type Account = {
  id: string;
  name: string;
  email: string;
};

type Organization = {
  id: string;
  name: string;
  website_url?: string;
  industry?: string;
  description?: string;
  audience_summary?: string;
  default_timezone?: string;
};

type Profile = {
  one_liner?: string;
  mission?: string;
  product_summary?: string;
  audience?: string;
  voice_rules: string[];
  preferred_phrases: string[];
  banned_phrases: string[];
  approved_claims: string[];
  forbidden_claims: string[];
  content_pillars: string[];
  sensitive_topics: string[];
};

type Source = {
  id: string;
  title: string;
  source_type: string;
  uri?: string;
  approval_status: string;
  freshness_days: number;
  last_ingested_at?: string;
  created_at: string;
  updated_at: string;
};

type AuditLog = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

type SourceDetail = {
  source: Source;
  raw_text: string;
  chunk_count: number;
  audit_logs: AuditLog[];
};

type Opportunity = {
  id: string;
  title: string;
  summary: string;
  reason_today: string;
  relevance_score: number;
  freshness_score: number;
  confidence_score: number;
  source_ids: string[];
  status: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

type ContentBrief = {
  id: string;
  opportunity_id: string;
  organization_id: string;
  objective: string;
  audience: string;
  key_message: string;
  supporting_points: string[];
  claims: string[];
  do_not_say: string[];
  source_ids: string[];
  risks: string[];
  prompt_version: string;
};

type Claim = {
  text: string;
  support_status: string;
  supporting_chunk_ids: string[];
  risk_reason?: string;
};

type ApprovalDecision = {
  id: string;
  draft_id: string;
  decision: string;
  reason?: string;
  created_at: string;
};

type Draft = {
  id: string;
  platform: string;
  content_type: string;
  body: string;
  hook: string;
  status: string;
  source_ids: string[];
  source_map: Record<string, string[]>;
  risk_report: string[];
  quality_report: string[];
  duplicate_report: { duplicate_score: number; similar_posts: Array<{ excerpt: string; score: number }> };
  claims: Claim[];
  generation_metadata: Record<string, unknown>;
  approval_metadata: Record<string, unknown>;
  scheduled_for?: string;
  exported_at?: string;
  published_at?: string;
  publish_result: Record<string, unknown>;
  updated_at: string;
};

type LinkedInIntegration = {
  organization_id: string;
  selected_page_urn?: string;
  selected_page_name?: string;
  oauth_status: string;
  permissions: string[];
  publishing_enabled: boolean;
  updated_at: string;
};

type PublishResult = {
  provider: string;
  status: string;
  draft_id: string;
  page_urn: string;
  page_name?: string;
  provider_post_id?: string;
  published_url?: string;
  failure_reason?: string;
};

type PostMemory = {
  id: string;
  platform: string;
  content_type: string;
  final_body: string;
  source_draft_id: string;
  published_at?: string;
  performance_snapshot: Record<string, unknown>;
};

type AnalyticsPostSummary = {
  post_memory_id: string;
  source_draft_id: string;
  platform: string;
  content_type: string;
  excerpt: string;
  performance_score: number;
  metrics: Record<string, number>;
};

type AnalyticsDashboard = {
  organization_id: string;
  posts_analyzed: number;
  total_impressions: number;
  total_reactions: number;
  total_comments: number;
  total_shares: number;
  total_clicks: number;
  average_performance_score: number;
  top_posts: AnalyticsPostSummary[];
};

type ContentArtifact = {
  id: string;
  kind: string;
  title: string;
  platform?: string | null;
  content_type?: string | null;
  status: string;
  excerpt: string;
  source_count: number;
  risk_count: number;
  updated_at: string;
  scheduled_for?: string | null;
  published_at?: string | null;
};

type PillarCoverage = {
  pillar: string;
  source_count: number;
  artifact_count: number;
  performance_score: number;
  recommendation: string;
};

type TopicRepetition = {
  topic: string;
  count: number;
  last_seen?: string | null;
};

type PerformanceBreakdown = {
  key: string;
  label: string;
  posts: number;
  average_score: number;
  impressions: number;
  reactions: number;
  clicks: number;
};

type StrategyDirection = {
  title: string;
  rationale: string;
  source_basis: string[];
  confidence: number;
};

type StrategyDashboard = {
  organization_id: string;
  pillar_coverage: PillarCoverage[];
  topic_repetition: TopicRepetition[];
  performance_by_platform: PerformanceBreakdown[];
  performance_by_content_type: PerformanceBreakdown[];
  suggested_directions: StrategyDirection[];
};

type WorkspaceUser = {
  id: string;
  organization_id: string;
  name: string;
  email?: string;
  role: "owner" | "editor" | "reviewer" | "viewer";
};

type OnboardingState = {
  organization_id: string;
  account_id: string;
  completed_steps: string[];
  profile_skipped: boolean;
  completion_percent: number;
  updated_at: string;
};

type ApprovalPolicy = {
  organization_id: string;
  required_reviewer_count: number;
  require_approval_before_export: boolean;
  require_approval_before_publish: boolean;
  allow_risk_override: boolean;
  updated_at: string;
};

type ApprovalPolicyForm = {
  required_reviewer_count: string;
  require_approval_before_export: boolean;
  require_approval_before_publish: boolean;
  allow_risk_override: boolean;
};

type PreferenceSuggestion = {
  id: string;
  organization_id: string;
  kind: string;
  title: string;
  rationale: string;
  proposed_update: Record<string, string[]>;
  evidence: string[];
  confidence: number;
  status: "pending" | "approved" | "dismissed";
};

type CalendarEvent = {
  id: string;
  organization_id: string;
  title: string;
  event_type: "company" | "public";
  event_date?: string;
  starts_at: string;
  ends_at?: string;
  description?: string;
  relevance_terms: string[];
  created_at: string;
};

type TrendSignal = {
  id: string;
  organization_id: string;
  title: string;
  summary: string;
  source_name: string;
  source_url?: string;
  observed_at: string;
  relevance_terms: string[];
  created_at: string;
};

type SourceChunk = {
  id: string;
  source_id: string;
  chunk_text: string;
  chunk_index: number;
};

type ReviewerPackage = {
  draft: Draft;
  opportunity: Opportunity;
  sources: Source[];
  source_chunks: SourceChunk[];
  decision_history: ApprovalDecision[];
  suggested_action: string;
};

type Bootstrap = {
  organization: Organization;
  profile: Profile;
  sources: Source[];
  opportunities: Opportunity[];
};

type CurrentWorkspace = {
  account: Account;
  organization: Organization;
  user: WorkspaceUser;
  profile: Profile;
  sources: Source[];
  onboarding: OnboardingState;
};

type AuthResponse = {
  token: string;
  workspace: CurrentWorkspace;
};

type AuthForm = {
  name: string;
  email: string;
  password: string;
  organization_name: string;
  website_url: string;
  industry: string;
  description: string;
  audience_summary: string;
  default_timezone: string;
};

type SetupForm = {
  name: string;
  website_url: string;
  industry: string;
  description: string;
  audience_summary: string;
  default_timezone: string;
  one_liner: string;
  voice_rules: string;
  preferred_phrases: string;
  banned_phrases: string;
  approved_claims: string;
  forbidden_claims: string;
  content_pillars: string;
  sensitive_topics: string;
};

type SourceForm = {
  source_type: string;
  title: string;
  uri: string;
  raw_text: string;
  approval_status: string;
  freshness_days: string;
};

type MetricsForm = {
  memory_id: string;
  impressions: string;
  reactions: string;
  comments: string;
  shares: string;
  clicks: string;
};

type UserForm = {
  name: string;
  email: string;
  role: WorkspaceUser["role"];
};

type CalendarEventForm = {
  title: string;
  event_type: CalendarEvent["event_type"];
  starts_at: string;
  ends_at: string;
  description: string;
  relevance_terms: string;
};

type TrendSignalForm = {
  title: string;
  summary: string;
  source_name: string;
  source_url: string;
  observed_at: string;
  relevance_terms: string;
};

type FormatChoice =
  | "linkedin_company_post"
  | "blog_outline"
  | "newsletter_email"
  | "instagram_caption"
  | "instagram_carousel_outline";

type WorkspaceView = "studio" | "library" | "calendar" | "sources" | "strategy" | "settings";
type SetupSection = "company" | "voice" | "claims" | "linkedin";
type LibraryStatusFilter =
  | "all"
  | "opportunity"
  | "brief"
  | "draft"
  | "needs_review"
  | "approved"
  | "scheduled"
  | "exported"
  | "published"
  | "rejected";
type LibraryPlatformFilter = "all" | string;

type ViewItem = {
  id: WorkspaceView;
  label: string;
  eyebrow: string;
  title: string;
  description: string;
  badge: string;
};

function fieldNameFromLocation(location: unknown[]): string {
  const parts = location
    .filter((item) => typeof item === "string")
    .filter((item) => !["body", "query", "path"].includes(item));
  const field = parts[parts.length - 1];
  if (!field) return "Request";
  return field.replace(/_/g, " ");
}

async function responseErrorMessage(response: Response): Promise<string> {
  const fallback = `Request failed with status ${response.status}.`;
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    try {
      const text = await response.text();
      return text || fallback;
    } catch {
      return fallback;
    }
  }
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (!item || typeof item !== "object") return "";
          const issue = item as { loc?: unknown[]; msg?: unknown };
          const label = Array.isArray(issue.loc) ? fieldNameFromLocation(issue.loc) : "Field";
          return `${label}: ${String(issue.msg ?? "Invalid value")}`;
        })
        .filter(Boolean);
      if (messages.length > 0) return messages.join("\n");
    }
  }
  return fallback;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const bases = resolvedApiBase ? [resolvedApiBase, ...API_BASES.filter((base) => base !== resolvedApiBase)] : API_BASES;
  let lastError: unknown = null;
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  for (const base of bases) {
    let response: Response;
    try {
      response = await fetch(`${base}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(init?.headers ?? {}),
        },
      });
    } catch (error) {
      lastError = error;
      continue;
    }
    resolvedApiBase = base;
    if (!response.ok) {
      throw new Error(await responseErrorMessage(response));
    }
    return response.json();
  }
  throw new Error(
    `The workspace service is unavailable. Please check that the app services are running and try again.${
      lastError instanceof Error ? ` ${lastError.message}` : ""
    }`,
  );
}

function listToText(values: string[] | undefined): string {
  return (values ?? []).join("\n");
}

function textToList(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function validateEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function validateHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function validateAuthForm(form: AuthForm, mode: "signup" | "login"): string[] {
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

function validateSetupForm(form: SetupForm): string[] {
  const errors: string[] = [];
  if (!form.name.trim()) errors.push("Organization name is required.");
  if (!form.default_timezone.trim()) errors.push("Timezone is required.");
  if (form.website_url.trim() && !validateHttpUrl(form.website_url)) errors.push("Website must be a valid http(s) URL.");
  return errors;
}

function validateSourceForm(form: SourceForm): string[] {
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

function draftFormatLabel(draft: Draft | null): string {
  if (!draft) return "Draft";
  if (draft.platform === "blog") return "Blog outline";
  if (draft.platform === "newsletter") return "Newsletter email";
  if (draft.platform === "instagram" && draft.content_type === "carousel_outline") return "Instagram carousel";
  if (draft.platform === "instagram") return "Instagram caption";
  return "LinkedIn company post";
}

function platformDisplayName(platform: string): string {
  if (platform === "linkedin") return "LinkedIn";
  if (platform === "blog") return "Blog";
  if (platform === "newsletter") return "Newsletter";
  if (platform === "instagram") return "Instagram";
  return platform || "Platform";
}

function contentTypeDisplayName(contentType: string): string {
  return contentType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function auditTimeValue(value: string): number {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function formatAuditTime(value: string): string {
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

function formatChoiceParams(choice: FormatChoice): string {
  const params: Record<FormatChoice, string> = {
    linkedin_company_post: "?platform=linkedin&content_type=company_post",
    blog_outline: "?platform=blog&content_type=outline",
    newsletter_email: "?platform=newsletter&content_type=email",
    instagram_caption: "?platform=instagram&content_type=caption",
    instagram_carousel_outline: "?platform=instagram&content_type=carousel_outline",
  };
  return params[choice];
}

function formatChoiceNotice(choice: FormatChoice): string {
  const notices: Record<FormatChoice, string> = {
    linkedin_company_post: "LinkedIn variants generated from the selected brief.",
    blog_outline: "Blog outline variants generated from the selected brief.",
    newsletter_email: "Newsletter email variants generated from the selected brief.",
    instagram_caption: "Instagram caption variants generated from the selected brief.",
    instagram_carousel_outline: "Instagram carousel variants generated from the selected brief.",
  };
  return notices[choice];
}

function formatChoiceLabel(choice: FormatChoice): string {
  const labels: Record<FormatChoice, string> = {
    linkedin_company_post: "LinkedIn company post",
    blog_outline: "Blog article outline",
    newsletter_email: "Newsletter email",
    instagram_caption: "Instagram caption",
    instagram_carousel_outline: "Instagram carousel outline",
  };
  return labels[choice];
}

function formatChoicePlatform(choice: FormatChoice): { platform: string; contentType: string } {
  const formats: Record<FormatChoice, { platform: string; contentType: string }> = {
    linkedin_company_post: { platform: "linkedin", contentType: "company_post" },
    blog_outline: { platform: "blog", contentType: "outline" },
    newsletter_email: { platform: "newsletter", contentType: "email" },
    instagram_caption: { platform: "instagram", contentType: "caption" },
    instagram_carousel_outline: { platform: "instagram", contentType: "carousel_outline" },
  };
  return formats[choice];
}

function summarizeNames(names: string[], limit = 3): string {
  if (names.length === 0) return "";
  const visible = names.slice(0, limit).join(", ");
  const remaining = names.length - limit;
  return remaining > 0 ? `${visible} + ${remaining} more` : visible;
}

function setupFromBootstrap(data: Bootstrap): SetupForm {
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

function bootstrapFromCurrentWorkspace(workspace: CurrentWorkspace, opportunities: Opportunity[] = []): Bootstrap {
  return {
    organization: workspace.organization,
    profile: workspace.profile,
    sources: workspace.sources,
    opportunities,
  };
}

const emptySourceForm: SourceForm = {
  source_type: "manual_note",
  title: "",
  uri: "",
  raw_text: "",
  approval_status: "approved",
  freshness_days: "180",
};

function emptySourceFormFor(sourceType = "manual_note"): SourceForm {
  return { ...emptySourceForm, source_type: sourceType };
}

const emptyMetricsForm: MetricsForm = {
  memory_id: "",
  impressions: "",
  reactions: "",
  comments: "",
  shares: "",
  clicks: "",
};

const emptyAuthForm: AuthForm = {
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

const emptyUserForm: UserForm = {
  name: "",
  email: "",
  role: "viewer",
};

const emptyCalendarEventForm: CalendarEventForm = {
  title: "",
  event_type: "company",
  starts_at: "",
  ends_at: "",
  description: "",
  relevance_terms: "",
};

const emptyTrendSignalForm: TrendSignalForm = {
  title: "",
  summary: "",
  source_name: "",
  source_url: "",
  observed_at: "",
  relevance_terms: "",
};

function opportunityWarnings(opportunity: Opportunity): string[] {
  const warnings = opportunity.metadata?.warnings;
  return Array.isArray(warnings) ? warnings.map(String) : [];
}

function canBuildBrief(opportunity: Opportunity): boolean {
  return opportunity.status !== "warned" && opportunity.source_ids.length > 0;
}

function opportunityRecencyValue(opportunity: Opportunity): number {
  const metadataTime = typeof opportunity.metadata?.source_updated_at === "string" ? opportunity.metadata.source_updated_at : "";
  const parsed = Date.parse(metadataTime || opportunity.created_at);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function opportunityRank(opportunity: Opportunity): number {
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

function sortOpportunities(opportunitiesToSort: Opportunity[]): Opportunity[] {
  return [...opportunitiesToSort].sort((left, right) => {
    const rankDifference = opportunityRank(right) - opportunityRank(left);
    if (Math.abs(rankDifference) > 0.0001) return rankDifference;
    return opportunityRecencyValue(right) - opportunityRecencyValue(left);
  });
}

function approvalPolicyForm(policy: ApprovalPolicy): ApprovalPolicyForm {
  return {
    required_reviewer_count: String(policy.required_reviewer_count),
    require_approval_before_export: policy.require_approval_before_export,
    require_approval_before_publish: policy.require_approval_before_publish,
    allow_risk_override: policy.allow_risk_override,
  };
}

function App() {
  const [currentUser, setCurrentUser] = useState<WorkspaceUser | null>(null);
  const [onboarding, setOnboarding] = useState<OnboardingState | null>(null);
  const [authMode, setAuthMode] = useState<"signup" | "login">("signup");
  const [authForm, setAuthForm] = useState<AuthForm>(emptyAuthForm);
  const [authErrors, setAuthErrors] = useState<string[]>([]);
  const [authRequired, setAuthRequired] = useState(false);
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [bootstrapError, setBootstrapError] = useState("");
  const [setupForm, setSetupForm] = useState<SetupForm | null>(null);
  const [setupErrors, setSetupErrors] = useState<string[]>([]);
  const [sourceForm, setSourceForm] = useState<SourceForm>(emptySourceForm);
  const [sourceErrors, setSourceErrors] = useState<string[]>([]);
  const [sourceDraftsByType, setSourceDraftsByType] = useState<Record<string, SourceForm>>({});
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [sourceDetail, setSourceDetail] = useState<SourceDetail | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [visibleOpportunityCount, setVisibleOpportunityCount] = useState(12);
  const [opportunityMessage, setOpportunityMessage] = useState("");
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);
  const [selectedBrief, setSelectedBrief] = useState<ContentBrief | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<Draft | null>(null);
  const [reviewPackage, setReviewPackage] = useState<ReviewerPackage | null>(null);
  const [editedBody, setEditedBody] = useState("");
  const [reviewReason, setReviewReason] = useState("");
  const [scheduleFor, setScheduleFor] = useState("");
  const [calendarItems, setCalendarItems] = useState<Draft[]>([]);
  const [linkedinIntegration, setLinkedinIntegration] = useState<LinkedInIntegration | null>(null);
  const [memoryItems, setMemoryItems] = useState<PostMemory[]>([]);
  const [analyticsDashboard, setAnalyticsDashboard] = useState<AnalyticsDashboard | null>(null);
  const [contentArtifacts, setContentArtifacts] = useState<ContentArtifact[]>([]);
  const [strategyDashboard, setStrategyDashboard] = useState<StrategyDashboard | null>(null);
  const [metricsForm, setMetricsForm] = useState<MetricsForm>(emptyMetricsForm);
  const [users, setUsers] = useState<WorkspaceUser[]>([]);
  const [userForm, setUserForm] = useState<UserForm>(emptyUserForm);
  const [approvalPolicy, setApprovalPolicy] = useState<ApprovalPolicy | null>(null);
  const [approvalPolicyDraft, setApprovalPolicyDraft] = useState<ApprovalPolicyForm | null>(null);
  const [preferenceSuggestions, setPreferenceSuggestions] = useState<PreferenceSuggestion[]>([]);
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [trendSignals, setTrendSignals] = useState<TrendSignal[]>([]);
  const [calendarEventForm, setCalendarEventForm] = useState<CalendarEventForm>(emptyCalendarEventForm);
  const [trendSignalForm, setTrendSignalForm] = useState<TrendSignalForm>(emptyTrendSignalForm);
  const [formatChoice, setFormatChoice] = useState<FormatChoice>("linkedin_company_post");
  const [activeView, setActiveView] = useState<WorkspaceView>("studio");
  const [setupSection, setSetupSection] = useState<SetupSection>("company");
  const [libraryStatusFilter, setLibraryStatusFilter] = useState<LibraryStatusFilter>("all");
  const [libraryPlatformFilter, setLibraryPlatformFilter] = useState<LibraryPlatformFilter>("all");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  async function loadWorkspace() {
    setBootstrapError("");
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
      setAuthRequired(true);
      setBootstrap(null);
      return;
    }
    try {
      setAuthRequired(false);
      const current = await api<CurrentWorkspace>("/me");
      const opportunities = await api<Opportunity[]>(`/organizations/${current.organization.id}/opportunities`);
      const data = bootstrapFromCurrentWorkspace(current, opportunities);
      setCurrentUser(current.user);
      setOnboarding(current.onboarding);
      setBootstrap(data);
      setSetupForm(setupFromBootstrap(data));
      setOpportunities(sortOpportunities(data.opportunities));
      setVisibleOpportunityCount(12);
      await Promise.allSettled([
        api<Draft[]>(`/organizations/${data.organization.id}/calendar`).then(setCalendarItems),
        api<LinkedInIntegration>(`/organizations/${data.organization.id}/linkedin-integration`).then(setLinkedinIntegration),
        api<PostMemory[]>(`/organizations/${data.organization.id}/memory`).then((memory) => {
        setMemoryItems(memory);
        if (memory.length > 0) {
          setMetricsForm((current) => ({ ...current, memory_id: memory[0].id }));
        }
        }),
        api<AnalyticsDashboard>(`/organizations/${data.organization.id}/analytics`).then(setAnalyticsDashboard),
        api<ContentArtifact[]>(`/organizations/${data.organization.id}/content-artifacts`).then(setContentArtifacts),
        api<StrategyDashboard>(`/organizations/${data.organization.id}/strategy`).then(setStrategyDashboard),
        api<WorkspaceUser[]>(`/organizations/${data.organization.id}/users`).then(setUsers),
        api<ApprovalPolicy>(`/organizations/${data.organization.id}/approval-policy`).then((policy) => {
          setApprovalPolicy(policy);
          setApprovalPolicyDraft(approvalPolicyForm(policy));
        }),
        api<PreferenceSuggestion[]>(`/organizations/${data.organization.id}/preference-suggestions`).then(setPreferenceSuggestions),
        api<CalendarEvent[]>(`/organizations/${data.organization.id}/calendar-events`).then(setCalendarEvents),
        api<TrendSignal[]>(`/organizations/${data.organization.id}/trend-signals`).then(setTrendSignals),
      ]);
    } catch (error) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      setAuthRequired(true);
      setBootstrap(null);
      setBootstrapError(error instanceof Error ? error.message : "Could not load your workspace.");
    }
  }

  useEffect(() => {
    void loadWorkspace();
  }, []);

  useEffect(() => {
    if (!selectedDraft) {
      setReviewPackage(null);
      return;
    }
    api<ReviewerPackage>(`/drafts/${selectedDraft.id}/reviewer-package`).then((pkg) => {
      setReviewPackage(pkg);
      setEditedBody(pkg.draft.body);
      setReviewReason("");
    });
  }, [selectedDraft]);

  useEffect(() => {
    if (!selectedSourceId) {
      setSourceDetail(null);
      return;
    }
    api<SourceDetail>(`/sources/${selectedSourceId}`).then(setSourceDetail);
  }, [selectedSourceId]);

  async function refreshProductSurfaces(organizationId = bootstrap?.organization.id) {
    if (!organizationId) return;
    await Promise.allSettled([
      api<ContentArtifact[]>(`/organizations/${organizationId}/content-artifacts`).then(setContentArtifacts),
      api<StrategyDashboard>(`/organizations/${organizationId}/strategy`).then(setStrategyDashboard),
    ]);
  }

  async function refreshCurrentWorkspaceState() {
    const current = await api<CurrentWorkspace>("/me");
    setCurrentUser(current.user);
    setOnboarding(current.onboarding);
    return current;
  }

  const healthLabel = useMemo(() => {
    if (!bootstrap) return "Loading";
    const approvedCount = bootstrap.sources.filter((source) => source.approval_status === "approved").length;
    return `${approvedCount} approved sources`;
  }, [bootstrap]);

  const approvalBlocked = reviewPackage?.suggested_action.toLowerCase().includes("unsupported claims") ?? false;
  const approvalProgress = selectedDraft?.approval_metadata ?? {};
  const canApproveDraft = !busy && !approvalBlocked;
  const canExportDraft = Boolean(selectedDraft && ["approved", "scheduled", "exported", "published"].includes(selectedDraft.status));
  const canScheduleDraft = Boolean(selectedDraft && ["approved", "scheduled", "exported"].includes(selectedDraft.status));
  const canAttemptLinkedinPublish =
    selectedDraft?.platform === "linkedin" &&
    selectedDraft.content_type === "company_post" &&
    ["approved", "scheduled", "exported"].includes(selectedDraft.status);
  const publishCapabilityText = selectedDraft
    ? canAttemptLinkedinPublish
      ? linkedinIntegration?.selected_page_urn
        ? "Direct publishing is available for this LinkedIn company post."
        : "Select a LinkedIn company page in Settings before publishing directly."
      : `Direct publishing is not configured for ${platformDisplayName(selectedDraft.platform)} ${contentTypeDisplayName(
          selectedDraft.content_type,
        )}. Export the artifact or save a schedule intent for an external channel.`
    : "";
  const setupSections: Array<{ id: SetupSection; label: string }> = [
    { id: "company", label: "Company" },
    { id: "voice", label: "Voice" },
    { id: "claims", label: "Claims" },
    { id: "linkedin", label: "LinkedIn" },
  ];
  const viewItems: ViewItem[] = [
    {
      id: "studio",
      label: "Studio",
      eyebrow: "Create",
      title: "Create platform-ready content",
      description: "Choose a supported platform, turn an approved opportunity into a brief, generate variants, and complete review.",
      badge: `${drafts.length} drafts`,
    },
    {
      id: "library",
      label: "Library",
      eyebrow: "Work",
      title: "Generated and approved content",
      description: "Browse drafts, approved memory, and exported artifacts without dropping into edit mode first.",
      badge: `${drafts.length + memoryItems.length} artifacts`,
    },
    {
      id: "calendar",
      label: "Calendar",
      eyebrow: "Schedule",
      title: "Queue, campaigns, and trends",
      description: "Manage upcoming publishing intent, company events, and trend signals used by the relevance gate.",
      badge: `${calendarItems.length} queued`,
    },
    {
      id: "sources",
      label: "Sources",
      eyebrow: "Knowledge",
      title: "Approved company source library",
      description: "Add, inspect, refresh, and test the source material that every opportunity and draft must cite.",
      badge: `${bootstrap?.sources.length ?? 0} sources`,
    },
    {
      id: "strategy",
      label: "Strategy",
      eyebrow: "Learn",
      title: "Analytics and preference learning",
      description: "Review post performance and decide which repeated edit patterns should become durable profile memory.",
      badge: `${analyticsDashboard?.posts_analyzed ?? 0} posts`,
    },
    {
      id: "settings",
      label: "Settings",
      eyebrow: "Govern",
      title: "Users, roles, and approval policy",
      description: "Manage collaborators, permission boundaries, reviewer requirements, and approval controls.",
      badge: `${users.length} users`,
    },
  ];
  const currentView = viewItems.find((item) => item.id === activeView) ?? viewItems[0];
  const readyDrafts = drafts.filter((draft) => ["needs_review", "pending_approval", "approved"].includes(draft.status));
  const approvedSources = bootstrap?.sources.filter((source) => source.approval_status === "approved") ?? [];
  const disabledSources = bootstrap?.sources.filter((source) => source.approval_status === "disabled") ?? [];
  const archivedSources = bootstrap?.sources.filter((source) => source.approval_status === "archived") ?? [];
  const sourceHealthState = approvedSources.length > 0 ? "healthy" : "blocked";
  const sourceHealthText =
    approvedSources.length > 0
      ? `${approvedSources.length} approved source${approvedSources.length === 1 ? "" : "s"} can support recommendations.`
      : "Approved company knowledge is required before safe recommendations can be generated.";
  const selectedFormatConfig = formatChoicePlatform(formatChoice);
  const selectedFormatLabel = formatChoiceLabel(formatChoice);
  const sourceTitleById = new Map((bootstrap?.sources ?? []).map((source) => [source.id, source.title]));
  const activeSourceNames = approvedSources.map((source) => source.title);
  const activeSourceSummary = summarizeNames(activeSourceNames, 3);
  const sampleSourceActive = approvedSources.some((source) => source.uri?.startsWith("sample://"));
  const selectedDraftMatchesFormat =
    Boolean(selectedDraft) &&
    selectedDraft?.platform === selectedFormatConfig.platform &&
    selectedDraft?.content_type === selectedFormatConfig.contentType;
  const railSourceLimit = 25;
  const railSources = [...(bootstrap?.sources ?? [])]
    .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime())
    .slice(0, railSourceLimit);
  const railSourceOverflow = Math.max((bootstrap?.sources.length ?? 0) - railSourceLimit, 0);
  const availableLibraryPlatforms = Array.from(
    new Set(contentArtifacts.map((artifact) => artifact.platform).filter((platform): platform is string => Boolean(platform))),
  );
  const statusOptions: Array<{ id: LibraryStatusFilter; label: string }> = [
    { id: "all", label: "All" },
    { id: "opportunity", label: "Opportunities" },
    { id: "brief", label: "Briefs" },
    { id: "draft", label: "Drafts" },
    { id: "needs_review", label: "Needs review" },
    { id: "approved", label: "Approved" },
    { id: "scheduled", label: "Scheduled" },
    { id: "exported", label: "Exported" },
    { id: "published", label: "Published" },
    { id: "rejected", label: "Rejected" },
  ];
  const sourceGuideCards = [
    {
      id: "document",
      title: "Upload a company document",
      description: "Best for product source-of-truth, positioning docs, policies, and launch notes.",
      source_type: "markdown",
    },
    {
      id: "paste",
      title: "Paste approved text",
      description: "Best for short claims, customer proof, FAQs, and voice guidance.",
      source_type: "manual_note",
    },
    {
      id: "url",
      title: "Add a public URL",
      description: "Best for docs, changelogs, pages, and source material you want tracked by origin.",
      source_type: "url",
    },
    {
      id: "release",
      title: "Add release notes",
      description: "Best for product updates, changelog entries, and launch context.",
      source_type: "github_release",
    },
    {
      id: "notion",
      title: "Add a Notion page",
      description: "Best for internal knowledge that has already been approved for content use.",
      source_type: "notion_page",
    },
  ];
  const selectedSourceGuide = sourceGuideCards.find((guide) => guide.source_type === sourceForm.source_type) ?? sourceGuideCards[1];
  const sourceTypeText: Record<
    string,
    {
      heading: string;
      helper: string;
      titlePlaceholder: string;
      textLabel: string;
      textPlaceholder: string;
      uriLabel?: string;
      uriPlaceholder?: string;
      showUpload?: boolean;
    }
  > = {
    manual_note: {
      heading: "Paste approved company context",
      helper: "Use this for claims, positioning, proof points, FAQs, or voice guidance that is already approved for public content.",
      titlePlaceholder: "Example: Approved positioning notes",
      textLabel: "Approved note",
      textPlaceholder: "Paste approved claims, customer proof, positioning, policies, or product details.",
    },
    markdown: {
      heading: "Upload or paste a company document",
      helper: "Use this for source-of-truth documents, launch notes, product docs, or policy language.",
      titlePlaceholder: "Example: Product source of truth",
      textLabel: "Document text",
      textPlaceholder: "Upload a markdown/text file or paste the exact approved document content here.",
      uriLabel: "Document reference",
      uriPlaceholder: "Filename, doc URL, or internal reference",
      showUpload: true,
    },
    text: {
      heading: "Upload or paste a text document",
      helper: "Use this when the approved source is a plain text document.",
      titlePlaceholder: "Example: Customer proof notes",
      textLabel: "Document text",
      textPlaceholder: "Upload a text file or paste the exact approved document content here.",
      uriLabel: "Document reference",
      uriPlaceholder: "Filename, doc URL, or internal reference",
      showUpload: true,
    },
    url: {
      heading: "Add a selected public URL",
      helper: "Use this for one approved public page. The app stores only the page you provide, not a full website crawl.",
      titlePlaceholder: "Example: Public changelog page",
      textLabel: "Approved page text",
      textPlaceholder: "Paste the approved page text or relevant excerpt that should be available as source evidence.",
      uriLabel: "Public page URL",
      uriPlaceholder: "https://example.com/docs/product-update",
    },
    github_release: {
      heading: "Add release notes",
      helper: "Use this for public release notes or changelog excerpts that should support launch and product-update content.",
      titlePlaceholder: "Example: v1.8 launch notes",
      textLabel: "Approved release text",
      textPlaceholder: "Paste the public release notes, changelog excerpt, or approved launch details.",
      uriLabel: "GitHub release or repo URL",
      uriPlaceholder: "https://github.com/org/repo/releases/tag/v1.8.0",
    },
    notion_page: {
      heading: "Add a selected Notion page",
      helper: "Use this only for a page whose contents have already been approved for content generation.",
      titlePlaceholder: "Example: Approved campaign brief",
      textLabel: "Approved page text",
      textPlaceholder: "Paste the approved Notion page contents or excerpt.",
      uriLabel: "Notion page URL",
      uriPlaceholder: "https://notion.so/...",
    },
  };
  const sourceCopy = sourceTypeText[sourceForm.source_type] ?? sourceTypeText.manual_note;
  const sourceNeedsUri = Boolean(sourceCopy.uriLabel);
  const sourceAuditLogs = [...(sourceDetail?.audit_logs ?? [])].sort((left, right) => auditTimeValue(right.created_at) - auditTimeValue(left.created_at));
  const visibleSourceAuditLogs = sourceAuditLogs.slice(0, 6);
  const rankedOpportunities = useMemo(() => sortOpportunities(opportunities), [opportunities]);
  const visibleOpportunities = rankedOpportunities.slice(0, visibleOpportunityCount);
  const hiddenOpportunityCount = Math.max(rankedOpportunities.length - visibleOpportunities.length, 0);
  const visibleContentArtifacts = contentArtifacts.filter((artifact) => {
    const statusMatches =
      libraryStatusFilter === "all" ||
      artifact.kind === libraryStatusFilter ||
      artifact.status === libraryStatusFilter ||
      (libraryStatusFilter === "draft" && artifact.kind === "draft") ||
      (libraryStatusFilter === "needs_review" && ["needs_review", "pending_approval"].includes(artifact.status));
    const platformMatches = libraryPlatformFilter === "all" || artifact.platform === libraryPlatformFilter;
    return statusMatches && platformMatches;
  });
  const hasVisibleLibraryArtifacts = visibleContentArtifacts.length > 0;
  const libraryMetrics = [
    {
      label: "Source-backed ideas",
      value: contentArtifacts.filter((artifact) => artifact.kind === "opportunity").length,
      detail: "Ideas generated from approved sources, before format adaptation.",
    },
    {
      label: "Review queue",
      value: contentArtifacts.filter((artifact) => ["needs_review", "pending_approval"].includes(artifact.status)).length,
      detail: "Drafts waiting for review, edits, approval, or rejection.",
    },
    {
      label: "Reusable memory",
      value: memoryItems.length,
      detail: "Approved or published posts available for duplicate and preference checks.",
    },
    {
      label: "Active evidence",
      value: approvedSources.length,
      detail: activeSourceSummary || "No approved source is available.",
    },
  ];
  const calendarEntries: Array<{ id: string; kind: string; title: string; status: string; date: string }> = [
    ...calendarItems.map((item) => ({
      id: item.id,
      kind: "content",
      title: item.hook || item.body.slice(0, 72),
      status: item.status,
      date: item.scheduled_for || item.published_at || item.exported_at || item.updated_at,
    })),
    ...calendarEvents.map((eventItem) => ({
      id: eventItem.id,
      kind: eventItem.event_type,
      title: eventItem.title,
      status: eventItem.event_type,
      date: eventItem.starts_at || eventItem.event_date || eventItem.created_at,
    })),
  ].filter((entry) => Boolean(entry.date));
  const todayDate = new Date();
  const calendarDays = Array.from({ length: 14 }, (_, index) => {
    const date = new Date(todayDate);
    date.setDate(todayDate.getDate() + index);
    const dateKey = date.toISOString().slice(0, 10);
    return {
      date,
      dateKey,
      entries: calendarEntries.filter((entry) => new Date(entry.date).toISOString().slice(0, 10) === dateKey),
    };
  });
  const supportedClaimCount = selectedDraft?.claims.filter((claim) => claim.support_status === "supported").length ?? 0;
  const unsupportedClaimCount = selectedDraft?.claims.filter((claim) => claim.support_status === "unsupported").length ?? 0;
  const duplicateMatchCount = selectedDraft?.duplicate_report.similar_posts.length ?? 0;
  const selectedDraftBody = editedBody || selectedDraft?.body || "";
  const previewParagraphs = selectedDraftBody
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
  const selectedDraftAdapter = selectedDraft
    ? String(selectedDraft.generation_metadata.adapter_name ?? `${selectedDraft.platform} adapter`)
    : "";
  const selectedDraftPromptVersion = selectedDraft ? String(selectedDraft.generation_metadata.prompt_version ?? "prompt tracked") : "";
  const trustTimelineItems: Array<{
    step: string;
    title: string;
    detail: string;
    status: "complete" | "warning" | "pending";
  }> = [];
  if (selectedDraft) {
    trustTimelineItems.push({
      step: "Source basis",
      title: approvedSources.length > 0 ? "Approved knowledge is available" : "Approved knowledge is missing",
        detail:
          approvedSources.length > 0
          ? `${approvedSources.length} approved source${approvedSources.length === 1 ? "" : "s"} can support recommendations and claims: ${activeSourceSummary}.`
          : "Add approved company knowledge before relying on recommendations.",
      status: approvedSources.length > 0 ? "complete" : "warning",
    });
  }
  if (selectedDraft && selectedOpportunity) {
    trustTimelineItems.push({
      step: "Opportunity",
      title: selectedOpportunity.title,
      detail: `${Math.round(selectedOpportunity.relevance_score * 100)}% relevance, ${Math.round(
        selectedOpportunity.freshness_score * 100,
      )}% freshness, ${selectedOpportunity.source_ids.length} source${selectedOpportunity.source_ids.length === 1 ? "" : "s"}: ${selectedOpportunity.source_ids
        .map((sourceId) => sourceTitleById.get(sourceId) ?? sourceId)
        .slice(0, 2)
        .join(", ")}.`,
      status: selectedOpportunity.status === "warned" ? "warning" : "complete",
    });
  }
  if (selectedDraft && selectedBrief) {
    trustTimelineItems.push({
      step: "Brief",
      title: selectedBrief.key_message,
      detail: `${selectedBrief.supporting_points.length} supporting points and ${selectedBrief.risks.length} risk guardrail${
        selectedBrief.risks.length === 1 ? "" : "s"
      } carried into generation.`,
      status: "complete",
    });
  }
  if (selectedDraft) {
    trustTimelineItems.push({
      step: "Draft",
      title: `${platformDisplayName(selectedDraft.platform)} ${contentTypeDisplayName(selectedDraft.content_type)}`,
      detail: `${selectedDraftAdapter} generated this artifact with ${selectedDraft.source_ids.length} source${
        selectedDraft.source_ids.length === 1 ? "" : "s"
      } and ${selectedDraftPromptVersion}.`,
      status: "complete",
    });
    trustTimelineItems.push({
      step: "Checks",
      title: unsupportedClaimCount > 0 ? "Review needed before approval" : "Review checks are ready",
      detail: `${supportedClaimCount}/${selectedDraft.claims.length} claims supported, ${selectedDraft.risk_report.length} risk note${
        selectedDraft.risk_report.length === 1 ? "" : "s"
      }, ${duplicateMatchCount} similar memory match${duplicateMatchCount === 1 ? "" : "es"}.`,
      status: unsupportedClaimCount > 0 || selectedDraft.risk_report.length > 0 ? "warning" : "complete",
    });
  }
  if (reviewPackage) {
    trustTimelineItems.push({
      step: "Reviewer action",
      title: reviewPackage.suggested_action,
      detail:
        reviewPackage.decision_history.length > 0
          ? `${reviewPackage.decision_history.length} recorded decision${reviewPackage.decision_history.length === 1 ? "" : "s"}.`
          : "No reviewer decision has been recorded yet.",
      status: reviewPackage.suggested_action.toLowerCase().includes("unsupported") ? "warning" : "pending",
    });
    reviewPackage.decision_history.slice(0, 3).forEach((decision) => {
      trustTimelineItems.push({
        step: "Decision",
        title: decision.decision,
        detail: `${new Date(decision.created_at).toLocaleString()}${decision.reason ? ` - ${decision.reason}` : ""}`,
        status: decision.decision === "rejected" ? "warning" : "complete",
      });
    });
  }

  function selectContentFormat(choice: FormatChoice) {
    setFormatChoice(choice);
    setDrafts([]);
    setSelectedDraft(null);
    setReviewPackage(null);
    setEditedBody("");
    setReviewReason("");
    setScheduleFor("");
    setNotice(`Draft format set to ${formatChoiceLabel(choice)}. Generate fresh drafts from the selected brief.`);
  }

  async function generateOpportunities() {
    if (!bootstrap) return;
    setBusy(true);
    try {
      const result = await api<{ opportunities: Opportunity[]; message?: string }>(
        `/organizations/${bootstrap.organization.id}/opportunities/generate`,
        { method: "POST" },
      );
      const ranked = sortOpportunities(result.opportunities);
      setOpportunities(ranked);
      setVisibleOpportunityCount(12);
      setOpportunityMessage(result.message ?? (result.opportunities.length ? "Opportunities generated from approved source context." : ""));
      setSelectedOpportunity(ranked[0] ?? null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshProductSurfaces();
      await refreshCurrentWorkspaceState();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Opportunity generation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitAuth(event: React.FormEvent) {
    event.preventDefault();
    const errors = validateAuthForm(authForm, authMode);
    setAuthErrors(errors);
    if (errors.length > 0) return;
    setBusy(true);
    setBootstrapError("");
    try {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      const response =
        authMode === "signup"
          ? await api<AuthResponse>("/auth/signup", {
              method: "POST",
              body: JSON.stringify({
                name: authForm.name,
                email: authForm.email,
                password: authForm.password,
                organization_name: authForm.organization_name,
                website_url: authForm.website_url || null,
                industry: authForm.industry || null,
                description: authForm.description || null,
                audience_summary: authForm.audience_summary || null,
                default_timezone: authForm.default_timezone || "UTC",
              }),
            })
          : await api<AuthResponse>("/auth/login", {
              method: "POST",
              body: JSON.stringify({
                email: authForm.email,
                password: authForm.password,
              }),
            });
      localStorage.setItem(AUTH_TOKEN_KEY, response.token);
      setAuthRequired(false);
      const opportunities = await api<Opportunity[]>(`/organizations/${response.workspace.organization.id}/opportunities`);
      const data = bootstrapFromCurrentWorkspace(response.workspace, opportunities);
      setCurrentUser(response.workspace.user);
      setOnboarding(response.workspace.onboarding);
      setBootstrap(data);
      setSetupForm(setupFromBootstrap(data));
      setOpportunities(sortOpportunities(opportunities));
      setVisibleOpportunityCount(12);
      setActiveView(response.workspace.sources.length > 0 ? "studio" : "sources");
      await Promise.allSettled([
        api<Draft[]>(`/organizations/${response.workspace.organization.id}/calendar`).then(setCalendarItems),
        api<LinkedInIntegration>(`/organizations/${response.workspace.organization.id}/linkedin-integration`).then(setLinkedinIntegration),
        api<PostMemory[]>(`/organizations/${response.workspace.organization.id}/memory`).then(setMemoryItems),
        api<AnalyticsDashboard>(`/organizations/${response.workspace.organization.id}/analytics`).then(setAnalyticsDashboard),
        api<ContentArtifact[]>(`/organizations/${response.workspace.organization.id}/content-artifacts`).then(setContentArtifacts),
        api<StrategyDashboard>(`/organizations/${response.workspace.organization.id}/strategy`).then(setStrategyDashboard),
        api<WorkspaceUser[]>(`/organizations/${response.workspace.organization.id}/users`).then(setUsers),
        api<ApprovalPolicy>(`/organizations/${response.workspace.organization.id}/approval-policy`).then((policy) => {
          setApprovalPolicy(policy);
          setApprovalPolicyDraft(approvalPolicyForm(policy));
        }),
        api<PreferenceSuggestion[]>(`/organizations/${response.workspace.organization.id}/preference-suggestions`).then(setPreferenceSuggestions),
        api<CalendarEvent[]>(`/organizations/${response.workspace.organization.id}/calendar-events`).then(setCalendarEvents),
        api<TrendSignal[]>(`/organizations/${response.workspace.organization.id}/trend-signals`).then(setTrendSignals),
      ]);
      setAuthForm(emptyAuthForm);
      setAuthErrors([]);
      setBootstrapError("");
      setNotice(authMode === "signup" ? "Organization created. Add your first approved source when you are ready." : "Welcome back.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Authentication failed.";
      setBootstrapError(message);
      setAuthErrors(message.split("\n"));
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    setCurrentUser(null);
    setOnboarding(null);
    setBootstrap(null);
    setAuthForm(emptyAuthForm);
    setAuthErrors([]);
    setBootstrapError("");
    setAuthMode("login");
    setAuthRequired(true);
    setNotice("");
  }

  async function skipProfileForNow() {
    if (!bootstrap) return;
    setBusy(true);
    try {
      const state = await api<OnboardingState>(`/organizations/${bootstrap.organization.id}/onboarding/profile`, {
        method: "POST",
        body: JSON.stringify({ skip_profile: true }),
      });
      setOnboarding(state);
      setActiveView("sources");
      setNotice("Profile setup skipped for now. Add an approved source to improve recommendations.");
    } finally {
      setBusy(false);
    }
  }

  if (authRequired && !bootstrap) {
    return (
      <main className="auth-shell">
        <section className="auth-panel">
          <div className="auth-copy">
            <p className="eyebrow">Quainy Vouch</p>
            <h1>Turn real company work into trusted public communication.</h1>
            <p>
              Create your organization, add approved context when ready, and let the system surface source-backed opportunities you can brief,
              review, publish, and learn from.
            </p>
          </div>
          <form className="auth-form" onSubmit={submitAuth} autoComplete={authMode === "signup" ? "off" : "on"}>
            <div className="auth-toggle" aria-label="Authentication mode">
              <button type="button" className={authMode === "signup" ? "active" : ""} onClick={() => setAuthMode("signup")}>
                Sign up
              </button>
              <button type="button" className={authMode === "login" ? "active" : ""} onClick={() => setAuthMode("login")}>
                Log in
              </button>
            </div>
            {authMode === "signup" && (
              <>
                <Field label="Your name" required>
                  <input
                    value={authForm.name}
                    onChange={(event) => setAuthForm({ ...authForm, name: event.target.value })}
                    autoComplete="name"
                  />
                </Field>
                <Field label="Organization" required>
                  <input
                    value={authForm.organization_name}
                    onChange={(event) => setAuthForm({ ...authForm, organization_name: event.target.value })}
                    placeholder="Acme Labs"
                    autoComplete="organization"
                  />
                </Field>
                <Field label="Website">
                  <input
                    value={authForm.website_url}
                    onChange={(event) => setAuthForm({ ...authForm, website_url: event.target.value })}
                    placeholder="https://example.com"
                    autoComplete="url"
                  />
                </Field>
                <Field label="Industry">
                  <input value={authForm.industry} onChange={(event) => setAuthForm({ ...authForm, industry: event.target.value })} />
                </Field>
                <Field label="What do you do?" wide>
                  <textarea
                    value={authForm.description}
                    onChange={(event) => setAuthForm({ ...authForm, description: event.target.value })}
                    placeholder="A short description is enough. You can improve this later."
                  />
                </Field>
              </>
            )}
            <Field label="Email" required>
              <input
                value={authForm.email}
                onChange={(event) => setAuthForm({ ...authForm, email: event.target.value })}
                autoComplete="email"
              />
            </Field>
            <Field label="Password" required>
              <input
                type="password"
                value={authForm.password}
                onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })}
                autoComplete={authMode === "signup" ? "new-password" : "current-password"}
              />
            </Field>
            <ErrorList errors={authErrors} />
            <button className="icon-button primary" type="submit" disabled={busy}>
              <Sparkles size={18} />
              <span>{authMode === "signup" ? "Create workspace" : "Log in"}</span>
            </button>
          </form>
        </section>
      </main>
    );
  }

  if (!bootstrap) {
    return (
      <main className="loading">
        <section className="connection-card">
          <p className="eyebrow">Quainy Vouch</p>
          <h1>{bootstrapError ? "Workspace service is unavailable" : "Loading workspace"}</h1>
          <p>
            {bootstrapError ||
              "Preparing your workspace. If this takes more than a moment, check that the app services are running."}
          </p>
          {bootstrapError && (
            <div className="connection-actions">
              <button className="icon-button primary" onClick={loadWorkspace} title="Retry connection">
                <RefreshCcw size={18} />
                <span>Retry</span>
              </button>
              <span>Check the app services, then retry.</span>
            </div>
          )}
        </section>
      </main>
    );
  }

  async function saveSetup() {
    if (!bootstrap || !setupForm) return;
    const errors = validateSetupForm(setupForm);
    setSetupErrors(errors);
    if (errors.length > 0) return;
    setBusy(true);
    try {
      const organization = await api<Organization>(`/organizations/${bootstrap.organization.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: setupForm.name,
          website_url: setupForm.website_url || null,
          industry: setupForm.industry || null,
          description: setupForm.description || null,
          audience_summary: setupForm.audience_summary || null,
          default_timezone: setupForm.default_timezone || "UTC",
        }),
      });
      const profile = await api<Profile>(`/organizations/${bootstrap.organization.id}/profile`, {
        method: "PATCH",
        body: JSON.stringify({
          one_liner: setupForm.one_liner,
          mission: setupForm.description,
          product_summary: setupForm.description,
          audience: setupForm.audience_summary,
          voice_rules: textToList(setupForm.voice_rules),
          preferred_phrases: textToList(setupForm.preferred_phrases),
          banned_phrases: textToList(setupForm.banned_phrases),
          approved_claims: textToList(setupForm.approved_claims),
          forbidden_claims: textToList(setupForm.forbidden_claims),
          content_pillars: textToList(setupForm.content_pillars),
          sensitive_topics: textToList(setupForm.sensitive_topics),
        }),
      });
      if (linkedinIntegration) {
        setLinkedinIntegration(
          await api<LinkedInIntegration>(`/organizations/${bootstrap.organization.id}/linkedin-integration`, {
            method: "PATCH",
            body: JSON.stringify({
              selected_page_urn: linkedinIntegration.selected_page_urn || null,
              selected_page_name: linkedinIntegration.selected_page_name || null,
              oauth_status: linkedinIntegration.oauth_status || "not_connected",
              permissions: linkedinIntegration.permissions,
              publishing_enabled: linkedinIntegration.publishing_enabled,
            }),
          }),
        );
      }
      const nextBootstrap = { ...bootstrap, organization, profile };
      setBootstrap(nextBootstrap);
      setSetupForm(setupFromBootstrap(nextBootstrap));
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshCurrentWorkspaceState();
      setSetupErrors([]);
      setNotice("Workspace and voice profile saved.");
    } catch (error) {
      setSetupErrors((error instanceof Error ? error.message : "Workspace setup failed.").split("\n"));
      setNotice(error instanceof Error ? error.message : "Workspace setup failed.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshSources(selectedId?: string) {
    if (!bootstrap) return;
    const sources = await api<Source[]>(`/organizations/${bootstrap.organization.id}/sources`);
    setBootstrap({ ...bootstrap, sources });
    if (selectedId) {
      setSelectedSourceId(selectedId);
      setSourceDetail(await api<SourceDetail>(`/sources/${selectedId}`));
    }
  }

  function commitSourceForm(nextForm: SourceForm) {
    setSourceForm(nextForm);
    setSourceDraftsByType((current) => ({ ...current, [nextForm.source_type]: nextForm }));
  }

  function selectSourceType(sourceType: string) {
    setSourceDraftsByType((current) => ({ ...current, [sourceForm.source_type]: sourceForm }));
    setSourceForm(sourceDraftsByType[sourceType] ?? emptySourceFormFor(sourceType));
  }

  async function addSource() {
    if (!bootstrap) return;
    const errors = validateSourceForm(sourceForm);
    setSourceErrors(errors);
    if (errors.length > 0) return;
    setBusy(true);
    try {
      const addedSourceType = sourceForm.source_type;
      const source = await api<Source>(`/organizations/${bootstrap.organization.id}/sources`, {
        method: "POST",
        body: JSON.stringify({
          source_type: sourceForm.source_type,
          title: sourceForm.title,
          uri: sourceForm.uri || null,
          raw_text: sourceForm.raw_text,
          approval_status: sourceForm.approval_status,
          freshness_days: Number(sourceForm.freshness_days) || 180,
        }),
      });
      const clearedForm = emptySourceFormFor(addedSourceType);
      setSourceForm(clearedForm);
      setSourceDraftsByType((current) => ({ ...current, [addedSourceType]: clearedForm }));
      await refreshSources(source.id);
      setOpportunities([]);
      setVisibleOpportunityCount(12);
      setOpportunityMessage("Source library changed. Generate opportunities again to use the latest approved knowledge.");
      setSelectedOpportunity(null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshProductSurfaces();
      await refreshCurrentWorkspaceState();
      setSourceErrors([]);
      setNotice("Source added, ingested, and ready for opportunity generation.");
    } catch (error) {
      setSourceErrors((error instanceof Error ? error.message : "Source could not be added.").split("\n"));
      setNotice(error instanceof Error ? error.message : "Source could not be added.");
    } finally {
      setBusy(false);
    }
  }

  async function updateSourceStatus(sourceId: string, approvalStatus: string) {
    setBusy(true);
    try {
      await api<Source>(`/sources/${sourceId}`, {
        method: "PATCH",
        body: JSON.stringify({ approval_status: approvalStatus }),
      });
      await refreshSources(sourceId);
      setOpportunities([]);
      setVisibleOpportunityCount(12);
      setOpportunityMessage("Source availability changed. Generate opportunities again so disabled or archived sources are excluded.");
      setSelectedOpportunity(null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshProductSurfaces();
      setNotice(`Source marked ${approvalStatus}.`);
    } finally {
      setBusy(false);
    }
  }

  async function refreshSource(sourceId: string) {
    setBusy(true);
    try {
      await api(`/sources/${sourceId}/refresh`, { method: "POST" });
      await refreshSources(sourceId);
      setOpportunities([]);
      setVisibleOpportunityCount(12);
      setOpportunityMessage("Source was re-ingested. Generate opportunities again to use the refreshed evidence.");
      setSelectedOpportunity(null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshProductSurfaces();
      setNotice("Source refreshed and re-ingested.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSourceFile(file: File | undefined) {
    if (!file) return;
    const rawText = await file.text();
    const lowerName = file.name.toLowerCase();
    const extension = lowerName.endsWith(".md") || lowerName.endsWith(".markdown") ? "markdown" : "text";
    const title = file.name.replace(/\.[^/.]+$/, "");
    commitSourceForm({
      ...emptySourceFormFor(extension),
      approval_status: sourceForm.approval_status,
      freshness_days: sourceForm.freshness_days,
      source_type: extension,
      title,
      uri: file.name,
      raw_text: rawText,
    });
  }

  async function createBrief(opportunity: Opportunity) {
    if (!canBuildBrief(opportunity)) {
      setSelectedOpportunity(opportunity);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      setNotice("This trend needs approved company context before a brief can be created.");
      return;
    }
    setBusy(true);
    try {
      setSelectedOpportunity(opportunity);
      setDrafts([]);
      setSelectedDraft(null);
      const brief = await api<ContentBrief>(`/opportunities/${opportunity.id}/briefs`, { method: "POST" });
      setSelectedBrief(brief);
      setActiveView("studio");
      await refreshProductSurfaces();
      await refreshCurrentWorkspaceState();
      setNotice("Brief created from approved source context.");
    } finally {
      setBusy(false);
    }
  }

  async function addCalendarEvent() {
    if (!bootstrap || !calendarEventForm.title.trim() || !calendarEventForm.starts_at) return;
    setBusy(true);
    try {
      await api<CalendarEvent>(`/organizations/${bootstrap.organization.id}/calendar-events`, {
        method: "POST",
        body: JSON.stringify({
          title: calendarEventForm.title,
          event_type: calendarEventForm.event_type,
          starts_at: new Date(calendarEventForm.starts_at).toISOString(),
          ends_at: calendarEventForm.ends_at ? new Date(calendarEventForm.ends_at).toISOString() : null,
          description: calendarEventForm.description || null,
          relevance_terms: textToList(calendarEventForm.relevance_terms),
        }),
      });
      setCalendarEventForm(emptyCalendarEventForm);
      setCalendarEvents(await api<CalendarEvent[]>(`/organizations/${bootstrap.organization.id}/calendar-events`));
      setNotice("Calendar event added for trend relevance checks.");
    } finally {
      setBusy(false);
    }
  }

  async function addTrendSignal() {
    if (!bootstrap || !trendSignalForm.title.trim() || trendSignalForm.summary.trim().length < 10) return;
    setBusy(true);
    try {
      await api<TrendSignal>(`/organizations/${bootstrap.organization.id}/trend-signals`, {
        method: "POST",
        body: JSON.stringify({
          title: trendSignalForm.title,
          summary: trendSignalForm.summary,
          source_name: trendSignalForm.source_name || "Manual trend research",
          source_url: trendSignalForm.source_url || null,
          observed_at: trendSignalForm.observed_at ? new Date(trendSignalForm.observed_at).toISOString() : null,
          relevance_terms: textToList(trendSignalForm.relevance_terms),
        }),
      });
      setTrendSignalForm(emptyTrendSignalForm);
      setTrendSignals(await api<TrendSignal[]>(`/organizations/${bootstrap.organization.id}/trend-signals`));
      setNotice("Trend signal added. Generate trend opportunities when company context is ready.");
    } finally {
      setBusy(false);
    }
  }

  async function generateTrendOpportunities() {
    if (!bootstrap) return;
    setBusy(true);
    try {
      const result = await api<{ opportunities: Opportunity[] }>(`/organizations/${bootstrap.organization.id}/trend-opportunities/generate`, {
        method: "POST",
      });
      const ranked = sortOpportunities(result.opportunities);
      setOpportunities(ranked);
      setVisibleOpportunityCount(12);
      setOpportunityMessage(
        result.opportunities.some((opportunity) => opportunity.status === "warned")
          ? "Trend opportunities generated with warnings for items missing company context."
          : "Trend opportunities generated from calendar and approved company context.",
      );
      setSelectedOpportunity(ranked[0] ?? null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      await refreshProductSurfaces();
    } finally {
      setBusy(false);
    }
  }

  async function generateDraftsFromBrief() {
    if (!selectedBrief) return;
    setBusy(true);
    try {
      const params = formatChoiceParams(formatChoice);
      const result = await api<{ drafts: Draft[] }>(`/briefs/${selectedBrief.id}/drafts${params}`, { method: "POST" });
      setDrafts(result.drafts);
      setSelectedDraft(result.drafts[0] ?? null);
      setActiveView("studio");
      await refreshProductSurfaces();
      await refreshCurrentWorkspaceState();
      setNotice(formatChoiceNotice(formatChoice));
    } finally {
      setBusy(false);
    }
  }

  async function regenerateSelectedDraft() {
    if (!selectedDraft) return;
    setBusy(true);
    try {
      const result = await api<{ drafts: Draft[] }>(`/drafts/${selectedDraft.id}/regenerate`, { method: "POST" });
      setDrafts(result.drafts);
      setSelectedDraft(result.drafts[0] ?? null);
      await refreshProductSurfaces();
      setNotice("Drafts regenerated from the same brief and adapter.");
    } finally {
      setBusy(false);
    }
  }

  async function approveDraft() {
    if (!selectedDraft) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/approve`, {
        method: "POST",
        body: JSON.stringify({
          edited_body: editedBody,
          reason: reviewReason || "Approved in review desk",
        }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      const pkg = await api<ReviewerPackage>(`/drafts/${selectedDraft.id}/reviewer-package`);
      setSelectedDraft(updated);
      setReviewPackage(pkg);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      await refreshMemoryAndAnalytics();
      await refreshProductSurfaces();
      await refreshCurrentWorkspaceState();
      setNotice(updated.status === "pending_approval" ? "Approval recorded. More reviewer approval is required." : "Approved and stored in memory.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Approval failed.");
    } finally {
      setBusy(false);
    }
  }

  async function rejectDraft() {
    if (!selectedDraft) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ edited_body: editedBody, reason: reviewReason }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshProductSurfaces();
      setNotice("Rejected with review signal.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Rejection failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDraftEdit() {
    if (!selectedDraft) return;
    setBusy(true);
    try {
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`, {
        method: "PATCH",
        body: JSON.stringify({ body: editedBody }),
      });
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshProductSurfaces();
      setNotice("Draft edit saved and review checks refreshed.");
    } finally {
      setBusy(false);
    }
  }

  async function exportDraft() {
    if (!selectedDraft) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/export`, { method: "POST" });
      let copied = false;
      try {
        await navigator.clipboard?.writeText(editedBody);
        copied = true;
      } catch {
        copied = false;
      }
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      await refreshMemoryAndAnalytics();
      await refreshProductSurfaces();
      setNotice(copied ? "Exported and copied." : "Exported. Clipboard permission was unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function scheduleDraft() {
    if (!selectedDraft || !scheduleFor) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/schedule`, {
        method: "POST",
        body: JSON.stringify({
          scheduled_for: new Date(scheduleFor).toISOString(),
          reason: reviewReason || "Manual queue intent",
        }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      await refreshProductSurfaces();
      setNotice("Scheduled intent saved to the queue.");
    } finally {
      setBusy(false);
    }
  }

  async function publishDraftToLinkedin() {
    if (!selectedDraft || !linkedinIntegration) return;
    setBusy(true);
    try {
      const result = await api<PublishResult>(`/drafts/${selectedDraft.id}/publish/linkedin`, {
        method: "POST",
        body: JSON.stringify({
          page_urn: linkedinIntegration.selected_page_urn || null,
          page_name: linkedinIntegration.selected_page_name || null,
          reason: reviewReason || "Publish approved LinkedIn post",
        }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      await refreshMemoryAndAnalytics();
      await refreshProductSurfaces();
      setNotice(
        result.status === "published"
          ? `Published to ${result.page_name || result.page_urn}.`
          : result.failure_reason || "Publishing failed; approved content was preserved.",
      );
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Publishing failed.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshCalendar() {
    if (!bootstrap) return;
    setCalendarItems(await api<Draft[]>(`/organizations/${bootstrap.organization.id}/calendar`));
  }

  async function refreshMemoryAndAnalytics() {
    if (!bootstrap) return;
    const [memory, analytics] = await Promise.all([
      api<PostMemory[]>(`/organizations/${bootstrap.organization.id}/memory`),
      api<AnalyticsDashboard>(`/organizations/${bootstrap.organization.id}/analytics`),
    ]);
    setMemoryItems(memory);
    setAnalyticsDashboard(analytics);
    if (!metricsForm.memory_id && memory.length > 0) {
      setMetricsForm((current) => ({ ...current, memory_id: memory[0].id }));
    }
  }

  async function importAnalytics() {
    if (!bootstrap) return;
    setBusy(true);
    try {
      await api<PostMemory[]>(`/organizations/${bootstrap.organization.id}/analytics/import`, { method: "POST" });
      await refreshMemoryAndAnalytics();
      await refreshProductSurfaces();
      setNotice("Analytics imported for published LinkedIn memory.");
    } finally {
      setBusy(false);
    }
  }

  async function saveManualMetrics() {
    if (!metricsForm.memory_id) return;
    setBusy(true);
    try {
      await api<PostMemory>(`/memory/${metricsForm.memory_id}/performance`, {
        method: "POST",
        body: JSON.stringify({
          impressions: Number(metricsForm.impressions) || 0,
          reactions: Number(metricsForm.reactions) || 0,
          comments: Number(metricsForm.comments) || 0,
          shares: Number(metricsForm.shares) || 0,
          clicks: Number(metricsForm.clicks) || 0,
          source: "manual",
        }),
      });
      setMetricsForm({ ...metricsForm, impressions: "", reactions: "", comments: "", shares: "", clicks: "" });
      await refreshMemoryAndAnalytics();
      await refreshProductSurfaces();
      setNotice("Manual performance metrics saved.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshUsers() {
    if (!bootstrap) return;
    setUsers(await api<WorkspaceUser[]>(`/organizations/${bootstrap.organization.id}/users`));
  }

  async function addUser() {
    if (!bootstrap || !userForm.name.trim()) return;
    setBusy(true);
    try {
      await api<WorkspaceUser>(`/organizations/${bootstrap.organization.id}/users`, {
        method: "POST",
        body: JSON.stringify({
          name: userForm.name,
          email: userForm.email || null,
          role: userForm.role,
        }),
      });
      setUserForm(emptyUserForm);
      await refreshUsers();
      setNotice("Team user added.");
    } finally {
      setBusy(false);
    }
  }

  async function updateUserRole(userId: string, role: WorkspaceUser["role"]) {
    if (!bootstrap) return;
    setBusy(true);
    try {
      await api<WorkspaceUser>(`/organizations/${bootstrap.organization.id}/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      await refreshUsers();
      setNotice("User role updated.");
    } finally {
      setBusy(false);
    }
  }

  async function saveApprovalPolicy() {
    if (!bootstrap || !approvalPolicyDraft) return;
    setBusy(true);
    try {
      const policy = await api<ApprovalPolicy>(`/organizations/${bootstrap.organization.id}/approval-policy`, {
        method: "PATCH",
        body: JSON.stringify({
          required_reviewer_count: Number(approvalPolicyDraft.required_reviewer_count) || 1,
          require_approval_before_export: approvalPolicyDraft.require_approval_before_export,
          require_approval_before_publish: approvalPolicyDraft.require_approval_before_publish,
          allow_risk_override: approvalPolicyDraft.allow_risk_override,
        }),
      });
      setApprovalPolicy(policy);
      setApprovalPolicyDraft(approvalPolicyForm(policy));
      setNotice("Approval policy saved.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Approval policy update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function generatePreferenceSuggestions() {
    if (!bootstrap) return;
    setBusy(true);
    try {
      const suggestions = await api<PreferenceSuggestion[]>(
        `/organizations/${bootstrap.organization.id}/preference-suggestions/generate`,
        { method: "POST" },
      );
      setPreferenceSuggestions(suggestions);
      setNotice(suggestions.length ? "Preference suggestions generated from review signals." : "No repeated preference signal yet.");
    } finally {
      setBusy(false);
    }
  }

  async function decidePreferenceSuggestion(suggestionId: string, action: "approve" | "dismiss") {
    if (!bootstrap) return;
    setBusy(true);
    try {
      await api<PreferenceSuggestion>(`/preference-suggestions/${suggestionId}/${action}`, {
        method: "POST",
        body: JSON.stringify({ reason: action === "approve" ? "Approved from preference panel." : "Dismissed from preference panel." }),
      });
      setPreferenceSuggestions(await api<PreferenceSuggestion[]>(`/organizations/${bootstrap.organization.id}/preference-suggestions`));
      const profile = await api<Profile>(`/organizations/${bootstrap.organization.id}/profile`);
      const nextBootstrap = { ...bootstrap, profile };
      setBootstrap(nextBootstrap);
      setSetupForm(setupFromBootstrap(nextBootstrap));
      setNotice(action === "approve" ? "Preference suggestion applied to profile." : "Preference suggestion dismissed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Quainy Vouch</p>
          <h1>{bootstrap.organization.name}</h1>
        </div>
        <div className="status-strip">
          <span>{healthLabel}</span>
          <span>{bootstrap.profile.content_pillars.length} pillars</span>
          <span>{onboarding ? `${onboarding.completion_percent}% onboarded` : currentUser?.role ?? "workspace"}</span>
          <button className="text-button" onClick={signOut} type="button">Sign out</button>
        </div>
      </header>

      {onboarding && onboarding.completion_percent < 75 && (
        <section className="onboarding-banner">
          <div>
            <p className="eyebrow">Fast onboarding</p>
            <h2>Start light, improve accuracy as you add context.</h2>
            <p>
              Add enough organization detail and one approved source to unlock better-ranked opportunities. You can refine voice, claims,
              sources, and integrations later.
            </p>
          </div>
          <div className="onboarding-progress">
            <strong>{onboarding.completion_percent}%</strong>
            <span>{onboarding.completed_steps.map((step) => step.replace(/_/g, " ")).join(" / ")}</span>
          </div>
          <div className="onboarding-actions">
            <button className="icon-button" onClick={() => setActiveView("settings")} type="button">
              <Save size={16} />
              <span>Org details</span>
            </button>
            {!onboarding.completed_steps.includes("profile_skipped") && !onboarding.completed_steps.includes("profile_started") && (
              <button className="icon-button" onClick={skipProfileForNow} type="button" disabled={busy}>
                <X size={16} />
                <span>Skip profile</span>
              </button>
            )}
            <button className="icon-button primary" onClick={() => setActiveView("sources")} type="button">
              <Upload size={16} />
              <span>Add source</span>
            </button>
          </div>
        </section>
      )}

      <nav className="view-nav" aria-label="Workspace views">
        {viewItems.map((item, index) => (
          <button
            className={activeView === item.id ? "active" : ""}
            key={item.id}
            onClick={() => setActiveView(item.id)}
            title={item.title}
          >
            <span>{index + 1}</span>
            <strong>{item.label}</strong>
            <small>{item.badge}</small>
          </button>
        ))}
      </nav>

      <section className="workspace">
        <aside className="rail">
          <section className="panel">
            <div className="panel-title">
              <Library size={18} />
              <h2>Sources</h2>
            </div>
            <div className="source-list-summary">
              <span>{approvedSources.length} approved</span>
              <span>{disabledSources.length} disabled</span>
              <span>{archivedSources.length} archived</span>
            </div>
            <div className="source-list">
              {railSources.map((source) => (
                <button
                  className={`source-row source-button ${selectedSourceId === source.id ? "selected" : ""}`}
                  key={source.id}
                  onClick={() => setSelectedSourceId(source.id)}
                >
                  <FileText size={16} />
                  <div>
                    <strong>{source.title}</strong>
                    <span>{source.approval_status}</span>
                  </div>
                </button>
              ))}
              {railSourceOverflow > 0 && (
                <button className="source-overflow-note" onClick={() => setActiveView("sources")} type="button">
                  View {railSourceOverflow} more source{railSourceOverflow === 1 ? "" : "s"} in Sources
                </button>
              )}
            </div>
          </section>

          <section className="panel">
            <div className="panel-title">
              <ShieldCheck size={18} />
              <h2>Voice</h2>
            </div>
            <div className="tag-wrap">
              {bootstrap.profile.preferred_phrases.map((phrase) => (
                <span className="tag" key={phrase}>
                  {phrase}
                </span>
              ))}
            </div>
          </section>
        </aside>

        <section className="main-column">
          <section className="view-hero">
            <div>
              <p className="eyebrow">{currentView.eyebrow}</p>
              <h2>{currentView.title}</h2>
              <p>{currentView.description}</p>
            </div>
            <span>{currentView.badge}</span>
          </section>

          {activeView === "library" && (
            <section className="panel band library-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Library</p>
                  <h2>Content memory and pipeline</h2>
                </div>
                <button className="icon-button" onClick={() => setActiveView("studio")} title="Open studio">
                  <FileCheck2 size={18} />
                  <span>Open studio</span>
                </button>
              </div>
              <div className="library-value-grid">
                {libraryMetrics.map((metric) => (
                  <article className="library-value-card" key={metric.label}>
                    <span>{metric.label}</span>
                    <strong>{metric.value}</strong>
                    <p>{metric.detail}</p>
                  </article>
                ))}
              </div>
              <div className="library-filter-bar" aria-label="Content library filters">
                <div className="filter-group">
                  {statusOptions.map((option) => (
                    <button
                      className={libraryStatusFilter === option.id ? "active" : ""}
                      key={option.id}
                      onClick={() => setLibraryStatusFilter(option.id)}
                      type="button"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                <select value={libraryPlatformFilter} onChange={(event) => setLibraryPlatformFilter(event.target.value)}>
                  <option value="all">All platforms</option>
                  {availableLibraryPlatforms.map((platform) => (
                    <option value={platform} key={platform}>
                      {platform}
                    </option>
                  ))}
                </select>
              </div>
              <div className="artifact-grid">
                {visibleContentArtifacts.map((artifact) => {
                  const matchingDraft = drafts.find((draft) => draft.id === artifact.id);
                  return (
                    <article className={`artifact-card ${artifact.kind}-artifact`} key={`${artifact.kind}-${artifact.id}`}>
                      <span>
                        {artifact.kind} / {artifact.platform ?? "source"} / {artifact.status.replace("_", " ")}
                      </span>
                      <strong>{artifact.title}</strong>
                      <p>{artifact.excerpt}</p>
                      <small>
                        {artifact.source_count} source{artifact.source_count === 1 ? "" : "s"} / {artifact.risk_count} risk
                        {artifact.risk_count === 1 ? "" : "s"} / Updated {new Date(artifact.updated_at).toLocaleString()}
                      </small>
                      {artifact.scheduled_for && <small>Scheduled {new Date(artifact.scheduled_for).toLocaleString()}</small>}
                      {artifact.published_at && <small>Published {new Date(artifact.published_at).toLocaleString()}</small>}
                      {matchingDraft && (
                        <button
                          className="text-action"
                          onClick={() => {
                            setSelectedDraft(matchingDraft);
                            setActiveView("studio");
                          }}
                          type="button"
                        >
                          Open in studio
                        </button>
                      )}
                    </article>
                  );
                })}
                {!hasVisibleLibraryArtifacts && (
                  <div className="empty-opportunities library-empty">
                    <Library size={22} />
                    <p>
                      No content matches these filters yet. Generate recommendations, create a brief, or clear the filters to see available work.
                    </p>
                  </div>
                )}
              </div>
            </section>
          )}

          {activeView === "settings" && setupForm && (
            <section className="panel band setup-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Setup</p>
                  <h2>Organization and voice profile</h2>
                </div>
                <div className="setup-actions">
                  <button className="icon-button primary" onClick={saveSetup} disabled={busy} title="Save setup">
                    <Save size={18} />
                    <span>Save setup</span>
                  </button>
                </div>
              </div>
              <ErrorList errors={setupErrors} />
              <div className="section-tabs" role="tablist" aria-label="Profile sections">
                {setupSections.map((section) => (
                  <button
                    className={setupSection === section.id ? "active" : ""}
                    key={section.id}
                    onClick={() => setSetupSection(section.id)}
                    type="button"
                  >
                    {section.label}
                  </button>
                ))}
              </div>
              <div className={`setup-grid setup-${setupSection}`}>
                {setupSection === "company" && (
                  <>
                    <Field label="Organization name">
                      <input
                        value={setupForm.name}
                        onChange={(event) => setSetupForm({ ...setupForm, name: event.target.value })}
                      />
                    </Field>
                    <Field label="Website">
                      <input
                        value={setupForm.website_url}
                        onChange={(event) => setSetupForm({ ...setupForm, website_url: event.target.value })}
                      />
                    </Field>
                    <Field label="Industry">
                      <input
                        value={setupForm.industry}
                        onChange={(event) => setSetupForm({ ...setupForm, industry: event.target.value })}
                      />
                    </Field>
                    <Field label="Timezone">
                      <input
                        value={setupForm.default_timezone}
                        onChange={(event) => setSetupForm({ ...setupForm, default_timezone: event.target.value })}
                      />
                    </Field>
                    <Field label="One-liner" wide>
                      <input
                        value={setupForm.one_liner}
                        onChange={(event) => setSetupForm({ ...setupForm, one_liner: event.target.value })}
                      />
                    </Field>
                    <Field label="Description" wide>
                      <textarea
                        className="small-textarea"
                        value={setupForm.description}
                        onChange={(event) => setSetupForm({ ...setupForm, description: event.target.value })}
                      />
                    </Field>
                    <Field label="Audience" wide>
                      <textarea
                        className="small-textarea"
                        value={setupForm.audience_summary}
                        onChange={(event) => setSetupForm({ ...setupForm, audience_summary: event.target.value })}
                      />
                    </Field>
                  </>
                )}
                {setupSection === "voice" && (
                  <>
                    <Field label="Content pillars" wide>
                      <textarea
                        className="list-textarea"
                        value={setupForm.content_pillars}
                        onChange={(event) => setSetupForm({ ...setupForm, content_pillars: event.target.value })}
                      />
                    </Field>
                    <Field label="Voice rules" wide>
                      <textarea
                        className="list-textarea"
                        value={setupForm.voice_rules}
                        onChange={(event) => setSetupForm({ ...setupForm, voice_rules: event.target.value })}
                      />
                    </Field>
                    <Field label="Preferred phrases">
                      <textarea
                        className="list-textarea"
                        value={setupForm.preferred_phrases}
                        onChange={(event) => setSetupForm({ ...setupForm, preferred_phrases: event.target.value })}
                      />
                    </Field>
                    <Field label="Banned phrases">
                      <textarea
                        className="list-textarea"
                        value={setupForm.banned_phrases}
                        onChange={(event) => setSetupForm({ ...setupForm, banned_phrases: event.target.value })}
                      />
                    </Field>
                    <Field label="Sensitive topics" wide>
                      <textarea
                        className="list-textarea"
                        value={setupForm.sensitive_topics}
                        onChange={(event) => setSetupForm({ ...setupForm, sensitive_topics: event.target.value })}
                      />
                    </Field>
                  </>
                )}
                {setupSection === "claims" && (
                  <>
                    <Field label="Approved claims" wide>
                      <textarea
                        className="list-textarea"
                        value={setupForm.approved_claims}
                        onChange={(event) => setSetupForm({ ...setupForm, approved_claims: event.target.value })}
                      />
                    </Field>
                    <Field label="Forbidden claims" wide>
                      <textarea
                        className="list-textarea"
                        value={setupForm.forbidden_claims}
                        onChange={(event) => setSetupForm({ ...setupForm, forbidden_claims: event.target.value })}
                      />
                    </Field>
                  </>
                )}
                {setupSection === "linkedin" && linkedinIntegration && (
                  <>
                    <Field label="LinkedIn page URN">
                      <input
                        value={linkedinIntegration.selected_page_urn ?? ""}
                        onChange={(event) =>
                          setLinkedinIntegration({ ...linkedinIntegration, selected_page_urn: event.target.value })
                        }
                      />
                    </Field>
                    <Field label="LinkedIn page name">
                      <input
                        value={linkedinIntegration.selected_page_name ?? ""}
                        onChange={(event) =>
                          setLinkedinIntegration({ ...linkedinIntegration, selected_page_name: event.target.value })
                        }
                      />
                    </Field>
                    <Field label="LinkedIn OAuth status">
                      <select
                        value={linkedinIntegration.oauth_status}
                        onChange={(event) =>
                          setLinkedinIntegration({ ...linkedinIntegration, oauth_status: event.target.value })
                        }
                      >
                        <option value="not_connected">Not connected</option>
                        <option value="validated">Validated</option>
                      </select>
                    </Field>
                    <Field label="LinkedIn permissions" wide>
                      <textarea
                        className="list-textarea"
                        value={listToText(linkedinIntegration.permissions)}
                        onChange={(event) =>
                          setLinkedinIntegration({ ...linkedinIntegration, permissions: textToList(event.target.value) })
                        }
                      />
                    </Field>
                  </>
                )}
              </div>
              {notice && <p className="notice">{notice}</p>}
            </section>
          )}

          {activeView === "settings" && <section className="panel band team-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Team</p>
                <h2>Users and roles</h2>
              </div>
              <button className="icon-button primary" onClick={addUser} disabled={busy || !userForm.name.trim()} title="Add user">
                <Plus size={18} />
                <span>Add user</span>
              </button>
            </div>
            <div className="team-form">
              <input
                value={userForm.name}
                onChange={(event) => setUserForm({ ...userForm, name: event.target.value })}
                placeholder="Name"
              />
              <input
                value={userForm.email}
                onChange={(event) => setUserForm({ ...userForm, email: event.target.value })}
                placeholder="Email"
              />
              <select
                value={userForm.role}
                onChange={(event) => setUserForm({ ...userForm, role: event.target.value as WorkspaceUser["role"] })}
              >
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
                    onChange={(event) => updateUserRole(user.id, event.target.value as WorkspaceUser["role"])}
                    disabled={busy || user.id === "local_user"}
                  >
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                    <option value="reviewer">Reviewer</option>
                    <option value="owner">Owner</option>
                  </select>
                </article>
              ))}
            </div>
            {approvalPolicyDraft && (
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
                      onChange={(event) =>
                        setApprovalPolicyDraft({ ...approvalPolicyDraft, required_reviewer_count: event.target.value })
                      }
                      inputMode="numeric"
                    />
                  </label>
                  <label className="check-field">
                    <input
                      type="checkbox"
                      checked={approvalPolicyDraft.require_approval_before_export}
                      onChange={(event) =>
                        setApprovalPolicyDraft({ ...approvalPolicyDraft, require_approval_before_export: event.target.checked })
                      }
                    />
                    <span>Require approval before export</span>
                  </label>
                  <label className="check-field">
                    <input
                      type="checkbox"
                      checked={approvalPolicyDraft.require_approval_before_publish}
                      onChange={(event) =>
                        setApprovalPolicyDraft({ ...approvalPolicyDraft, require_approval_before_publish: event.target.checked })
                      }
                    />
                    <span>Require approval before publish</span>
                  </label>
                  <label className="check-field">
                    <input
                      type="checkbox"
                      checked={approvalPolicyDraft.allow_risk_override}
                      onChange={(event) =>
                        setApprovalPolicyDraft({ ...approvalPolicyDraft, allow_risk_override: event.target.checked })
                      }
                    />
                    <span>Allow logged risk override</span>
                  </label>
                </div>
                <button className="icon-button" onClick={saveApprovalPolicy} disabled={busy} title="Save approval policy">
                  <Save size={18} />
                  <span>Save policy</span>
                </button>
              </div>
            )}
          </section>}

          {activeView === "sources" && <section className="panel band source-library-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Source Library</p>
                <h2>Approved company knowledge</h2>
              </div>
              <button className="icon-button primary" onClick={addSource} disabled={busy} title="Add source">
                <Plus size={18} />
                <span>Add source</span>
              </button>
            </div>
            <ErrorList errors={sourceErrors} />
            <div className="source-health-grid">
              <article className={`source-health-tile ${approvedSources.length > 0 ? "healthy" : "blocked"}`}>
                <span>Approved</span>
                <strong>{approvedSources.length}</strong>
                <p>{approvedSources.length > 0 ? "Available to recommendations and drafts." : "Add approved context to unlock safe generation."}</p>
              </article>
              <article className="source-health-tile">
                <span>Disabled</span>
                <strong>{disabledSources.length}</strong>
                <p>Not used as active evidence until re-approved.</p>
              </article>
              <article className="source-health-tile">
                <span>Archived</span>
                <strong>{archivedSources.length}</strong>
                <p>Kept for audit history, not active guidance.</p>
              </article>
              <article className="source-health-tile">
                <span>Library</span>
                <strong>{bootstrap.sources.length}</strong>
                <p>Total source records in this workspace.</p>
              </article>
            </div>
            <div className="source-guide-grid" aria-label="Source onboarding options">
              {sourceGuideCards.map((guide) => (
                <button
                  className={sourceForm.source_type === guide.source_type ? "source-guide-card active" : "source-guide-card"}
                  key={guide.id}
                  onClick={() => selectSourceType(guide.source_type)}
                  type="button"
                >
                  <span>{guide.source_type.replace("_", " ")}</span>
                  <strong>{guide.title}</strong>
                  <small>{guide.description}</small>
                </button>
              ))}
            </div>
            <div className="source-library-grid">
              <section className="source-form">
                <div className="source-primary-grid">
                  <Field label="Knowledge title" required>
                    <input
                      value={sourceForm.title}
                      onChange={(event) => commitSourceForm({ ...sourceForm, title: event.target.value })}
                      placeholder={sourceCopy.titlePlaceholder}
                    />
                  </Field>
                  {sourceCopy.showUpload ? (
                    <label className="upload-target">
                      <Upload size={18} />
                      <span>Upload file</span>
                      <input type="file" accept=".md,.markdown,.txt,text/plain,text/markdown" onChange={(event) => handleSourceFile(event.target.files?.[0])} />
                    </label>
                  ) : (
                    <div className="source-mode-note">
                      <span>{sourceForm.source_type.replace("_", " ")}</span>
                      <p>No file needed for this source type.</p>
                    </div>
                  )}
                </div>
                {sourceCopy.uriLabel && (
                  <Field label={sourceCopy.uriLabel} wide required>
                    <input
                      value={sourceForm.uri}
                      onChange={(event) => commitSourceForm({ ...sourceForm, uri: event.target.value })}
                      placeholder={sourceCopy.uriPlaceholder}
                    />
                  </Field>
                )}
                <Field label={sourceCopy.textLabel} wide required>
                  <textarea
                    className="source-textarea"
                    value={sourceForm.raw_text}
                    onChange={(event) => commitSourceForm({ ...sourceForm, raw_text: event.target.value })}
                    placeholder={sourceCopy.textPlaceholder}
                  />
                </Field>
                <div className="source-availability-panel">
                  <div className="source-availability-copy">
                    <span>Availability</span>
                    <p>Choose whether this source can be used as active evidence.</p>
                  </div>
                  <div className="source-availability-controls">
                    <div className="source-status-options" aria-label="Source availability">
                      {["approved", "disabled", "archived"].map((status) => (
                        <button
                          className={sourceForm.approval_status === status ? "active" : ""}
                          key={status}
                          onClick={() => commitSourceForm({ ...sourceForm, approval_status: status })}
                          type="button"
                        >
                          {status}
                        </button>
                      ))}
                    </div>
                    <label className="refresh-field">
                      <span>Refresh days</span>
                      <input
                        value={sourceForm.freshness_days}
                        onChange={(event) => commitSourceForm({ ...sourceForm, freshness_days: event.target.value })}
                        inputMode="numeric"
                      />
                    </label>
                  </div>
                </div>
              </section>

              <section className="source-detail">
                {sourceDetail ? (
                  <>
                    <div className="source-detail-header">
                      <div>
                        <p className="eyebrow">Source Detail</p>
                        <h3>{sourceDetail.source.title}</h3>
                      </div>
                      <span className={`status-pill ${sourceDetail.source.approval_status}`}>{sourceDetail.source.approval_status}</span>
                    </div>
                    <div className="source-actions">
                      {["approved", "disabled", "archived"].map((status) => (
                        <button
                          className={sourceDetail.source.approval_status === status ? "active" : ""}
                          key={status}
                          onClick={() => updateSourceStatus(sourceDetail.source.id, status)}
                          disabled={busy}
                        >
                          {status}
                        </button>
                      ))}
                      <button onClick={() => refreshSource(sourceDetail.source.id)} disabled={busy} title="Refresh source">
                        <RefreshCcw size={15} />
                        refresh
                      </button>
                    </div>
                    <div className="source-meta">
                      <div>
                        <span>Type</span>
                        <strong>{sourceDetail.source.source_type.replace("_", " ")}</strong>
                      </div>
                      <div>
                        <span>Chunks</span>
                        <strong>{sourceDetail.chunk_count}</strong>
                      </div>
                      <div>
                        <span>Refresh</span>
                        <strong>{sourceDetail.source.freshness_days} days</strong>
                      </div>
                      {sourceDetail.source.uri && (
                        <div>
                          <span>Origin</span>
                          <strong>{sourceDetail.source.uri}</strong>
                        </div>
                      )}
                    </div>
                    <div className="source-raw-block">
                      <div>
                        <h4>Source text</h4>
                        <span>{sourceDetail.raw_text.length.toLocaleString()} chars</span>
                      </div>
                      <p className="source-raw">{sourceDetail.raw_text}</p>
                    </div>
                    <div className="audit-list">
                      <div className="audit-heading">
                        <h4>Audit events</h4>
                        {sourceAuditLogs.length > 0 && (
                          <span>
                            Latest {visibleSourceAuditLogs.length} of {sourceAuditLogs.length} - IST
                          </span>
                        )}
                      </div>
                      {sourceAuditLogs.length > 0 ? (
                        <div className="audit-scroll">
                          {visibleSourceAuditLogs.map((log) => (
                            <div className="audit-row" key={log.id}>
                              <strong>{log.action}</strong>
                              <span>{formatAuditTime(log.created_at)}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="empty-results">No audit events recorded yet.</p>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="empty-detail">
                    <Library size={24} />
                    <strong>Choose a source to inspect</strong>
                    <p>Source text, status, chunk count, origin, refresh policy, and audit events will appear here.</p>
                    <div className="empty-detail-stats">
                      <span>{approvedSources.length} approved</span>
                      <span>{disabledSources.length} disabled</span>
                      <span>{archivedSources.length} archived</span>
                    </div>
                  </div>
                )}
              </section>
            </div>
          </section>}

          {activeView === "calendar" && <section className="panel band trend-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Calendar And Trends</p>
                <h2>Context-aware market moments</h2>
              </div>
              <button className="icon-button primary" onClick={generateTrendOpportunities} disabled={busy || trendSignals.length === 0} title="Generate trend opportunities">
                <Sparkles size={18} />
                <span>Generate trends</span>
              </button>
            </div>
            <div className="trend-grid">
              <section className="trend-form-block">
                <div className="panel-title">
                  <CalendarClock size={17} />
                  <h2>Calendar</h2>
                </div>
                <div className="trend-form">
                  <label className="micro-field">
                    <span>Event title</span>
                    <input
                      value={calendarEventForm.title}
                      onChange={(event) => setCalendarEventForm({ ...calendarEventForm, title: event.target.value })}
                    />
                  </label>
                  <label className="micro-field">
                    <span>Type</span>
                    <select
                      value={calendarEventForm.event_type}
                      onChange={(event) =>
                        setCalendarEventForm({ ...calendarEventForm, event_type: event.target.value as CalendarEvent["event_type"] })
                      }
                    >
                      <option value="company">Company</option>
                      <option value="public">Public</option>
                    </select>
                  </label>
                  <label className="micro-field">
                    <span>Starts</span>
                    <input
                      type="datetime-local"
                      value={calendarEventForm.starts_at}
                      onChange={(event) => setCalendarEventForm({ ...calendarEventForm, starts_at: event.target.value })}
                    />
                  </label>
                  <label className="micro-field">
                    <span>Ends</span>
                    <input
                      type="datetime-local"
                      value={calendarEventForm.ends_at}
                      onChange={(event) => setCalendarEventForm({ ...calendarEventForm, ends_at: event.target.value })}
                    />
                  </label>
                  <label className="micro-field wide">
                    <span>Description</span>
                    <textarea
                      className="small-textarea"
                      value={calendarEventForm.description}
                      onChange={(event) => setCalendarEventForm({ ...calendarEventForm, description: event.target.value })}
                    />
                  </label>
                  <label className="micro-field wide">
                    <span>Relevance terms</span>
                    <textarea
                      className="small-textarea"
                      value={calendarEventForm.relevance_terms}
                      onChange={(event) => setCalendarEventForm({ ...calendarEventForm, relevance_terms: event.target.value })}
                    />
                  </label>
                  <button
                    className="icon-button"
                    onClick={addCalendarEvent}
                    disabled={busy || !calendarEventForm.title.trim() || !calendarEventForm.starts_at}
                    title="Add calendar event"
                  >
                    <Plus size={18} />
                    <span>Add event</span>
                  </button>
                </div>
                <div className="trend-list">
                  {calendarEvents.map((eventItem) => (
                    <article className="trend-row" key={eventItem.id}>
                      <div>
                        <strong>{eventItem.title}</strong>
                        <span>{eventItem.event_type} / {new Date(eventItem.starts_at).toLocaleDateString()}</span>
                      </div>
                      {eventItem.description && <p>{eventItem.description}</p>}
                    </article>
                  ))}
                  {calendarEvents.length === 0 && <p className="empty-results">Company launches, campaigns, holidays, and industry events help the relevance gate decide what is timely.</p>}
                </div>
              </section>

              <section className="trend-form-block">
                <div className="panel-title">
                  <Sparkles size={17} />
                  <h2>Trend Signals</h2>
                </div>
                <div className="trend-form">
                  <label className="micro-field">
                    <span>Trend title</span>
                    <input
                      value={trendSignalForm.title}
                      onChange={(event) => setTrendSignalForm({ ...trendSignalForm, title: event.target.value })}
                    />
                  </label>
                  <label className="micro-field">
                    <span>Source</span>
                    <input
                      value={trendSignalForm.source_name}
                      onChange={(event) => setTrendSignalForm({ ...trendSignalForm, source_name: event.target.value })}
                    />
                  </label>
                  <label className="micro-field">
                    <span>Source URL</span>
                    <input
                      value={trendSignalForm.source_url}
                      onChange={(event) => setTrendSignalForm({ ...trendSignalForm, source_url: event.target.value })}
                    />
                  </label>
                  <label className="micro-field">
                    <span>Observed</span>
                    <input
                      type="datetime-local"
                      value={trendSignalForm.observed_at}
                      onChange={(event) => setTrendSignalForm({ ...trendSignalForm, observed_at: event.target.value })}
                    />
                  </label>
                  <label className="micro-field wide">
                    <span>Summary</span>
                    <textarea
                      className="small-textarea"
                      value={trendSignalForm.summary}
                      onChange={(event) => setTrendSignalForm({ ...trendSignalForm, summary: event.target.value })}
                    />
                  </label>
                  <label className="micro-field wide">
                    <span>Relevance terms</span>
                    <textarea
                      className="small-textarea"
                      value={trendSignalForm.relevance_terms}
                      onChange={(event) => setTrendSignalForm({ ...trendSignalForm, relevance_terms: event.target.value })}
                    />
                  </label>
                  <button
                    className="icon-button"
                    onClick={addTrendSignal}
                    disabled={busy || !trendSignalForm.title.trim() || trendSignalForm.summary.trim().length < 10}
                    title="Add trend signal"
                  >
                    <Plus size={18} />
                    <span>Add trend</span>
                  </button>
                </div>
                <div className="trend-list">
                  {trendSignals.map((trend) => (
                    <article className="trend-row" key={trend.id}>
                      <div>
                        <strong>{trend.title}</strong>
                        <span>{trend.source_name} / {new Date(trend.observed_at).toLocaleDateString()}</span>
                      </div>
                      <p>{trend.summary}</p>
                    </article>
                  ))}
                  {trendSignals.length === 0 && <p className="empty-results">Trend research is filtered against approved company sources before it can become a usable opportunity.</p>}
                </div>
              </section>
            </div>
          </section>}

          {activeView === "studio" && <section className="panel band">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Opportunities</p>
                <h2>Source-backed angles</h2>
              </div>
              <button className="icon-button primary" onClick={generateOpportunities} disabled={busy} title="Generate opportunities">
                <RefreshCcw size={18} />
                <span>Generate</span>
              </button>
            </div>
            {rankedOpportunities.length > 0 && (
              <div className="opportunity-rank-bar">
                <div>
                  <span>{visibleOpportunities.length} shown</span>
                  <strong>{rankedOpportunities.length} ranked source-backed angle{rankedOpportunities.length === 1 ? "" : "s"}</strong>
                </div>
                <p>Sorted by relevance, confidence, freshness, source coverage, and latest source activity.</p>
              </div>
            )}
            <div className={`studio-source-strip ${approvedSources.length > 0 ? "ready" : "blocked"}`}>
              <div>
                <span>{approvedSources.length} active source{approvedSources.length === 1 ? "" : "s"}</span>
                <strong>{activeSourceSummary || "No approved knowledge available"}</strong>
                {sampleSourceActive && (
                  <p>
                    Sample context is still active. Disable it in Sources when you want recommendations to come only from your own company knowledge.
                  </p>
                )}
              </div>
              <small>Draft format is selected after a brief is created.</small>
            </div>
            <div className="opportunity-grid">
              {visibleOpportunities.length > 0 ? (
                visibleOpportunities.map((opportunity, index) => (
                  <button
                    className={`opportunity-card ${selectedOpportunity?.id === opportunity.id ? "selected" : ""} ${opportunity.status === "warned" ? "warned" : ""}`}
                    key={opportunity.id}
                    onClick={() => createBrief(opportunity)}
                    disabled={busy}
                  >
                    <div className="opportunity-scores">
                      <span>#{index + 1}</span>
                      <span className="score">{Math.round(opportunity.relevance_score * 100)}% relevant</span>
                      <span>{Math.round(opportunity.freshness_score * 100)}% fresh</span>
                      <span>{Math.round(opportunity.confidence_score * 100)}% confidence</span>
                      <span>{opportunity.source_ids.length} source{opportunity.source_ids.length === 1 ? "" : "s"}</span>
                      {opportunity.status === "warned" && <span>warning</span>}
                    </div>
                    <h3>{opportunity.title}</h3>
                    <p>{opportunity.reason_today}</p>
                    <small>
                      Evidence: {opportunity.source_ids.map((sourceId) => sourceTitleById.get(sourceId) ?? sourceId).join(", ") || "No approved source"}
                    </small>
                    <small>Next step: create a brief from this source-backed angle.</small>
                    {opportunityWarnings(opportunity).length > 0 && (
                      <ul className="warning-list">
                        {opportunityWarnings(opportunity).map((warning) => (
                          <li key={warning}>{warning}</li>
                        ))}
                      </ul>
                    )}
                  </button>
                ))
              ) : (
                <div className="empty-opportunities">
                  <Sparkles size={22} />
                  <p>{opportunityMessage || "Generate opportunities after adding enough approved source context."}</p>
                </div>
              )}
            </div>
            {hiddenOpportunityCount > 0 && (
              <div className="opportunity-load-row">
                <span>{hiddenOpportunityCount} lower-ranked angle{hiddenOpportunityCount === 1 ? "" : "s"} available</span>
                <button
                  className="icon-button"
                  onClick={() => setVisibleOpportunityCount((current) => current + 12)}
                  type="button"
                  title="Show more source-backed angles"
                >
                  <Plus size={18} />
                  <span>Show more</span>
                </button>
              </div>
            )}
            {opportunityMessage && opportunities.length > 0 && <p className="notice">{opportunityMessage}</p>}
          </section>}

          {activeView === "studio" && selectedBrief && (
            <section className="panel band brief-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Brief</p>
                  <h2>Source brief for {selectedFormatLabel}</h2>
                </div>
                <div className="format-actions">
                  <select value={formatChoice} onChange={(event) => selectContentFormat(event.target.value as FormatChoice)}>
                    <option value="linkedin_company_post">LinkedIn post</option>
                    <option value="blog_outline">Blog outline</option>
                    <option value="newsletter_email">Newsletter email</option>
                    <option value="instagram_caption">Instagram caption</option>
                    <option value="instagram_carousel_outline">Instagram carousel</option>
                  </select>
                  <button className="icon-button primary" onClick={generateDraftsFromBrief} disabled={busy} title="Generate drafts">
                    <FileCheck2 size={18} />
                    <span>Generate drafts</span>
                  </button>
                </div>
              </div>
              <div className="brief-grid">
                <section className="brief-summary">
                  <span>Selected format</span>
                  <p>{selectedFormatLabel}</p>
                  <span>Objective</span>
                  <p>{selectedBrief.objective}</p>
                  <span>Audience</span>
                  <p>{selectedBrief.audience}</p>
                  <span>Key message</span>
                  <p>{selectedBrief.key_message}</p>
                </section>
                <section className="brief-list">
                  <h3>Supporting points</h3>
                  <ul className="plain-list">
                    {selectedBrief.supporting_points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </section>
                <section className="brief-list">
                  <h3>Guardrails</h3>
                  <ul className="plain-list">
                    {[...selectedBrief.do_not_say, ...selectedBrief.risks].map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>
              </div>
            </section>
          )}

          {activeView === "studio" && drafts.length > 0 && (
            <section className="panel band">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Drafts</p>
                  <h2>{draftFormatLabel(selectedDraft)}</h2>
                </div>
                <Sparkles size={20} />
              </div>
              <div className="draft-tabs">
                {drafts.map((draft, index) => (
                  <button
                    key={draft.id}
                    className={selectedDraft?.id === draft.id ? "active" : ""}
                    onClick={() => setSelectedDraft(draft)}
                  >
                    Variant {index + 1}
                  </button>
                ))}
              </div>
              {selectedDraft && (
                <div className="draft-meta-row">
                  <span>{String(selectedDraft.generation_metadata.adapter_name ?? selectedDraft.platform ?? "adapter")}</span>
                  <span>{String(selectedDraft.generation_metadata.prompt_version ?? "prompt tracked")}</span>
                  <span>{selectedDraft.source_ids.length} source{selectedDraft.source_ids.length === 1 ? "" : "s"}</span>
                  <span>{selectedDraftMatchesFormat ? "Matches selected format" : "Different from selected format"}</span>
                  <span>{Object.keys(selectedDraft.source_map).length} source map candidate{Object.keys(selectedDraft.source_map).length === 1 ? "" : "s"}</span>
                  {selectedDraft.published_at && <span>Published {new Date(selectedDraft.published_at).toLocaleString()}</span>}
                  {selectedDraft.publish_result?.status === "failed" && <span>Publish failed</span>}
                </div>
              )}
            </section>
          )}

          {activeView === "studio" && selectedDraft && (
            <section className="panel band preview-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Preview</p>
                  <h2>{platformDisplayName(selectedDraft.platform)} artifact</h2>
                </div>
                <span className="platform-count">{contentTypeDisplayName(selectedDraft.content_type)}</span>
              </div>
              <div className="preview-layout">
                <article className={`platform-preview ${selectedDraft.platform}`}>
                  <div className="preview-chrome">
                    <div>
                      <span>{platformDisplayName(selectedDraft.platform)}</span>
                      <strong>{selectedDraft.hook || draftFormatLabel(selectedDraft)}</strong>
                    </div>
                    <small>{selectedDraft.status.replace("_", " ")}</small>
                  </div>
                  <div className="preview-body">
                    {previewParagraphs.length > 0 ? (
                      previewParagraphs.map((paragraph, index) => <p key={`${selectedDraft.id}-paragraph-${index}`}>{paragraph}</p>)
                    ) : (
                      <p>{selectedDraft.body}</p>
                    )}
                  </div>
                </article>

                <aside className="trust-summary">
                  <div className="trust-card strong">
                    <span>Evidence</span>
                    <strong>{selectedDraft.source_ids.length}</strong>
                    <small>approved source{selectedDraft.source_ids.length === 1 ? "" : "s"}</small>
                  </div>
                  <div className={unsupportedClaimCount > 0 ? "trust-card warning" : "trust-card"}>
                    <span>Claims</span>
                    <strong>
                      {supportedClaimCount}/{selectedDraft.claims.length}
                    </strong>
                    <small>{unsupportedClaimCount > 0 ? `${unsupportedClaimCount} need review` : "supported or non-factual"}</small>
                  </div>
                  <div className={selectedDraft.risk_report.length > 0 ? "trust-card warning" : "trust-card"}>
                    <span>Risk</span>
                    <strong>{selectedDraft.risk_report.length}</strong>
                    <small>{selectedDraft.risk_report.length === 1 ? "review note" : "review notes"}</small>
                  </div>
                  <div className={duplicateMatchCount > 0 ? "trust-card warning" : "trust-card"}>
                    <span>Memory</span>
                    <strong>{duplicateMatchCount}</strong>
                    <small>similar post{duplicateMatchCount === 1 ? "" : "s"}</small>
                  </div>
                  <div className="trust-explain">
                    <span>Generated by</span>
                    <strong>{selectedDraftAdapter}</strong>
                    <small>{selectedDraftPromptVersion}</small>
                  </div>
                  {selectedOpportunity && (
                    <div className="trust-explain">
                      <span>Why today</span>
                      <p>{selectedOpportunity.reason_today}</p>
                    </div>
                  )}
                  {reviewPackage?.source_chunks.length ? (
                    <div className="trust-evidence">
                      <span>Evidence preview</span>
                      {reviewPackage.source_chunks.slice(0, 2).map((chunk) => (
                        <p key={chunk.id}>{chunk.chunk_text}</p>
                      ))}
                    </div>
                  ) : null}
                </aside>
              </div>
            </section>
          )}

          {activeView === "studio" && selectedDraft && trustTimelineItems.length > 0 && (
            <section className="panel band trust-timeline-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Trust History</p>
                  <h2>Why this artifact is reviewable</h2>
                </div>
                <span className="platform-count">{trustTimelineItems.length} signals</span>
              </div>
              <div className="trust-timeline">
                {trustTimelineItems.map((item, index) => (
                  <article className={`trust-step ${item.status}`} key={`${item.step}-${index}-${item.title}`}>
                    <span>{item.step}</span>
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                  </article>
                ))}
              </div>
            </section>
          )}

          {activeView === "studio" && reviewPackage && selectedDraft && (
            <section className="review-grid">
              <section className="panel review-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Review Desk</p>
                    <h2>{selectedDraft.status.replace("_", " ")}</h2>
                  </div>
                  <span className="review-status">{reviewPackage.suggested_action}</span>
                </div>
                <textarea value={editedBody} onChange={(event) => setEditedBody(event.target.value)} />
                {approvalPolicy && (
                  <div className="approval-progress">
                    <span>
                      {Number(approvalProgress.approved_reviewer_count ?? 0)} / {approvalPolicy.required_reviewer_count} approvals
                    </span>
                    <span>{String((approvalProgress.approved_reviewer_ids as string[] | undefined)?.join(", ") || "No approvals yet")}</span>
                  </div>
                )}
                <div className="review-control-stack">
                  <label className="review-note-field">
                    <span>Decision note</span>
                    <input
                      value={reviewReason}
                      onChange={(event) => setReviewReason(event.target.value)}
                      placeholder="Add context for approval, rejection, export, or scheduling"
                    />
                  </label>
                  <div className="review-action-grid">
                    <section className="review-action-card">
                      <div>
                        <span>Review decision</span>
                        <p>Approve only when claims and risk checks are acceptable. Rejections require a note.</p>
                      </div>
                      <div className="action-row">
                        <button className="icon-button" onClick={saveDraftEdit} disabled={busy || editedBody === selectedDraft.body} title="Save edit">
                          <Save size={18} />
                          <span>Save edit</span>
                        </button>
                        <button
                          className="icon-button primary"
                          onClick={approveDraft}
                          disabled={!canApproveDraft}
                          title={approvalBlocked ? "Resolve unsupported claims before approval" : "Approve draft"}
                        >
                          <Check size={18} />
                          <span>Approve</span>
                        </button>
                        <button className="icon-button" onClick={rejectDraft} disabled={busy || !reviewReason.trim()} title="Reject draft">
                          <X size={18} />
                          <span>Reject</span>
                        </button>
                      </div>
                    </section>

                    <section className="review-action-card">
                      <div>
                        <span>Delivery</span>
                        <p>{publishCapabilityText}</p>
                      </div>
                      <div className="action-row">
                        <button className="icon-button" onClick={exportDraft} disabled={busy || !canExportDraft} title="Export draft">
                          <Clipboard size={18} />
                          <span>Export</span>
                        </button>
                        <button
                          className="icon-button"
                          onClick={publishDraftToLinkedin}
                          disabled={busy || !canAttemptLinkedinPublish || !linkedinIntegration?.selected_page_urn}
                          title="Publish approved LinkedIn post"
                        >
                          <Send size={18} />
                          <span>Publish</span>
                        </button>
                        <button
                          className="icon-button"
                          onClick={regenerateSelectedDraft}
                          disabled={busy || !selectedDraft}
                          title="Regenerate drafts"
                        >
                          <RefreshCcw size={18} />
                          <span>Regenerate</span>
                        </button>
                      </div>
                    </section>

                    <section className="review-action-card schedule-card">
                      <div>
                        <span>Schedule intent</span>
                        <p>Save this artifact to the internal calendar for planning. This does not publish to Reddit, blogs, or unsupported channels.</p>
                      </div>
                      <div className="schedule-row">
                        <input
                          type="datetime-local"
                          value={scheduleFor}
                          onChange={(event) => setScheduleFor(event.target.value)}
                          aria-label="Schedule intent date and time"
                        />
                        <button
                          className="icon-button"
                          onClick={scheduleDraft}
                          disabled={busy || !canScheduleDraft || !scheduleFor}
                          title="Save schedule intent"
                        >
                          <CalendarClock size={18} />
                          <span>Schedule</span>
                        </button>
                      </div>
                    </section>
                  </div>
                </div>
                {notice && <p className="notice">{notice}</p>}
              </section>

              <aside className="evidence-column">
                <InsightList title="Risk" icon={<Archive size={17} />} items={selectedDraft.risk_report} />
                <InsightList title="Quality" icon={<ShieldCheck size={17} />} items={selectedDraft.quality_report} />
                {selectedDraft.duplicate_report.similar_posts.length > 0 && (
                  <section className="panel compact">
                    <div className="panel-title">
                      <RefreshCcw size={17} />
                      <h2>Similar Memory</h2>
                    </div>
                    {selectedDraft.duplicate_report.similar_posts.map((post) => (
                      <div className="memory-match" key={post.excerpt}>
                        <strong>{Math.round(post.score * 100)}% similar</strong>
                        <p>{post.excerpt}</p>
                      </div>
                    ))}
                  </section>
                )}
                {reviewPackage.decision_history.length > 0 && (
                  <section className="panel compact">
                    <div className="panel-title">
                      <ShieldCheck size={17} />
                      <h2>Decision History</h2>
                    </div>
                    {reviewPackage.decision_history.map((decision) => (
                      <div className="decision-row" key={decision.id}>
                        <strong>{decision.decision}</strong>
                        <span>{new Date(decision.created_at).toLocaleString()}</span>
                        {decision.reason && <p>{decision.reason}</p>}
                      </div>
                    ))}
                  </section>
                )}
                <section className="panel compact">
                  <div className="panel-title">
                    <FileText size={17} />
                    <h2>Claims</h2>
                  </div>
                  <div className="claim-list">
                    {selectedDraft.claims.map((claim) => (
                      <div className="claim-row" key={claim.text}>
                        <span className={`dot ${claim.support_status}`} />
                        <p>{claim.text}</p>
                      </div>
                    ))}
                  </div>
                </section>
                <section className="panel compact">
                  <div className="panel-title">
                    <Library size={17} />
                    <h2>Evidence</h2>
                  </div>
                  {reviewPackage.source_chunks.slice(0, 4).map((chunk) => (
                    <p className="excerpt" key={chunk.id}>
                      {chunk.chunk_text}
                    </p>
                  ))}
                </section>
              </aside>
            </section>
          )}

          {activeView === "calendar" && <section className="panel band calendar-board-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Calendar</p>
                <h2>Upcoming publishing context</h2>
              </div>
              <span className="platform-count">{calendarEntries.length} dated items</span>
            </div>
            <div className="calendar-grid" aria-label="Upcoming calendar">
              {calendarDays.map((day) => (
                <article className={day.entries.length > 0 ? "calendar-day has-items" : "calendar-day"} key={day.dateKey}>
                  <div className="calendar-day-head">
                    <span>{day.date.toLocaleDateString(undefined, { weekday: "short" })}</span>
                    <strong>{day.date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}</strong>
                  </div>
                  <div className="calendar-day-list">
                    {day.entries.length > 0 ? (
                      day.entries.map((entry) => (
                        <div className={`calendar-entry ${entry.kind}`} key={`${entry.kind}-${entry.id}`}>
                          <span>{entry.status.replace("_", " ")}</span>
                          <p>{entry.title}</p>
                        </div>
                      ))
                    ) : (
                      <small>No planned item</small>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </section>}

          {activeView === "calendar" && <section className="panel band">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Queue</p>
                <h2>Approved and upcoming posts</h2>
              </div>
              <CalendarClock size={20} />
            </div>
            <div className="queue-list">
              {calendarItems.length > 0 ? (
                calendarItems.map((item) => (
                  <article className="queue-row" key={item.id}>
                    <div>
                      <strong>{item.hook || item.body.slice(0, 80)}</strong>
                      <span>{item.status}</span>
                    </div>
                    <p>{item.body}</p>
                    <small>
                      {item.published_at
                          ? `Published ${new Date(item.published_at).toLocaleString()}`
                        : item.scheduled_for
                          ? `Scheduled ${new Date(item.scheduled_for).toLocaleString()}`
                        : item.exported_at
                          ? `Exported ${new Date(item.exported_at).toLocaleString()}`
                          : `Updated ${new Date(item.updated_at).toLocaleString()}`}
                    </small>
                  </article>
                ))
              ) : (
                <p className="empty-results">Approved, scheduled, and exported drafts will appear here.</p>
              )}
            </div>
          </section>}

          {activeView === "strategy" && <section className="panel band strategy-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Strategy</p>
                <h2>Coverage, repetition, and next bets</h2>
              </div>
              <span className="platform-count">{strategyDashboard?.suggested_directions.length ?? 0} directions</span>
            </div>
            <div className="strategy-grid">
              <section className="strategy-block direction-block">
                <div className="panel-title">
                  <Sparkles size={17} />
                  <h2>Suggested directions</h2>
                </div>
                <div className="direction-list">
                  {(strategyDashboard?.suggested_directions ?? []).map((direction) => (
                    <article className="direction-card" key={direction.title}>
                      <div>
                        <strong>{direction.title}</strong>
                        <span>{Math.round(direction.confidence * 100)}% confidence</span>
                      </div>
                      <p>{direction.rationale}</p>
                      {direction.source_basis.length > 0 && <small>{direction.source_basis.join(", ")}</small>}
                    </article>
                  ))}
                  {(strategyDashboard?.suggested_directions.length ?? 0) === 0 && (
                    <p className="empty-results">Generate and publish content with metrics to unlock source-backed direction suggestions.</p>
                  )}
                </div>
              </section>

              <section className="strategy-block">
                <div className="panel-title">
                  <Library size={17} />
                  <h2>Pillar coverage</h2>
                </div>
                <div className="pillar-grid">
                  {(strategyDashboard?.pillar_coverage ?? []).map((pillar) => (
                    <article className="pillar-card" key={pillar.pillar}>
                      <span>{pillar.pillar}</span>
                      <strong>{pillar.artifact_count} artifacts</strong>
                      <small>
                        {pillar.source_count} source chunks / {Math.round(pillar.performance_score * 100)}% score
                      </small>
                      <p>{pillar.recommendation}</p>
                    </article>
                  ))}
                  {(strategyDashboard?.pillar_coverage.length ?? 0) === 0 && (
                    <p className="empty-results">Add content pillars and approved sources to see coverage.</p>
                  )}
                </div>
              </section>
            </div>

            <div className="strategy-grid secondary">
              <section className="strategy-block">
                <div className="panel-title">
                  <RefreshCcw size={17} />
                  <h2>Topic repetition</h2>
                </div>
                <div className="topic-cloud">
                  {(strategyDashboard?.topic_repetition ?? []).map((topic) => (
                    <span className="topic-chip" key={topic.topic}>
                      {topic.topic}
                      <strong>{topic.count}</strong>
                    </span>
                  ))}
                  {(strategyDashboard?.topic_repetition.length ?? 0) === 0 && (
                    <p className="empty-results">Published memory topics will appear here to prevent repetitive content.</p>
                  )}
                </div>
              </section>

              <section className="strategy-block">
                <div className="panel-title">
                  <FileCheck2 size={17} />
                  <h2>Performance breakdown</h2>
                </div>
                <div className="breakdown-sections">
                  <div>
                    <h3>By platform</h3>
                    <div className="breakdown-grid">
                      {(strategyDashboard?.performance_by_platform ?? []).map((breakdown) => (
                        <article className="breakdown-card" key={`platform-${breakdown.key}`}>
                          <span>{breakdown.label}</span>
                          <strong>{Math.round(breakdown.average_score * 100)}%</strong>
                          <small>
                            {breakdown.posts} posts / {breakdown.impressions} impressions / {breakdown.clicks} clicks
                          </small>
                        </article>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h3>By content type</h3>
                    <div className="breakdown-grid">
                      {(strategyDashboard?.performance_by_content_type ?? []).map((breakdown) => (
                        <article className="breakdown-card" key={`content-type-${breakdown.key}`}>
                          <span>{breakdown.label}</span>
                          <strong>{Math.round(breakdown.average_score * 100)}%</strong>
                          <small>
                            {breakdown.posts} posts / {breakdown.impressions} impressions / {breakdown.clicks} clicks
                          </small>
                        </article>
                      ))}
                    </div>
                  </div>
                  {((strategyDashboard?.performance_by_platform.length ?? 0) +
                    (strategyDashboard?.performance_by_content_type.length ?? 0) ===
                    0) && <p className="empty-results">Import or enter post metrics to compare platforms and formats.</p>}
                </div>
              </section>
            </div>
          </section>}

          {activeView === "strategy" && <section className="panel band analytics-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Analytics</p>
                <h2>Performance learning</h2>
              </div>
              <button className="icon-button" onClick={importAnalytics} disabled={busy} title="Import analytics">
                <RefreshCcw size={18} />
                <span>Import</span>
              </button>
            </div>
            <div className="analytics-grid">
              <div className="metric-tile">
                <span>Posts</span>
                <strong>{analyticsDashboard?.posts_analyzed ?? 0}</strong>
              </div>
              <div className="metric-tile">
                <span>Impressions</span>
                <strong>{analyticsDashboard?.total_impressions ?? 0}</strong>
              </div>
              <div className="metric-tile">
                <span>Reactions</span>
                <strong>{analyticsDashboard?.total_reactions ?? 0}</strong>
              </div>
              <div className="metric-tile">
                <span>Avg score</span>
                <strong>{Math.round((analyticsDashboard?.average_performance_score ?? 0) * 100)}%</strong>
              </div>
            </div>
            <div className="manual-metrics">
              <select value={metricsForm.memory_id} onChange={(event) => setMetricsForm({ ...metricsForm, memory_id: event.target.value })}>
                <option value="">Select memory</option>
                {memoryItems.map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.platform} / {item.content_type} / {item.id}
                  </option>
                ))}
              </select>
              {(["impressions", "reactions", "comments", "shares", "clicks"] as const).map((field) => (
                <input
                  key={field}
                  value={metricsForm[field]}
                  onChange={(event) => setMetricsForm({ ...metricsForm, [field]: event.target.value })}
                  placeholder={field}
                  inputMode="numeric"
                />
              ))}
              <button className="icon-button primary" onClick={saveManualMetrics} disabled={busy || !metricsForm.memory_id} title="Save metrics">
                <Save size={18} />
                <span>Save metrics</span>
              </button>
            </div>
            <div className="analytics-posts">
              {(analyticsDashboard?.top_posts ?? []).map((post) => (
                <article className="analytics-row" key={post.post_memory_id}>
                  <strong>{Math.round(post.performance_score * 100)}% score</strong>
                  <p>{post.excerpt}</p>
                  <span>
                    {post.metrics.impressions ?? 0} impressions / {post.metrics.clicks ?? 0} clicks
                  </span>
                </article>
              ))}
              {analyticsDashboard?.top_posts.length === 0 && <p className="empty-results">Published post metrics will appear here.</p>}
            </div>
          </section>}

          {activeView === "strategy" && <section className="panel band preference-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Learning</p>
                <h2>Preference suggestions</h2>
              </div>
              <button className="icon-button" onClick={generatePreferenceSuggestions} disabled={busy} title="Generate suggestions">
                <RefreshCcw size={18} />
                <span>Suggest</span>
              </button>
            </div>
            <div className="preference-list">
              {preferenceSuggestions.length > 0 ? (
                preferenceSuggestions.map((suggestion) => (
                  <article className="preference-row" key={suggestion.id}>
                    <div>
                      <strong>{suggestion.title}</strong>
                      <span>{suggestion.kind} / {suggestion.status} / {Math.round(suggestion.confidence * 100)}%</span>
                    </div>
                    <p>{suggestion.rationale}</p>
                    <small>{suggestion.evidence.join(", ")}</small>
                    <div className="preference-actions">
                      <button
                        className="icon-button primary"
                        onClick={() => decidePreferenceSuggestion(suggestion.id, "approve")}
                        disabled={busy || suggestion.status !== "pending"}
                        title="Approve suggestion"
                      >
                        <Check size={18} />
                        <span>Approve</span>
                      </button>
                      <button
                        className="icon-button"
                        onClick={() => decidePreferenceSuggestion(suggestion.id, "dismiss")}
                        disabled={busy || suggestion.status !== "pending"}
                        title="Dismiss suggestion"
                      >
                        <X size={18} />
                        <span>Dismiss</span>
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <p className="empty-results">Repeated edits and rejection patterns will appear here as suggestions.</p>
              )}
            </div>
          </section>}
        </section>
      </section>
    </main>
  );
}

function Field({ label, wide, required, children }: { label: string; wide?: boolean; required?: boolean; children: React.ReactNode }) {
  return (
    <label className={`field ${wide ? "wide" : ""}`}>
      <span>
        {label}
        {required && <b aria-label="required">*</b>}
      </span>
      {children}
    </label>
  );
}

function ErrorList({ errors }: { errors: string[] }) {
  const uniqueErrors = Array.from(new Set(errors.map((error) => error.trim()).filter(Boolean)));
  if (uniqueErrors.length === 0) return null;
  return (
    <div className="form-error" role="alert">
      <strong>Check these details</strong>
      <ul>
        {uniqueErrors.map((error) => (
          <li key={error}>{error}</li>
        ))}
      </ul>
    </div>
  );
}

function InsightList({ title, icon, items }: { title: string; icon: React.ReactNode; items: string[] }) {
  return (
    <section className="panel compact">
      <div className="panel-title">
        {icon}
        <h2>{title}</h2>
      </div>
      <ul className="plain-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

const rootElement = document.getElementById("root")!;
window.__quainyVouchRoot ??= createRoot(rootElement);
window.__quainyVouchRoot.render(<App />);
