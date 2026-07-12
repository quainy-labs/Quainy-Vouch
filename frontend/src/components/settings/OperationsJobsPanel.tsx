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
              <strong>{job.kind.replace(/_/g, " ")}</strong>
              <span>
                {job.status} / attempt {job.attempt_count}
                {typeof job.result.count === "number" ? ` / ${job.result.count} item${job.result.count === 1 ? "" : "s"}` : ""}
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
              <span className={`status-pill ${job.status}`}>{new Date(job.updated_at).toLocaleString()}</span>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
