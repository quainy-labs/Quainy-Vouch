export type StudioSelectionKind = "opportunity" | "brief" | "draft";
export type PersistedStudioSection = "overview" | "opportunities" | "brief" | "drafts" | "review";
export type PersistedWorkspaceView = "studio" | "library" | "calendar" | "sources" | "strategy" | "settings";

export type StudioSelection = {
  kind: StudioSelectionKind;
  id: string;
  draft_ids?: string[];
};

function selectionKey(organizationId: string) {
  return `quainy_vouch_studio_selection:${organizationId}`;
}

function sectionKey(organizationId: string) {
  return `quainy_vouch_studio_section:${organizationId}`;
}

function workspaceViewKey(organizationId: string) {
  return `quainy_vouch_workspace_view:${organizationId}`;
}

export function saveStudioSelection(organizationId: string, selection: StudioSelection) {
  localStorage.setItem(selectionKey(organizationId), JSON.stringify(selection));
}

export function loadStudioSelection(organizationId: string): StudioSelection | null {
  const raw = localStorage.getItem(selectionKey(organizationId));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<StudioSelection>;
    if (!parsed.id || !parsed.kind) return null;
    if (!["opportunity", "brief", "draft"].includes(parsed.kind)) return null;
    return {
      kind: parsed.kind,
      id: parsed.id,
      draft_ids: Array.isArray(parsed.draft_ids) ? parsed.draft_ids.filter((id): id is string => typeof id === "string") : undefined,
    };
  } catch {
    return null;
  }
}

export function clearStudioSelection(organizationId: string) {
  localStorage.removeItem(selectionKey(organizationId));
}

export function saveStudioSection(organizationId: string, section: PersistedStudioSection) {
  localStorage.setItem(sectionKey(organizationId), section);
}

export function loadStudioSection(organizationId: string): PersistedStudioSection | null {
  const section = localStorage.getItem(sectionKey(organizationId));
  if (!section) return null;
  return ["overview", "opportunities", "brief", "drafts", "review"].includes(section) ? (section as PersistedStudioSection) : null;
}

export function clearStudioSection(organizationId: string) {
  localStorage.removeItem(sectionKey(organizationId));
}

export function saveWorkspaceView(organizationId: string, view: PersistedWorkspaceView) {
  localStorage.setItem(workspaceViewKey(organizationId), view);
}

export function loadWorkspaceView(organizationId: string): PersistedWorkspaceView | null {
  const view = localStorage.getItem(workspaceViewKey(organizationId));
  if (!view) return null;
  return ["studio", "library", "calendar", "sources", "strategy", "settings"].includes(view) ? (view as PersistedWorkspaceView) : null;
}

export function clearWorkspaceView(organizationId: string) {
  localStorage.removeItem(workspaceViewKey(organizationId));
}
