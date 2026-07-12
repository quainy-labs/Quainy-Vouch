import { X } from "lucide-react";
import type { OnboardingState } from "../../types";

type OnboardingBannerProps = {
  onboarding: OnboardingState;
  busy: boolean;
  onOpenSettings: () => void;
  onSkipProfile: () => void | Promise<void>;
  onAddSource: () => void;
};

export function OnboardingBanner({ onboarding, busy, onSkipProfile }: OnboardingBannerProps) {
  const canSkipProfile =
    !onboarding.completed_steps.includes("profile_skipped") && !onboarding.completed_steps.includes("profile_started");

  return (
    <section className="onboarding-banner">
      <div>
        <p className="eyebrow">Fast onboarding</p>
        <h2>Start light, improve accuracy over time.</h2>
        <p>Add approved context when it is ready. You can refine profile, sources, and integrations later.</p>
      </div>
      <div className="onboarding-progress">
        <strong>{onboarding.completion_percent}%</strong>
        <span>{onboarding.completed_steps.map((step) => step.replace(/_/g, " ")).join(" / ")}</span>
      </div>
      <div className="onboarding-actions">
        {canSkipProfile && (
          <button className="icon-button" onClick={() => void onSkipProfile()} type="button" disabled={busy}>
            <X size={16} />
            <span>Skip profile</span>
          </button>
        )}
      </div>
    </section>
  );
}
