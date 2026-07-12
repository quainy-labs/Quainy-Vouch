import type { ViewItem, WorkspaceView } from "../../types";

type WorkspaceNavProps = {
  activeView: WorkspaceView;
  items: ViewItem[];
  onSelectView: (view: WorkspaceView) => void;
};

export function WorkspaceNav({ activeView, items, onSelectView }: WorkspaceNavProps) {
  return (
    <nav className="view-nav" aria-label="Workspace views">
      {items.map((item, index) => (
        <button className={activeView === item.id ? "active" : ""} key={item.id} onClick={() => onSelectView(item.id)} title={item.title}>
          <span>{index + 1}</span>
          <strong>{item.label}</strong>
          <small>{item.badge}</small>
        </button>
      ))}
    </nav>
  );
}
