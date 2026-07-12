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
      <div>
        <p className="eyebrow">Quainy Vouch</p>
        <h1>{organizationName}</h1>
      </div>
      <div className="status-strip">
        <span>{healthLabel}</span>
        <span>{pillarCount} pillars</span>
        <span>{workspaceLabel}</span>
        <button className="text-button" onClick={onSignOut} type="button">
          Sign out
        </button>
      </div>
    </header>
  );
}
