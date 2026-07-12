import { CalendarClock, Plus, Sparkles } from "lucide-react";
import type { CalendarEvent, CalendarEventForm, Draft, TrendSignal, TrendSignalForm } from "../../types";

type CalendarEntry = {
  id: string;
  kind: string;
  title: string;
  status: string;
  date: string;
};

type CalendarViewProps = {
  busy: boolean;
  canEditContent: boolean;
  canEditKnowledge: boolean;
  permissionMessage: string;
  calendarItems: Draft[];
  calendarEvents: CalendarEvent[];
  trendSignals: TrendSignal[];
  calendarEventForm: CalendarEventForm;
  trendSignalForm: TrendSignalForm;
  onCalendarEventFormChange: (form: CalendarEventForm) => void;
  onTrendSignalFormChange: (form: TrendSignalForm) => void;
  onAddCalendarEvent: () => void | Promise<void>;
  onAddTrendSignal: () => void | Promise<void>;
  onGenerateTrendOpportunities: () => void | Promise<void>;
};

function buildCalendarEntries(calendarItems: Draft[], calendarEvents: CalendarEvent[]): CalendarEntry[] {
  return [
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
}

function queueTimestamp(item: Draft): string {
  if (item.published_at) return `Published ${new Date(item.published_at).toLocaleString()}`;
  if (item.scheduled_for) return `Scheduled ${new Date(item.scheduled_for).toLocaleString()}`;
  if (item.exported_at) return `Exported ${new Date(item.exported_at).toLocaleString()}`;
  return `Updated ${new Date(item.updated_at).toLocaleString()}`;
}

export function CalendarView({
  busy,
  canEditContent,
  canEditKnowledge,
  permissionMessage,
  calendarItems,
  calendarEvents,
  trendSignals,
  calendarEventForm,
  trendSignalForm,
  onCalendarEventFormChange,
  onTrendSignalFormChange,
  onAddCalendarEvent,
  onAddTrendSignal,
  onGenerateTrendOpportunities,
}: CalendarViewProps) {
  const calendarEntries = buildCalendarEntries(calendarItems, calendarEvents);
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

  return (
    <>
      <section className="panel band trend-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Calendar And Trends</p>
            <h2>Context-aware market moments</h2>
          </div>
          <button
            className="icon-button primary"
            onClick={() => void onGenerateTrendOpportunities()}
            disabled={busy || !canEditContent || trendSignals.length === 0}
            title={canEditContent ? "Generate trend opportunities" : permissionMessage}
          >
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
                  onChange={(event) => onCalendarEventFormChange({ ...calendarEventForm, title: event.target.value })}
                />
              </label>
              <label className="micro-field">
                <span>Type</span>
                <select
                  value={calendarEventForm.event_type}
                  onChange={(event) =>
                    onCalendarEventFormChange({ ...calendarEventForm, event_type: event.target.value as CalendarEvent["event_type"] })
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
                  onChange={(event) => onCalendarEventFormChange({ ...calendarEventForm, starts_at: event.target.value })}
                />
              </label>
              <label className="micro-field">
                <span>Ends</span>
                <input
                  type="datetime-local"
                  value={calendarEventForm.ends_at}
                  onChange={(event) => onCalendarEventFormChange({ ...calendarEventForm, ends_at: event.target.value })}
                />
              </label>
              <label className="micro-field wide">
                <span>Description</span>
                <textarea
                  className="small-textarea"
                  value={calendarEventForm.description}
                  onChange={(event) => onCalendarEventFormChange({ ...calendarEventForm, description: event.target.value })}
                />
              </label>
              <label className="micro-field wide">
                <span>Relevance terms</span>
                <textarea
                  className="small-textarea"
                  value={calendarEventForm.relevance_terms}
                  onChange={(event) => onCalendarEventFormChange({ ...calendarEventForm, relevance_terms: event.target.value })}
                />
              </label>
              <button
                className="icon-button"
                onClick={() => void onAddCalendarEvent()}
                disabled={busy || !canEditKnowledge || !calendarEventForm.title.trim() || !calendarEventForm.starts_at}
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
                    <span>
                      {eventItem.event_type} / {new Date(eventItem.starts_at).toLocaleDateString()}
                    </span>
                  </div>
                  {eventItem.description && <p>{eventItem.description}</p>}
                </article>
              ))}
              {calendarEvents.length === 0 && (
                <p className="empty-results">
                  Company launches, campaigns, holidays, and industry events help the relevance gate decide what is timely.
                </p>
              )}
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
                  onChange={(event) => onTrendSignalFormChange({ ...trendSignalForm, title: event.target.value })}
                />
              </label>
              <label className="micro-field">
                <span>Source</span>
                <input
                  value={trendSignalForm.source_name}
                  onChange={(event) => onTrendSignalFormChange({ ...trendSignalForm, source_name: event.target.value })}
                />
              </label>
              <label className="micro-field">
                <span>Source URL</span>
                <input
                  value={trendSignalForm.source_url}
                  onChange={(event) => onTrendSignalFormChange({ ...trendSignalForm, source_url: event.target.value })}
                />
              </label>
              <label className="micro-field">
                <span>Observed</span>
                <input
                  type="datetime-local"
                  value={trendSignalForm.observed_at}
                  onChange={(event) => onTrendSignalFormChange({ ...trendSignalForm, observed_at: event.target.value })}
                />
              </label>
              <label className="micro-field wide">
                <span>Summary</span>
                <textarea
                  className="small-textarea"
                  value={trendSignalForm.summary}
                  onChange={(event) => onTrendSignalFormChange({ ...trendSignalForm, summary: event.target.value })}
                />
              </label>
              <label className="micro-field wide">
                <span>Relevance terms</span>
                <textarea
                  className="small-textarea"
                  value={trendSignalForm.relevance_terms}
                  onChange={(event) => onTrendSignalFormChange({ ...trendSignalForm, relevance_terms: event.target.value })}
                />
              </label>
              <button
                className="icon-button"
                onClick={() => void onAddTrendSignal()}
                disabled={busy || !canEditKnowledge || !trendSignalForm.title.trim() || trendSignalForm.summary.trim().length < 10}
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
                    <span>
                      {trend.source_name} / {new Date(trend.observed_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p>{trend.summary}</p>
                </article>
              ))}
              {trendSignals.length === 0 && (
                <p className="empty-results">
                  Trend research is filtered against approved company sources before it can become a usable opportunity.
                </p>
              )}
            </div>
          </section>
        </div>
      </section>

      <section className="panel band calendar-board-panel">
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
      </section>

      <section className="panel band">
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
                <small>{queueTimestamp(item)}</small>
              </article>
            ))
          ) : (
            <p className="empty-results">Approved, scheduled, and exported drafts will appear here.</p>
          )}
        </div>
      </section>
    </>
  );
}
