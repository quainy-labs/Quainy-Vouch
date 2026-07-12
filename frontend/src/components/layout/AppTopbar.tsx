type AppTopbarProps = {
  organizationName: string;
  healthLabel: string;
  pillarCount: number;
  workspaceLabel: string;
  onSignOut: () => void;
};

export function AppTopbar({ organizationName, healthLabel, pillarCount, workspaceLabel, onSignOut }: AppTopbarProps) {
  return (
    <header className="topbar">
      <div className="topbar-identity">
        <span className="brand-mark" aria-hidden="true">
          QV
        </span>
        <div>
          <p className="eyebrow">Quainy Vouch</p>
          <h1>{organizationName}</h1>
        </div>
      </div>
      <div className="status-strip">
        <span className="status-metric">{healthLabel}</span>
        <span className="status-metric">{pillarCount} pillars</span>
        <span className="status-metric">{workspaceLabel}</span>
        <button className="text-button" onClick={onSignOut} type="button">
          Sign out
        </button>
      </div>
    </header>
  );
}
