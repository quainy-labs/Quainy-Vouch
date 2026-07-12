import { CalendarClock, FileCheck2, Library, Settings, ShieldCheck, Sparkles } from "lucide-react";
import type { ViewItem, WorkspaceView } from "../../types";

type WorkspaceNavProps = {
  activeView: WorkspaceView;
  items: ViewItem[];
  onSelectView: (view: WorkspaceView) => void;
};

const viewIcons = {
  studio: Sparkles,
  library: Library,
  calendar: CalendarClock,
  sources: FileCheck2,
  strategy: ShieldCheck,
  settings: Settings,
};

export function WorkspaceNav({ activeView, items, onSelectView }: WorkspaceNavProps) {
  return (
    <nav className="view-nav" aria-label="Workspace views">
      {items.map((item) => {
        const Icon = viewIcons[item.id];

        return (
          <button
            className={activeView === item.id ? "active" : ""}
            key={item.id}
            onClick={() => onSelectView(item.id)}
            title={item.title}
            type="button"
          >
            <span aria-hidden="true">
              <Icon size={17} strokeWidth={2.1} />
            </span>
            <strong>{item.label}</strong>
            <small>{item.badge}</small>
          </button>
        );
      })}
    </nav>
  );
}
