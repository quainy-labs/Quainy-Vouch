import { FileCheck2, Library } from "lucide-react";
import type { ContentArtifact, LibraryPlatformFilter, LibraryStatusFilter } from "../../types";

type LibraryMetric = {
  label: string;
  value: string | number;
  detail: string;
};

type LibraryStatusOption = {
  id: LibraryStatusFilter;
  label: string;
};

type LibraryViewProps = {
  metrics: LibraryMetric[];
  statusOptions: LibraryStatusOption[];
  statusFilter: LibraryStatusFilter;
  platformFilter: LibraryPlatformFilter;
  availablePlatforms: string[];
  artifacts: ContentArtifact[];
  hasVisibleArtifacts: boolean;
  onStatusFilterChange: (status: LibraryStatusFilter) => void;
  onPlatformFilterChange: (platform: LibraryPlatformFilter) => void;
  onOpenStudio: () => void;
  onOpenArtifact: (artifact: ContentArtifact) => void | Promise<void>;
};

export function LibraryView({
  metrics,
  statusOptions,
  statusFilter,
  platformFilter,
  availablePlatforms,
  artifacts,
  hasVisibleArtifacts,
  onStatusFilterChange,
  onPlatformFilterChange,
  onOpenStudio,
  onOpenArtifact,
}: LibraryViewProps) {
  const openableKinds = new Set(["opportunity", "brief", "draft"]);

  return (
    <section className="panel band library-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Library</p>
          <h2>Content memory and pipeline</h2>
        </div>
        <button className="icon-button" onClick={onOpenStudio} title="Open studio">
          <FileCheck2 size={18} />
          <span>Open studio</span>
        </button>
      </div>
      <div className="library-value-grid">
        {metrics.map((metric) => (
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
              className={statusFilter === option.id ? "active" : ""}
              key={option.id}
              onClick={() => onStatusFilterChange(option.id)}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
        <select value={platformFilter} onChange={(event) => onPlatformFilterChange(event.target.value)}>
          <option value="all">All platforms</option>
          {availablePlatforms.map((platform) => (
            <option value={platform} key={platform}>
              {platform}
            </option>
          ))}
        </select>
      </div>
      <div className="artifact-grid">
        {artifacts.map((artifact) => {
          const canOpenInStudio = openableKinds.has(artifact.kind) && !(artifact.kind === "opportunity" && artifact.status === "dismissed");
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
              {canOpenInStudio && (
                <button className="text-action" onClick={() => onOpenArtifact(artifact)} type="button">
                  Open in studio
                </button>
              )}
            </article>
          );
        })}
        {!hasVisibleArtifacts && (
          <div className="empty-opportunities library-empty">
            <Library size={22} />
            <p>No content matches these filters yet. Generate recommendations, create a brief, or clear the filters to see available work.</p>
          </div>
        )}
      </div>
    </section>
  );
}
