import { Save, Upload, X } from "lucide-react";
import type { OnboardingState } from "../../types";

type OnboardingBannerProps = {
  onboarding: OnboardingState;
  busy: boolean;
  onOpenSettings: () => void;
  onSkipProfile: () => void | Promise<void>;
  onAddSource: () => void;
};

export function OnboardingBanner({ onboarding, busy, onOpenSettings, onSkipProfile, onAddSource }: OnboardingBannerProps) {
  const canSkipProfile =
    !onboarding.completed_steps.includes("profile_skipped") && !onboarding.completed_steps.includes("profile_started");

  return (
    <section className="onboarding-banner">
      <div>
        <p className="eyebrow">Fast onboarding</p>
        <h2>Start light, improve accuracy as you add context.</h2>
        <p>
          Add enough organization detail and one approved source to unlock better-ranked opportunities. You can refine voice, claims,
          sources, and integrations later.
        </p>
      </div>
      <div className="onboarding-progress">
        <strong>{onboarding.completion_percent}%</strong>
        <span>{onboarding.completed_steps.map((step) => step.replace(/_/g, " ")).join(" / ")}</span>
      </div>
      <div className="onboarding-actions">
        <button className="icon-button" onClick={onOpenSettings} type="button">
          <Save size={16} />
          <span>Org details</span>
        </button>
        {canSkipProfile && (
          <button className="icon-button" onClick={() => void onSkipProfile()} type="button" disabled={busy}>
            <X size={16} />
            <span>Skip profile</span>
          </button>
        )}
        <button className="icon-button primary" onClick={onAddSource} type="button">
          <Upload size={16} />
          <span>Add source</span>
        </button>
      </div>
    </section>
  );
}
