import { api } from "../../lib/api";
import { emptyCalendarEventForm, emptyTrendSignalForm, setupFromBootstrap, sortOpportunities, textToList } from "../../lib/forms";
import type { AnalyticsDashboard, CalendarEvent, Draft, Opportunity, PostMemory, PreferenceSuggestion, Profile, TrendSignal } from "../../types";
import type { WorkspaceControllerState } from "./useWorkspaceControllerState";

type CalendarStrategyActionsOptions = {
  canEditContent: boolean;
  canEditKnowledge: boolean;
  knowledgePermissionMessage: string;
  requirePermission: (allowed: boolean, message: string) => boolean;
  refreshProductSurfaces: (organizationId?: string) => Promise<void>;
};

export function createCalendarStrategyActions(state: WorkspaceControllerState, options: CalendarStrategyActionsOptions) {
  async function addCalendarEvent() {
    if (!state.bootstrap || !state.calendarEventForm.title.trim() || !state.calendarEventForm.starts_at) return;
    if (!options.requirePermission(options.canEditKnowledge, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api<CalendarEvent>(`/organizations/${state.bootstrap.organization.id}/calendar-events`, {
        method: "POST",
        body: JSON.stringify({
          title: state.calendarEventForm.title,
          event_type: state.calendarEventForm.event_type,
          starts_at: new Date(state.calendarEventForm.starts_at).toISOString(),
          ends_at: state.calendarEventForm.ends_at ? new Date(state.calendarEventForm.ends_at).toISOString() : null,
          description: state.calendarEventForm.description || null,
          relevance_terms: textToList(state.calendarEventForm.relevance_terms),
        }),
      });
      state.setCalendarEventForm(emptyCalendarEventForm);
      state.setCalendarEvents(await api<CalendarEvent[]>(`/organizations/${state.bootstrap.organization.id}/calendar-events`));
      state.setNotice("Calendar event added for trend relevance checks.");
    } finally {
      state.setBusy(false);
    }
  }

  async function addTrendSignal() {
    if (!state.bootstrap || !state.trendSignalForm.title.trim() || state.trendSignalForm.summary.trim().length < 10) return;
    if (!options.requirePermission(options.canEditKnowledge, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api<TrendSignal>(`/organizations/${state.bootstrap.organization.id}/trend-signals`, {
        method: "POST",
        body: JSON.stringify({
          title: state.trendSignalForm.title,
          summary: state.trendSignalForm.summary,
          source_name: state.trendSignalForm.source_name || "Manual trend research",
          source_url: state.trendSignalForm.source_url || null,
          observed_at: state.trendSignalForm.observed_at ? new Date(state.trendSignalForm.observed_at).toISOString() : null,
          relevance_terms: textToList(state.trendSignalForm.relevance_terms),
        }),
      });
      state.setTrendSignalForm(emptyTrendSignalForm);
      state.setTrendSignals(await api<TrendSignal[]>(`/organizations/${state.bootstrap.organization.id}/trend-signals`));
      state.setNotice("Trend signal added. Generate trend opportunities when company context is ready.");
    } finally {
      state.setBusy(false);
    }
  }

  async function generateTrendOpportunities() {
    if (!state.bootstrap) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      const result = await api<{ opportunities: Opportunity[] }>(
        `/organizations/${state.bootstrap.organization.id}/trend-opportunities/generate`,
        { method: "POST" },
      );
      const ranked = sortOpportunities(result.opportunities);
      state.setOpportunities(ranked);
      state.setVisibleOpportunityCount(12);
      state.setOpportunityMessage(
        result.opportunities.some((opportunity) => opportunity.status === "warned")
          ? "Trend opportunities generated with warnings for items missing company context."
          : "Trend opportunities generated from calendar and approved company context.",
      );
      state.setSelectedOpportunity(ranked[0] ?? null);
      state.setSelectedBrief(null);
      state.setDrafts([]);
      state.setSelectedDraft(null);
      await options.refreshProductSurfaces();
    } finally {
      state.setBusy(false);
    }
  }

  async function refreshCalendar() {
    if (!state.bootstrap) return;
    state.setCalendarItems(await api<Draft[]>(`/organizations/${state.bootstrap.organization.id}/calendar`));
  }

  async function refreshMemoryAndAnalytics() {
    if (!state.bootstrap) return;
    const [memory, analytics] = await Promise.all([
      api<PostMemory[]>(`/organizations/${state.bootstrap.organization.id}/memory`),
      api<AnalyticsDashboard>(`/organizations/${state.bootstrap.organization.id}/analytics`),
    ]);
    state.setMemoryItems(memory);
    state.setAnalyticsDashboard(analytics);
    if (!state.metricsForm.memory_id && memory.length > 0) {
      state.setMetricsForm((current) => ({ ...current, memory_id: memory[0].id }));
    }
  }

  async function importAnalytics() {
    if (!state.bootstrap) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api<PostMemory[]>(`/organizations/${state.bootstrap.organization.id}/analytics/import`, { method: "POST" });
      await refreshMemoryAndAnalytics();
      await options.refreshProductSurfaces();
      state.setNotice("Analytics imported for published LinkedIn memory.");
    } finally {
      state.setBusy(false);
    }
  }

  async function saveManualMetrics() {
    if (!state.metricsForm.memory_id) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api<PostMemory>(`/memory/${state.metricsForm.memory_id}/performance`, {
        method: "POST",
        body: JSON.stringify({
          impressions: Number(state.metricsForm.impressions) || 0,
          reactions: Number(state.metricsForm.reactions) || 0,
          comments: Number(state.metricsForm.comments) || 0,
          shares: Number(state.metricsForm.shares) || 0,
          clicks: Number(state.metricsForm.clicks) || 0,
          source: "manual",
        }),
      });
      state.setMetricsForm({ ...state.metricsForm, impressions: "", reactions: "", comments: "", shares: "", clicks: "" });
      await refreshMemoryAndAnalytics();
      await options.refreshProductSurfaces();
      state.setNotice("Manual performance metrics saved.");
    } finally {
      state.setBusy(false);
    }
  }

  async function generatePreferenceSuggestions() {
    if (!state.bootstrap) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      const suggestions = await api<PreferenceSuggestion[]>(
        `/organizations/${state.bootstrap.organization.id}/preference-suggestions/generate`,
        { method: "POST" },
      );
      state.setPreferenceSuggestions(suggestions);
      state.setNotice(suggestions.length ? "Preference suggestions generated from review signals." : "No repeated preference signal yet.");
    } finally {
      state.setBusy(false);
    }
  }

  async function decidePreferenceSuggestion(suggestionId: string, action: "approve" | "dismiss") {
    if (!state.bootstrap) return;
    if (!options.requirePermission(options.canEditContent, options.knowledgePermissionMessage)) return;
    state.setBusy(true);
    try {
      await api<PreferenceSuggestion>(`/preference-suggestions/${suggestionId}/${action}`, {
        method: "POST",
        body: JSON.stringify({ reason: action === "approve" ? "Approved from preference panel." : "Dismissed from preference panel." }),
      });
      state.setPreferenceSuggestions(await api<PreferenceSuggestion[]>(`/organizations/${state.bootstrap.organization.id}/preference-suggestions`));
      const profile = await api<Profile>(`/organizations/${state.bootstrap.organization.id}/profile`);
      const nextBootstrap = { ...state.bootstrap, profile };
      state.setBootstrap(nextBootstrap);
      state.setSetupForm(setupFromBootstrap(nextBootstrap));
      state.setNotice(action === "approve" ? "Preference suggestion applied to profile." : "Preference suggestion dismissed.");
    } finally {
      state.setBusy(false);
    }
  }

  return {
    addCalendarEvent,
    addTrendSignal,
    decidePreferenceSuggestion,
    generatePreferenceSuggestions,
    generateTrendOpportunities,
    importAnalytics,
    refreshCalendar,
    refreshMemoryAndAnalytics,
    saveManualMetrics,
  };
}
