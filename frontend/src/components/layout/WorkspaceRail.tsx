import { FileText, Library, ShieldCheck } from "lucide-react";
import type { Source } from "../../types";

type WorkspaceRailProps = {
  approvedCount: number;
  disabledCount: number;
  archivedCount: number;
  sources: Source[];
  selectedSourceId: string | null;
  sourceOverflow: number;
  preferredPhrases: string[];
  onSelectSource: (sourceId: string) => void;
  onShowSources: () => void;
};

export function WorkspaceRail({
  approvedCount,
  disabledCount,
  archivedCount,
  sources,
  selectedSourceId,
  sourceOverflow,
  preferredPhrases,
  onSelectSource,
  onShowSources,
}: WorkspaceRailProps) {
  return (
    <aside className="rail">
      <section className="panel">
        <div className="panel-title">
          <Library size={18} />
          <h2>Sources</h2>
        </div>
        <div className="source-list-summary">
          <span>{approvedCount} approved</span>
          <span>{disabledCount} disabled</span>
          <span>{archivedCount} archived</span>
        </div>
        <div className="source-list">
          {sources.map((source) => (
            <button
              className={`source-row source-button ${selectedSourceId === source.id ? "selected" : ""}`}
              key={source.id}
              onClick={() => onSelectSource(source.id)}
            >
              <FileText size={16} />
              <div>
                <strong>{source.title}</strong>
                <span>{source.approval_status}</span>
              </div>
            </button>
          ))}
          {sourceOverflow > 0 && (
            <button className="source-overflow-note" onClick={onShowSources} type="button">
              View {sourceOverflow} more source{sourceOverflow === 1 ? "" : "s"} in Sources
            </button>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">
          <ShieldCheck size={18} />
          <h2>Voice</h2>
        </div>
        <div className="tag-wrap">
          {preferredPhrases.map((phrase) => (
            <span className="tag" key={phrase}>
              {phrase}
            </span>
          ))}
        </div>
      </section>
    </aside>
  );
}
