import { Check, FileCheck2, Library, RefreshCcw, Save, Sparkles, X } from "lucide-react";
import type { AnalyticsDashboard, MetricsForm, PostMemory, PreferenceSuggestion, StrategyDashboard } from "../../types";

type StrategyViewProps = {
  busy: boolean;
  canEditContent: boolean;
  permissionMessage: string;
  strategyDashboard: StrategyDashboard | null;
  analyticsDashboard: AnalyticsDashboard | null;
  memoryItems: PostMemory[];
  metricsForm: MetricsForm;
  preferenceSuggestions: PreferenceSuggestion[];
  onMetricsFormChange: (form: MetricsForm) => void;
  onImportAnalytics: () => void | Promise<void>;
  onSaveManualMetrics: () => void | Promise<void>;
  onGeneratePreferenceSuggestions: () => void | Promise<void>;
  onDecidePreferenceSuggestion: (suggestionId: string, action: "approve" | "dismiss") => void | Promise<void>;
};

const metricFields: Array<keyof Omit<MetricsForm, "memory_id">> = ["impressions", "reactions", "comments", "shares", "clicks"];

export function StrategyView({
  busy,
  canEditContent,
  permissionMessage,
  strategyDashboard,
  analyticsDashboard,
  memoryItems,
  metricsForm,
  preferenceSuggestions,
  onMetricsFormChange,
  onImportAnalytics,
  onSaveManualMetrics,
  onGeneratePreferenceSuggestions,
  onDecidePreferenceSuggestion,
}: StrategyViewProps) {
  const hasPerformanceBreakdown =
    (strategyDashboard?.performance_by_platform.length ?? 0) + (strategyDashboard?.performance_by_content_type.length ?? 0) > 0;

  return (
    <>
      <section className="panel band strategy-panel">
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
              {!hasPerformanceBreakdown && <p className="empty-results">Import or enter post metrics to compare platforms and formats.</p>}
            </div>
          </section>
        </div>
      </section>

      <section className="panel band analytics-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Analytics</p>
            <h2>Performance learning</h2>
          </div>
          <button
            className="icon-button"
            onClick={() => void onImportAnalytics()}
            disabled={busy || !canEditContent}
            title={canEditContent ? "Import analytics" : permissionMessage}
          >
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
          <select value={metricsForm.memory_id} onChange={(event) => onMetricsFormChange({ ...metricsForm, memory_id: event.target.value })}>
            <option value="">Select memory</option>
            {memoryItems.map((item) => (
              <option value={item.id} key={item.id}>
                {item.platform} / {item.content_type} / {item.id}
              </option>
            ))}
          </select>
          {metricFields.map((field) => (
            <input
              key={field}
              value={metricsForm[field]}
              onChange={(event) => onMetricsFormChange({ ...metricsForm, [field]: event.target.value })}
              placeholder={field}
              inputMode="numeric"
            />
          ))}
          <button
            className="icon-button primary"
            onClick={() => void onSaveManualMetrics()}
            disabled={busy || !canEditContent || !metricsForm.memory_id}
            title={canEditContent ? "Save metrics" : permissionMessage}
          >
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
      </section>

      <section className="panel band preference-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Learning</p>
            <h2>Preference suggestions</h2>
          </div>
          <button
            className="icon-button"
            onClick={() => void onGeneratePreferenceSuggestions()}
            disabled={busy || !canEditContent}
            title={canEditContent ? "Generate suggestions" : permissionMessage}
          >
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
                  <span>
                    {suggestion.kind} / {suggestion.status} / {Math.round(suggestion.confidence * 100)}%
                  </span>
                </div>
                <p>{suggestion.rationale}</p>
                <small>{suggestion.evidence.join(", ")}</small>
                <div className="preference-actions">
                  <button
                    className="icon-button primary"
                    onClick={() => void onDecidePreferenceSuggestion(suggestion.id, "approve")}
                    disabled={busy || !canEditContent || suggestion.status !== "pending"}
                    title="Approve suggestion"
                  >
                    <Check size={18} />
                    <span>Approve</span>
                  </button>
                  <button
                    className="icon-button"
                    onClick={() => void onDecidePreferenceSuggestion(suggestion.id, "dismiss")}
                    disabled={busy || !canEditContent || suggestion.status !== "pending"}
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
      </section>
    </>
  );
}
