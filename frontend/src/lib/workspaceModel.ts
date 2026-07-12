import type {
  AnalyticsDashboard,
  BackgroundJob,
  Bootstrap,
  ContentArtifact,
  Draft,
  KnowledgeReadiness,
  LibraryPlatformFilter,
  LibraryStatusFilter,
  LinkedInIntegration,
  Opportunity,
  PostMemory,
  ReviewerPackage,
  ViewItem,
  WorkspaceUser,
  WorkspaceView,
} from "../types";
import { contentTypeDisplayName, platformDisplayName, sortOpportunities, summarizeNames } from "./forms";

type BuildWorkspaceModelInput = {
  bootstrap: Bootstrap;
  knowledgeReadiness: KnowledgeReadiness | null;
  currentUser: WorkspaceUser | null;
  reviewPackage: ReviewerPackage | null;
  selectedDraft: Draft | null;
  busy: boolean;
  linkedinIntegration: LinkedInIntegration | null;
  jobs: BackgroundJob[];
  drafts: Draft[];
  memoryItems: PostMemory[];
  calendarItems: Draft[];
  analyticsDashboard: AnalyticsDashboard | null;
  users: WorkspaceUser[];
  activeView: WorkspaceView;
  contentArtifacts: ContentArtifact[];
  libraryStatusFilter: LibraryStatusFilter;
  libraryPlatformFilter: LibraryPlatformFilter;
  opportunities: Opportunity[];
  visibleOpportunityCount: number;
};

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

export function buildWorkspaceModel({
  bootstrap,
  knowledgeReadiness,
  currentUser,
  reviewPackage,
  selectedDraft,
  busy,
  linkedinIntegration,
  jobs,
  drafts,
  memoryItems,
  calendarItems,
  analyticsDashboard,
  users,
  activeView,
  contentArtifacts,
  libraryStatusFilter,
  libraryPlatformFilter,
  opportunities,
  visibleOpportunityCount,
}: BuildWorkspaceModelInput) {
  const approvedSourceCount = bootstrap.sources.filter((source) => source.approval_status === "approved").length;
  const healthLabel = `${approvedSourceCount} approved source${approvedSourceCount === 1 ? "" : "s"}`;

  const currentRole = currentUser?.role ?? "viewer";
  const canManageWorkspace = currentRole === "owner";
  const canEditKnowledge = currentRole === "owner" || currentRole === "editor";
  const canEditContent = canEditKnowledge;
  const canReviewContent = currentRole === "owner" || currentRole === "reviewer";
  const workspacePermissionMessage = "Only workspace owners can change organization settings, team roles, approval policy, and publishing settings.";
  const knowledgePermissionMessage = "Only owners and editors can change sources, calendar context, trends, briefs, and drafts.";
  const reviewPermissionMessage = "Only owners and reviewers can approve or reject drafts.";

  const approvalBlocked = reviewPackage?.suggested_action.toLowerCase().includes("unsupported claims") ?? false;
  const approvalProgress = selectedDraft?.approval_metadata ?? {};
  const canApproveDraft = !busy && !approvalBlocked && canReviewContent;
  const canExportDraft = Boolean(canEditContent && selectedDraft && ["approved", "scheduled", "exported", "published"].includes(selectedDraft.status));
  const canScheduleDraft = Boolean(canEditContent && selectedDraft && ["approved", "scheduled", "exported"].includes(selectedDraft.status));
  const canAttemptLinkedinPublish =
    canEditContent &&
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

  const recentJobs = jobs.slice(0, 5);
  const failedJobCount = jobs.filter((job) => job.status === "failed").length;

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
      badge: `${bootstrap.sources.length} sources`,
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
  const approvedSources = bootstrap.sources.filter((source) => source.approval_status === "approved");
  const disabledSources = bootstrap.sources.filter((source) => source.approval_status === "disabled");
  const archivedSources = bootstrap.sources.filter((source) => source.approval_status === "archived");
  const activeSourceSummary = summarizeNames(approvedSources.map((source) => source.title), 3);
  const availableLibraryPlatforms = Array.from(
    new Set(contentArtifacts.map((artifact) => artifact.platform).filter((platform): platform is string => Boolean(platform))),
  );

  const rankedOpportunities = sortOpportunities(opportunities);
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

  return {
    healthLabel,
    currentRole,
    canManageWorkspace,
    canEditKnowledge,
    canEditContent,
    canReviewContent,
    workspacePermissionMessage,
    knowledgePermissionMessage,
    reviewPermissionMessage,
    approvalBlocked,
    approvalProgress,
    canApproveDraft,
    canExportDraft,
    canScheduleDraft,
    canAttemptLinkedinPublish,
    publishCapabilityText,
    recentJobs,
    failedJobCount,
    viewItems,
    currentView,
    approvedSources,
    disabledSources,
    archivedSources,
    availableLibraryPlatforms,
    statusOptions,
    rankedOpportunities,
    visibleOpportunities,
    hiddenOpportunityCount,
    visibleContentArtifacts,
    hasVisibleLibraryArtifacts,
    libraryMetrics,
  };
}
