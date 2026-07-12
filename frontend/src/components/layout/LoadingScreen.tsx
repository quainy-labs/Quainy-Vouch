import { RefreshCcw } from "lucide-react";

type LoadingScreenProps = {
  error: string;
  onRetry: () => void | Promise<void>;
};

export function LoadingScreen({ error, onRetry }: LoadingScreenProps) {
  return (
    <main className="loading">
      <section className="connection-card">
        <p className="eyebrow">Quainy Vouch</p>
        <h1>{error ? "Workspace service is unavailable" : "Loading workspace"}</h1>
        <p>{error || "Preparing your workspace. If this takes more than a moment, check that the app services are running."}</p>
        {error && (
          <div className="connection-actions">
            <button className="icon-button primary" onClick={() => void onRetry()} title="Retry connection">
              <RefreshCcw size={18} />
              <span>Retry</span>
            </button>
            <span>Check the app services, then retry.</span>
          </div>
        )}
      </section>
    </main>
  );
}
