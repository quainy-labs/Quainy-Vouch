import type { CalendarEvent, WorkspaceUser } from "./types";

export type AuthForm = {
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

export type SetupForm = {
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

export type SourceForm = {
  source_type: string;
  title: string;
  uri: string;
  raw_text: string;
  approval_status: string;
  freshness_days: string;
};

export type MetricsForm = {
  memory_id: string;
  impressions: string;
  reactions: string;
  comments: string;
  shares: string;
  clicks: string;
};

export type UserForm = {
  name: string;
  email: string;
  role: WorkspaceUser["role"];
};

export type CalendarEventForm = {
  title: string;
  event_type: CalendarEvent["event_type"];
  starts_at: string;
  ends_at: string;
  description: string;
  relevance_terms: string;
};

export type TrendSignalForm = {
  title: string;
  summary: string;
  source_name: string;
  source_url: string;
  observed_at: string;
  relevance_terms: string;
};

export type FormatChoice =
  | "linkedin_post"
  | "reddit_post"
  | "instagram_post";

export type WorkspaceView = "studio" | "library" | "calendar" | "sources" | "strategy" | "settings";
export type SetupSection = "company" | "voice" | "claims" | "linkedin" | "ai";
export type LibraryStatusFilter =
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
export type LibraryPlatformFilter = "all" | string;

export type ViewItem = {
  id: WorkspaceView;
  label: string;
  eyebrow: string;
  title: string;
  description: string;
  badge: string;
};
