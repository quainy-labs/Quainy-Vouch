import { RefreshCcw } from "lucide-react";
import type { BackgroundJob } from "../../types";

type OperationsJobsPanelProps = {
  busy: boolean;
  canEditContent: boolean;
  permissionMessage: string;
  jobs: BackgroundJob[];
  failedJobCount: number;
  onRetryJob: (jobId: string) => void | Promise<void>;
};

export function OperationsJobsPanel({ busy, canEditContent, permissionMessage, jobs, failedJobCount, onRetryJob }: OperationsJobsPanelProps) {
  if (jobs.length === 0) return null;

  return (
    <section className="panel band operations-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Recent background jobs</h2>
        </div>
        <span className={failedJobCount > 0 ? "review-status warning" : "review-status"}>
          {failedJobCount > 0 ? `${failedJobCount} failed` : "All clear"}
        </span>
      </div>
      <div className="team-list">
        {jobs.map((job) => (
          <article className="team-row" key={job.id}>
            <div>
              <strong>{jobTitle(job.kind)}</strong>
              <span>{jobTarget(job)}</span>
              <span>
                {job.status} / attempt {job.attempt_count} / {new Date(job.updated_at).toLocaleString()}
                {jobResultSummary(job)}
                {job.error_message ? ` / ${job.error_message}` : ""}
              </span>
            </div>
            {job.status === "failed" ? (
              <button
                className="icon-button"
                onClick={() => void onRetryJob(job.id)}
                disabled={busy || !canEditContent || job.attempt_count >= job.max_attempts}
                title={canEditContent ? "Retry job" : permissionMessage}
                type="button"
              >
                <RefreshCcw size={16} />
                <span>Retry</span>
              </button>
            ) : (
              <span className={`status-pill ${job.status}`}>{job.status}</span>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function jobTitle(kind: string): string {
  const labels: Record<string, string> = {
    source_ingest: "Source ingest",
    source_refresh: "Source refresh",
    opportunity_generation: "Opportunity generation",
    trend_opportunity_generation: "Trend opportunity generation",
    draft_generation: "Draft generation",
    draft_regeneration: "Draft regeneration",
    linkedin_publish: "LinkedIn publish",
    analytics_import: "Analytics import",
    performance_capture: "Performance capture",
    preference_suggestion_generation: "Preference suggestions",
  };
  return labels[kind] ?? titleCase(kind.replace(/_/g, " "));
}

function jobTarget(job: BackgroundJob): string {
  const platform = readText(job.payload.platform);
  const contentType = readText(job.payload.content_type);
  const format = [platform, contentType].filter(Boolean).join(" / ");
  const briefId = readText(job.payload.brief_id);
  const sourceId = readText(job.payload.source_id);
  const draftId = readText(job.payload.draft_id) || (job.entity_type === "draft" ? job.entity_id : "");

  if (job.kind === "draft_generation") {
    return [`Brief ${shortId(briefId || job.entity_id)}`, format].filter(Boolean).join(" -> ");
  }
  if (job.kind === "draft_regeneration") {
    return `Draft ${shortId(draftId || job.entity_id)}`;
  }
  if (job.kind === "linkedin_publish") {
    return `Draft ${shortId(draftId || job.entity_id)}`;
  }
  if (job.kind === "source_ingest" || job.kind === "source_refresh") {
    return `Source ${shortId(sourceId || job.entity_id)}${readText(job.payload.source_type) ? ` / ${readText(job.payload.source_type)}` : ""}`;
  }
  if (job.entity_type && job.entity_id) {
    return `${titleCase(job.entity_type)} ${shortId(job.entity_id)}`;
  }
  return `Job ${shortId(job.id)}`;
}

function jobResultSummary(job: BackgroundJob): string {
  const parts: string[] = [];
  const count = typeof job.result.count === "number" ? job.result.count : undefined;
  const ids = Array.isArray(job.result.ids) ? job.result.ids.map((value) => String(value)).filter(Boolean) : [];
  const chunkCount = typeof job.result.chunk_count === "number" ? job.result.chunk_count : undefined;

  if (typeof count === "number") parts.push(`${count} item${count === 1 ? "" : "s"}`);
  if (typeof chunkCount === "number") parts.push(`${chunkCount} chunk${chunkCount === 1 ? "" : "s"}`);
  if (ids.length > 0) parts.push(`IDs ${ids.slice(0, 3).map(shortId).join(", ")}${ids.length > 3 ? ` +${ids.length - 3}` : ""}`);

  return parts.length > 0 ? ` / ${parts.join(" / ")}` : "";
}

function readText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function shortId(value: string): string {
  if (!value) return "unknown";
  if (value.length <= 24) return value;
  const [prefix, suffix] = value.split("_");
  if (suffix) return `${prefix}_${suffix.slice(0, 12)}`;
  return value.slice(0, 12);
}

function titleCase(value: string): string {
  return value.replace(/\b\w/g, (character) => character.toUpperCase());
}
