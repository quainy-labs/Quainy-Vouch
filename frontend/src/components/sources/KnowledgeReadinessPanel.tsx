import type { KnowledgeReadiness } from "../../types";

type KnowledgeReadinessPanelProps = {
  readiness: KnowledgeReadiness;
  copy: Record<string, string>;
  priorityLabels: Record<string, string>;
  onAction: (action: string) => void | Promise<void>;
};

function actionLabel(action: string): string {
  if (action === "settings") return "Open settings";
  if (action === "refresh_sources") return "Review sources";
  return "Add sources";
}

function statusLabel(score: number): string {
  if (score >= 0.8) return "Strong";
  if (score >= 0.45) return "Developing";
  if (score > 0) return "Started";
  return "Missing";
}

export function KnowledgeReadinessPanel({ readiness, copy, priorityLabels, onAction }: KnowledgeReadinessPanelProps) {
  return (
    <div className={`readiness-panel ${readiness.status}`}>
      <div className="readiness-score">
        <span>Knowledge coverage</span>
        <strong>{readiness.status.replace("_", " ")}</strong>
        <p>{copy[readiness.status] ?? copy.building}</p>
      </div>
      <div className="readiness-signals">
        {readiness.signals.map((signal) => (
          <article className={`readiness-signal ${signal.status}`} key={signal.key}>
            <div>
              <span>{signal.label}</span>
              <strong>{statusLabel(signal.score)}</strong>
            </div>
            <div className="readiness-meter" aria-hidden="true">
              <span style={{ width: `${Math.round(signal.score * 100)}%` }} />
            </div>
            <p>{signal.detail}</p>
          </article>
        ))}
      </div>
      {readiness.recommendations.length > 0 && (
        <div className="readiness-recommendations">
          {readiness.recommendations.map((recommendation) => (
            <article key={`${recommendation.action}-${recommendation.title}`}>
              <span>{priorityLabels[recommendation.priority] ?? "Medium"} priority</span>
              <strong>{recommendation.title}</strong>
              <p>{recommendation.detail}</p>
              <button className="text-button" onClick={() => void onAction(recommendation.action)} type="button">
                {actionLabel(recommendation.action)}
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
