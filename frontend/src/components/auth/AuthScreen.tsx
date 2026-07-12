import type React from "react";
import { Sparkles } from "lucide-react";
import type { AuthForm } from "../../types";
import { ErrorList } from "../ui/ErrorList";
import { Field } from "../ui/Field";

type AuthMode = "signup" | "login";

type AuthScreenProps = {
  authMode: AuthMode;
  authForm: AuthForm;
  authErrors: string[];
  bootstrapError: string;
  busy: boolean;
  onAuthModeChange: (mode: AuthMode) => void;
  onAuthFormChange: (form: AuthForm) => void;
  onSubmit: (event: React.FormEvent) => void;
};

export function AuthScreen({
  authMode,
  authForm,
  authErrors,
  bootstrapError,
  busy,
  onAuthModeChange,
  onAuthFormChange,
  onSubmit,
}: AuthScreenProps) {
  return (
    <main className="auth-shell">
      <section className="auth-panel">
        <div className="auth-copy">
          <p className="eyebrow">Quainy Vouch</p>
          <h1>Turn real company work into trusted public communication.</h1>
          <p>
            Create your organization, add approved context when ready, and let the system surface source-backed opportunities you can brief,
            review, publish, and learn from.
          </p>
        </div>
        <form className="auth-form" onSubmit={onSubmit} autoComplete={authMode === "signup" ? "off" : "on"}>
          <div className="auth-toggle" aria-label="Authentication mode">
            <button type="button" className={authMode === "signup" ? "active" : ""} onClick={() => onAuthModeChange("signup")}>
              Sign up
            </button>
            <button type="button" className={authMode === "login" ? "active" : ""} onClick={() => onAuthModeChange("login")}>
              Log in
            </button>
          </div>
          {authMode === "signup" && (
            <>
              <Field label="Your name" required>
                <input
                  value={authForm.name}
                  onChange={(event) => onAuthFormChange({ ...authForm, name: event.target.value })}
                  autoComplete="name"
                />
              </Field>
              <Field label="Organization" required>
                <input
                  value={authForm.organization_name}
                  onChange={(event) => onAuthFormChange({ ...authForm, organization_name: event.target.value })}
                  placeholder="Acme Labs"
                  autoComplete="organization"
                />
              </Field>
              <Field label="Website">
                <input
                  value={authForm.website_url}
                  onChange={(event) => onAuthFormChange({ ...authForm, website_url: event.target.value })}
                  placeholder="https://example.com"
                  autoComplete="url"
                />
              </Field>
              <Field label="Industry">
                <input value={authForm.industry} onChange={(event) => onAuthFormChange({ ...authForm, industry: event.target.value })} />
              </Field>
              <Field label="What do you do?" wide>
                <textarea
                  value={authForm.description}
                  onChange={(event) => onAuthFormChange({ ...authForm, description: event.target.value })}
                  placeholder="A short description is enough. You can improve this later."
                />
              </Field>
            </>
          )}
          <Field label="Email" required>
            <input
              value={authForm.email}
              onChange={(event) => onAuthFormChange({ ...authForm, email: event.target.value })}
              autoComplete="email"
            />
          </Field>
          <Field label="Password" required>
            <input
              type="password"
              value={authForm.password}
              onChange={(event) => onAuthFormChange({ ...authForm, password: event.target.value })}
              autoComplete={authMode === "signup" ? "new-password" : "current-password"}
            />
          </Field>
          <ErrorList errors={authErrors} />
          {bootstrapError && <p className="notice">{bootstrapError}</p>}
          <button className="icon-button primary" type="submit" disabled={busy}>
            <Sparkles size={18} />
            <span>{busy ? "Working..." : authMode === "signup" ? "Create workspace" : "Log in"}</span>
          </button>
        </form>
      </section>
    </main>
  );
}
