export type Account = {
  id: string;
  name: string;
  email: string;
};

export type Organization = {
  id: string;
  name: string;
  website_url?: string;
  industry?: string;
  description?: string;
  audience_summary?: string;
  default_timezone?: string;
};

export type Profile = {
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

export type Source = {
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

export type AuditLog = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type SourceDetail = {
  source: Source;
  raw_text: string;
  chunk_count: number;
  audit_logs: AuditLog[];
};

export type KnowledgeReadinessSignal = {
  key: string;
  label: string;
  score: number;
  status: string;
  detail: string;
};

export type KnowledgeReadinessRecommendation = {
  title: string;
  detail: string;
  action: string;
  priority: string;
};

export type KnowledgeReadiness = {
  organization_id: string;
  overall_score: number;
  status: "blocked" | "building" | "ready" | "strong";
  profile_completeness: number;
  approved_source_count: number;
  stale_source_count: number;
  covered_pillar_count: number;
  total_pillar_count: number;
  retrievable_chunk_count: number;
  signals: KnowledgeReadinessSignal[];
  recommendations: KnowledgeReadinessRecommendation[];
  generated_at: string;
};

export type Opportunity = {
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

export type ContentBrief = {
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

export type Claim = {
  text: string;
  support_status: string;
  supporting_chunk_ids: string[];
  risk_reason?: string;
};

export type ApprovalDecision = {
  id: string;
  draft_id: string;
  decision: string;
  reason?: string;
  created_at: string;
};

export type Draft = {
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

export type LinkedInIntegration = {
  organization_id: string;
  selected_page_urn?: string;
  selected_page_name?: string;
  oauth_status: string;
  permissions: string[];
  publishing_enabled: boolean;
  updated_at: string;
};

export type PublishResult = {
  provider: string;
  status: string;
  draft_id: string;
  page_urn: string;
  page_name?: string;
  provider_post_id?: string;
  published_url?: string;
  failure_reason?: string;
};

export type PostMemory = {
  id: string;
  platform: string;
  content_type: string;
  final_body: string;
  source_draft_id: string;
  published_at?: string;
  performance_snapshot: Record<string, unknown>;
};

export type AnalyticsPostSummary = {
  post_memory_id: string;
  source_draft_id: string;
  platform: string;
  content_type: string;
  excerpt: string;
  performance_score: number;
  metrics: Record<string, number>;
};

export type AnalyticsDashboard = {
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

export type ContentArtifact = {
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

export type BackgroundJob = {
  id: string;
  organization_id: string;
  actor_id: string;
  kind: string;
  status: "queued" | "running" | "succeeded" | "failed";
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  error_message?: string | null;
  attempt_count: number;
  max_attempts: number;
  queued_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at: string;
};

export type PillarCoverage = {
  pillar: string;
  source_count: number;
  artifact_count: number;
  performance_score: number;
  recommendation: string;
};

export type TopicRepetition = {
  topic: string;
  count: number;
  last_seen?: string | null;
};

export type PerformanceBreakdown = {
  key: string;
  label: string;
  posts: number;
  average_score: number;
  impressions: number;
  reactions: number;
  clicks: number;
};

export type StrategyDirection = {
  title: string;
  rationale: string;
  source_basis: string[];
  confidence: number;
};

export type StrategyDashboard = {
  organization_id: string;
  pillar_coverage: PillarCoverage[];
  topic_repetition: TopicRepetition[];
  performance_by_platform: PerformanceBreakdown[];
  performance_by_content_type: PerformanceBreakdown[];
  suggested_directions: StrategyDirection[];
};

export type WorkspaceUser = {
  id: string;
  organization_id: string;
  name: string;
  email?: string;
  role: "owner" | "editor" | "reviewer" | "viewer";
};

export type OnboardingState = {
  organization_id: string;
  account_id: string;
  completed_steps: string[];
  profile_skipped: boolean;
  completion_percent: number;
  updated_at: string;
};

export type ApprovalPolicy = {
  organization_id: string;
  required_reviewer_count: number;
  require_approval_before_export: boolean;
  require_approval_before_publish: boolean;
  allow_risk_override: boolean;
  updated_at: string;
};

export type ApprovalPolicyForm = {
  required_reviewer_count: string;
  require_approval_before_export: boolean;
  require_approval_before_publish: boolean;
  allow_risk_override: boolean;
};

export type AIProviderKind = "deterministic" | "openai" | "openai_compatible" | "local";
export type AIProviderRuntime = "none" | "ollama" | "vllm" | "lm_studio" | "custom";

export type AIProviderSettings = {
  organization_id: string;
  generation_provider: AIProviderKind;
  generation_model: string;
  generation_base_url?: string | null;
  generation_api_key_env_var?: string | null;
  generation_api_key_configured: boolean;
  embedding_provider: AIProviderKind;
  embedding_model: string;
  embedding_base_url?: string | null;
  embedding_api_key_env_var?: string | null;
  embedding_api_key_configured: boolean;
  local_runtime: AIProviderRuntime;
  enabled: boolean;
  updated_at: string;
  updated_by?: string | null;
};

export type AIProviderConnectionTest = {
  organization_id: string;
  provider: string;
  model: string;
  status: "succeeded" | "failed";
  message: string;
  checked_at: string;
};

export type AIProviderSettingsForm = {
  generation_provider: AIProviderKind;
  generation_model: string;
  generation_base_url: string;
  generation_api_key_env_var: string;
  embedding_provider: AIProviderKind;
  embedding_model: string;
  embedding_base_url: string;
  embedding_api_key_env_var: string;
  local_runtime: AIProviderRuntime;
  enabled: boolean;
};

export type PreferenceSuggestion = {
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

export type CalendarEvent = {
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

export type TrendSignal = {
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

export type SourceChunk = {
  id: string;
  source_id: string;
  chunk_text: string;
  chunk_index: number;
};

export type ReviewerPackage = {
  draft: Draft;
  opportunity: Opportunity;
  sources: Source[];
  source_chunks: SourceChunk[];
  decision_history: ApprovalDecision[];
  suggested_action: string;
};

export type Bootstrap = {
  organization: Organization;
  profile: Profile;
  sources: Source[];
  opportunities: Opportunity[];
};

export type CurrentWorkspace = {
  account: Account;
  organization: Organization;
  user: WorkspaceUser;
  profile: Profile;
  sources: Source[];
  onboarding: OnboardingState;
};

export type AuthResponse = {
  token: string;
  workspace: CurrentWorkspace;
};

export type {
  AuthForm,
  CalendarEventForm,
  FormatChoice,
  LibraryPlatformFilter,
  LibraryStatusFilter,
  MetricsForm,
  SetupForm,
  SetupSection,
  SourceForm,
  TrendSignalForm,
  UserForm,
  ViewItem,
  WorkspaceView,
} from "./formTypes";
