import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive,
  CalendarClock,
  Check,
  Clipboard,
  FileText,
  FileCheck2,
  Library,
  Plus,
  RefreshCcw,
  Save,
  Send,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

type Organization = {
  id: string;
  name: string;
  website_url?: string;
  industry?: string;
  description?: string;
  audience_summary?: string;
  default_timezone?: string;
};

type Profile = {
  one_liner?: string;
  mission?: string;
  product_summary?: string;
  audience?: string;
  voice_rules: string[];
  preferred_phrases: string[];
  banned_phrases: string[];
  approved_claims: string[];
  forbidden_claims: string[];
  content_pillars: string[];
  sensitive_topics: string[];
};

type Source = {
  id: string;
  title: string;
  source_type: string;
  uri?: string;
  approval_status: string;
  freshness_days: number;
  last_ingested_at?: string;
  created_at: string;
  updated_at: string;
};

type AuditLog = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

type SourceDetail = {
  source: Source;
  raw_text: string;
  chunk_count: number;
  audit_logs: AuditLog[];
};

type Opportunity = {
  id: string;
  title: string;
  summary: string;
  reason_today: string;
  relevance_score: number;
  freshness_score: number;
  confidence_score: number;
  source_ids: string[];
};

type ContentBrief = {
  id: string;
  opportunity_id: string;
  organization_id: string;
  objective: string;
  audience: string;
  key_message: string;
  supporting_points: string[];
  claims: string[];
  do_not_say: string[];
  source_ids: string[];
  risks: string[];
  prompt_version: string;
};

type Claim = {
  text: string;
  support_status: string;
  supporting_chunk_ids: string[];
  risk_reason?: string;
};

type ApprovalDecision = {
  id: string;
  draft_id: string;
  decision: string;
  reason?: string;
  created_at: string;
};

type Draft = {
  id: string;
  platform: string;
  content_type: string;
  body: string;
  hook: string;
  status: string;
  source_ids: string[];
  source_map: Record<string, string[]>;
  risk_report: string[];
  quality_report: string[];
  duplicate_report: { duplicate_score: number; similar_posts: Array<{ excerpt: string; score: number }> };
  claims: Claim[];
  generation_metadata: Record<string, unknown>;
  scheduled_for?: string;
  exported_at?: string;
  updated_at: string;
};

type SourceChunk = {
  id: string;
  source_id: string;
  chunk_text: string;
  chunk_index: number;
};

type RetrievalResult = {
  chunk: SourceChunk;
  source: Source;
  score: number;
};

type ReviewerPackage = {
  draft: Draft;
  opportunity: Opportunity;
  sources: Source[];
  source_chunks: SourceChunk[];
  decision_history: ApprovalDecision[];
  suggested_action: string;
};

type Bootstrap = {
  organization: Organization;
  profile: Profile;
  sources: Source[];
  opportunities: Opportunity[];
};

type SetupForm = {
  name: string;
  website_url: string;
  industry: string;
  description: string;
  audience_summary: string;
  default_timezone: string;
  one_liner: string;
  mission: string;
  product_summary: string;
  audience: string;
  voice_rules: string;
  preferred_phrases: string;
  banned_phrases: string;
  approved_claims: string;
  forbidden_claims: string;
  content_pillars: string;
  sensitive_topics: string;
};

type SourceForm = {
  source_type: string;
  title: string;
  uri: string;
  raw_text: string;
  approval_status: string;
  freshness_days: string;
};

type FormatChoice =
  | "linkedin_company_post"
  | "blog_outline"
  | "newsletter_email"
  | "instagram_caption"
  | "instagram_carousel_outline";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function listToText(values: string[] | undefined): string {
  return (values ?? []).join("\n");
}

function textToList(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function draftFormatLabel(draft: Draft | null): string {
  if (!draft) return "Draft";
  if (draft.platform === "blog") return "Blog outline";
  if (draft.platform === "newsletter") return "Newsletter email";
  if (draft.platform === "instagram" && draft.content_type === "carousel_outline") return "Instagram carousel";
  if (draft.platform === "instagram") return "Instagram caption";
  return "LinkedIn company post";
}

function formatChoiceParams(choice: FormatChoice): string {
  const params: Record<FormatChoice, string> = {
    linkedin_company_post: "?platform=linkedin&content_type=company_post",
    blog_outline: "?platform=blog&content_type=outline",
    newsletter_email: "?platform=newsletter&content_type=email",
    instagram_caption: "?platform=instagram&content_type=caption",
    instagram_carousel_outline: "?platform=instagram&content_type=carousel_outline",
  };
  return params[choice];
}

function formatChoiceNotice(choice: FormatChoice): string {
  const notices: Record<FormatChoice, string> = {
    linkedin_company_post: "LinkedIn variants generated from the selected brief.",
    blog_outline: "Blog outline variants generated from the selected brief.",
    newsletter_email: "Newsletter email variants generated from the selected brief.",
    instagram_caption: "Instagram caption variants generated from the selected brief.",
    instagram_carousel_outline: "Instagram carousel variants generated from the selected brief.",
  };
  return notices[choice];
}

function setupFromBootstrap(data: Bootstrap): SetupForm {
  return {
    name: data.organization.name ?? "",
    website_url: data.organization.website_url ?? "",
    industry: data.organization.industry ?? "",
    description: data.organization.description ?? "",
    audience_summary: data.organization.audience_summary ?? "",
    default_timezone: data.organization.default_timezone ?? "UTC",
    one_liner: data.profile.one_liner ?? "",
    mission: data.profile.mission ?? "",
    product_summary: data.profile.product_summary ?? "",
    audience: data.profile.audience ?? "",
    voice_rules: listToText(data.profile.voice_rules),
    preferred_phrases: listToText(data.profile.preferred_phrases),
    banned_phrases: listToText(data.profile.banned_phrases),
    approved_claims: listToText(data.profile.approved_claims),
    forbidden_claims: listToText(data.profile.forbidden_claims),
    content_pillars: listToText(data.profile.content_pillars),
    sensitive_topics: listToText(data.profile.sensitive_topics),
  };
}

const emptySourceForm: SourceForm = {
  source_type: "manual_note",
  title: "",
  uri: "",
  raw_text: "",
  approval_status: "approved",
  freshness_days: "180",
};

function App() {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [setupForm, setSetupForm] = useState<SetupForm | null>(null);
  const [sourceForm, setSourceForm] = useState<SourceForm>(emptySourceForm);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [sourceDetail, setSourceDetail] = useState<SourceDetail | null>(null);
  const [retrievalQuery, setRetrievalQuery] = useState("approved source context");
  const [retrievalResults, setRetrievalResults] = useState<RetrievalResult[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [opportunityMessage, setOpportunityMessage] = useState("");
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);
  const [selectedBrief, setSelectedBrief] = useState<ContentBrief | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<Draft | null>(null);
  const [reviewPackage, setReviewPackage] = useState<ReviewerPackage | null>(null);
  const [editedBody, setEditedBody] = useState("");
  const [reviewReason, setReviewReason] = useState("");
  const [scheduleFor, setScheduleFor] = useState("");
  const [calendarItems, setCalendarItems] = useState<Draft[]>([]);
  const [formatChoice, setFormatChoice] = useState<FormatChoice>("linkedin_company_post");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    api<Bootstrap>("/bootstrap").then((data) => {
      setBootstrap(data);
      setSetupForm(setupFromBootstrap(data));
      setOpportunities(data.opportunities);
      api<Draft[]>(`/organizations/${data.organization.id}/calendar`).then(setCalendarItems);
    });
  }, []);

  useEffect(() => {
    if (!selectedDraft) {
      setReviewPackage(null);
      return;
    }
    api<ReviewerPackage>(`/drafts/${selectedDraft.id}/reviewer-package`).then((pkg) => {
      setReviewPackage(pkg);
      setEditedBody(pkg.draft.body);
      setReviewReason("");
    });
  }, [selectedDraft]);

  useEffect(() => {
    if (!selectedSourceId) {
      setSourceDetail(null);
      return;
    }
    api<SourceDetail>(`/sources/${selectedSourceId}`).then(setSourceDetail);
  }, [selectedSourceId]);

  const healthLabel = useMemo(() => {
    if (!bootstrap) return "Loading";
    return `${bootstrap.sources.length} approved sources`;
  }, [bootstrap]);

  const approvalBlocked = reviewPackage?.suggested_action.toLowerCase().includes("unsupported claims") ?? false;

  if (!bootstrap) {
    return <main className="loading">Quainy Vouch</main>;
  }

  async function generateOpportunities() {
    if (!bootstrap) return;
    setBusy(true);
    const result = await api<{ opportunities: Opportunity[]; message?: string }>(
      `/organizations/${bootstrap.organization.id}/opportunities/generate`,
      { method: "POST" },
    );
    setOpportunities(result.opportunities);
    setOpportunityMessage(result.message ?? (result.opportunities.length ? "Opportunities generated from approved source context." : ""));
    setSelectedOpportunity(result.opportunities[0] ?? null);
    setSelectedBrief(null);
    setDrafts([]);
    setSelectedDraft(null);
    setBusy(false);
  }

  async function saveSetup() {
    if (!bootstrap || !setupForm) return;
    setBusy(true);
    try {
      const organization = await api<Organization>(`/organizations/${bootstrap.organization.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: setupForm.name,
          website_url: setupForm.website_url || null,
          industry: setupForm.industry || null,
          description: setupForm.description || null,
          audience_summary: setupForm.audience_summary || null,
          default_timezone: setupForm.default_timezone || "UTC",
        }),
      });
      const profile = await api<Profile>(`/organizations/${bootstrap.organization.id}/profile`, {
        method: "PATCH",
        body: JSON.stringify({
          one_liner: setupForm.one_liner,
          mission: setupForm.mission,
          product_summary: setupForm.product_summary,
          audience: setupForm.audience,
          voice_rules: textToList(setupForm.voice_rules),
          preferred_phrases: textToList(setupForm.preferred_phrases),
          banned_phrases: textToList(setupForm.banned_phrases),
          approved_claims: textToList(setupForm.approved_claims),
          forbidden_claims: textToList(setupForm.forbidden_claims),
          content_pillars: textToList(setupForm.content_pillars),
          sensitive_topics: textToList(setupForm.sensitive_topics),
        }),
      });
      const nextBootstrap = { ...bootstrap, organization, profile };
      setBootstrap(nextBootstrap);
      setSetupForm(setupFromBootstrap(nextBootstrap));
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      setNotice("Workspace and voice profile saved.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshSources(selectedId?: string) {
    if (!bootstrap) return;
    const sources = await api<Source[]>(`/organizations/${bootstrap.organization.id}/sources`);
    setBootstrap({ ...bootstrap, sources });
    if (selectedId) {
      setSelectedSourceId(selectedId);
      setSourceDetail(await api<SourceDetail>(`/sources/${selectedId}`));
    }
  }

  async function addSource() {
    if (!bootstrap) return;
    setBusy(true);
    try {
      const source = await api<Source>(`/organizations/${bootstrap.organization.id}/sources`, {
        method: "POST",
        body: JSON.stringify({
          source_type: sourceForm.source_type,
          title: sourceForm.title,
          uri: sourceForm.uri || null,
          raw_text: sourceForm.raw_text,
          approval_status: sourceForm.approval_status,
          freshness_days: Number(sourceForm.freshness_days) || 180,
        }),
      });
      setSourceForm(emptySourceForm);
      await refreshSources(source.id);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      setNotice("Source added to the approved knowledge library.");
    } finally {
      setBusy(false);
    }
  }

  async function updateSourceStatus(sourceId: string, approvalStatus: string) {
    setBusy(true);
    try {
      await api<Source>(`/sources/${sourceId}`, {
        method: "PATCH",
        body: JSON.stringify({ approval_status: approvalStatus }),
      });
      await refreshSources(sourceId);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      setNotice(`Source marked ${approvalStatus}.`);
    } finally {
      setBusy(false);
    }
  }

  async function refreshSource(sourceId: string) {
    setBusy(true);
    try {
      await api(`/sources/${sourceId}/refresh`, { method: "POST" });
      await refreshSources(sourceId);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      setNotice("Source refreshed and re-ingested.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSourceFile(file: File | undefined) {
    if (!file) return;
    const rawText = await file.text();
    const extension = file.name.toLowerCase().endsWith(".md") ? "markdown" : "text";
    setSourceForm({
      ...sourceForm,
      source_type: extension,
      title: file.name,
      uri: file.name,
      raw_text: rawText,
    });
  }

  async function runRetrieval() {
    if (!bootstrap || retrievalQuery.trim().length < 2) return;
    setBusy(true);
    try {
      const results = await api<RetrievalResult[]>(`/organizations/${bootstrap.organization.id}/retrieval/query`, {
        method: "POST",
        body: JSON.stringify({ query: retrievalQuery, limit: 5 }),
      });
      setRetrievalResults(results);
      setNotice(results.length ? "Retrieved approved source chunks." : "No approved source chunks matched that query.");
    } finally {
      setBusy(false);
    }
  }

  async function createWorkspaceFromSetup() {
    if (!bootstrap || !setupForm) return;
    setBusy(true);
    try {
      const organization = await api<Organization>("/organizations", {
        method: "POST",
        body: JSON.stringify({
          name: setupForm.name,
          website_url: setupForm.website_url || null,
          industry: setupForm.industry || null,
          description: setupForm.description || null,
          audience_summary: setupForm.audience_summary || null,
          default_timezone: setupForm.default_timezone || "UTC",
        }),
      });
      const profile = await api<Profile>(`/organizations/${organization.id}/profile`, {
        method: "PATCH",
        body: JSON.stringify({
          one_liner: setupForm.one_liner,
          mission: setupForm.mission,
          product_summary: setupForm.product_summary,
          audience: setupForm.audience,
          voice_rules: textToList(setupForm.voice_rules),
          preferred_phrases: textToList(setupForm.preferred_phrases),
          banned_phrases: textToList(setupForm.banned_phrases),
          approved_claims: textToList(setupForm.approved_claims),
          forbidden_claims: textToList(setupForm.forbidden_claims),
          content_pillars: textToList(setupForm.content_pillars),
          sensitive_topics: textToList(setupForm.sensitive_topics),
        }),
      });
      const nextBootstrap = { organization, profile, sources: [], opportunities: [] };
      setBootstrap(nextBootstrap);
      setSetupForm(setupFromBootstrap(nextBootstrap));
      setOpportunities([]);
      setOpportunityMessage("");
      setSelectedOpportunity(null);
      setSelectedBrief(null);
      setDrafts([]);
      setSelectedDraft(null);
      setNotice("New workspace created. Add approved sources to start generating opportunities.");
    } finally {
      setBusy(false);
    }
  }

  async function createBrief(opportunity: Opportunity) {
    setBusy(true);
    try {
      setSelectedOpportunity(opportunity);
      setDrafts([]);
      setSelectedDraft(null);
      const brief = await api<ContentBrief>(`/opportunities/${opportunity.id}/briefs`, { method: "POST" });
      setSelectedBrief(brief);
      setNotice("Brief created from approved source context.");
    } finally {
      setBusy(false);
    }
  }

  async function generateDraftsFromBrief() {
    if (!selectedBrief) return;
    setBusy(true);
    try {
      const params = formatChoiceParams(formatChoice);
      const result = await api<{ drafts: Draft[] }>(`/briefs/${selectedBrief.id}/drafts${params}`, { method: "POST" });
      setDrafts(result.drafts);
      setSelectedDraft(result.drafts[0] ?? null);
      setNotice(formatChoiceNotice(formatChoice));
    } finally {
      setBusy(false);
    }
  }

  async function regenerateSelectedDraft() {
    if (!selectedDraft) return;
    setBusy(true);
    try {
      const result = await api<{ drafts: Draft[] }>(`/drafts/${selectedDraft.id}/regenerate`, { method: "POST" });
      setDrafts(result.drafts);
      setSelectedDraft(result.drafts[0] ?? null);
      setNotice("Drafts regenerated from the same brief and adapter.");
    } finally {
      setBusy(false);
    }
  }

  async function approveDraft() {
    if (!selectedDraft) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ edited_body: editedBody, reason: reviewReason || "Approved in review desk" }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      setNotice("Approved and stored in memory.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Approval failed.");
    } finally {
      setBusy(false);
    }
  }

  async function rejectDraft() {
    if (!selectedDraft) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ edited_body: editedBody, reason: reviewReason }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      setNotice("Rejected with review signal.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Rejection failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDraftEdit() {
    if (!selectedDraft) return;
    setBusy(true);
    try {
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`, {
        method: "PATCH",
        body: JSON.stringify({ body: editedBody }),
      });
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      setNotice("Draft edit saved and review checks refreshed.");
    } finally {
      setBusy(false);
    }
  }

  async function exportDraft() {
    if (!selectedDraft) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/export`, { method: "POST" });
      let copied = false;
      try {
        await navigator.clipboard?.writeText(editedBody);
        copied = true;
      } catch {
        copied = false;
      }
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      setNotice(copied ? "Exported and copied." : "Exported. Clipboard permission was unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function scheduleDraft() {
    if (!selectedDraft || !scheduleFor) return;
    setBusy(true);
    try {
      await api(`/drafts/${selectedDraft.id}/schedule`, {
        method: "POST",
        body: JSON.stringify({
          scheduled_for: new Date(scheduleFor).toISOString(),
          reason: reviewReason || "Manual queue intent",
        }),
      });
      const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
      setSelectedDraft(updated);
      setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)));
      await refreshCalendar();
      setNotice("Scheduled intent saved to the queue.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshCalendar() {
    if (!bootstrap) return;
    setCalendarItems(await api<Draft[]>(`/organizations/${bootstrap.organization.id}/calendar`));
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Quainy Vouch</p>
          <h1>{bootstrap.organization.name}</h1>
        </div>
        <div className="status-strip">
          <span>{healthLabel}</span>
          <span>{bootstrap.profile.content_pillars.length} pillars</span>
          <span>Local MVP</span>
        </div>
      </header>

      <section className="workspace">
        <aside className="rail">
          <section className="panel">
            <div className="panel-title">
              <Library size={18} />
              <h2>Sources</h2>
            </div>
            <div className="source-list">
              {bootstrap.sources.map((source) => (
                <button
                  className={`source-row source-button ${selectedSourceId === source.id ? "selected" : ""}`}
                  key={source.id}
                  onClick={() => setSelectedSourceId(source.id)}
                >
                  <FileText size={16} />
                  <div>
                    <strong>{source.title}</strong>
                    <span>{source.approval_status}</span>
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-title">
              <ShieldCheck size={18} />
              <h2>Voice</h2>
            </div>
            <div className="tag-wrap">
              {bootstrap.profile.preferred_phrases.map((phrase) => (
                <span className="tag" key={phrase}>
                  {phrase}
                </span>
              ))}
            </div>
          </section>
        </aside>

        <section className="main-column">
          {setupForm && (
            <section className="panel band setup-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Setup</p>
                  <h2>Organization and voice profile</h2>
                </div>
                <div className="setup-actions">
                  <button className="icon-button" onClick={createWorkspaceFromSetup} disabled={busy} title="Create workspace">
                    <Plus size={18} />
                    <span>Create workspace</span>
                  </button>
                  <button className="icon-button primary" onClick={saveSetup} disabled={busy} title="Save setup">
                    <Save size={18} />
                    <span>Save setup</span>
                  </button>
                </div>
              </div>
              <div className="setup-grid">
                <Field label="Organization name">
                  <input
                    value={setupForm.name}
                    onChange={(event) => setSetupForm({ ...setupForm, name: event.target.value })}
                  />
                </Field>
                <Field label="Website">
                  <input
                    value={setupForm.website_url}
                    onChange={(event) => setSetupForm({ ...setupForm, website_url: event.target.value })}
                  />
                </Field>
                <Field label="Industry">
                  <input
                    value={setupForm.industry}
                    onChange={(event) => setSetupForm({ ...setupForm, industry: event.target.value })}
                  />
                </Field>
                <Field label="Timezone">
                  <input
                    value={setupForm.default_timezone}
                    onChange={(event) => setSetupForm({ ...setupForm, default_timezone: event.target.value })}
                  />
                </Field>
                <Field label="Description" wide>
                  <textarea
                    className="small-textarea"
                    value={setupForm.description}
                    onChange={(event) => setSetupForm({ ...setupForm, description: event.target.value })}
                  />
                </Field>
                <Field label="Audience summary" wide>
                  <textarea
                    className="small-textarea"
                    value={setupForm.audience_summary}
                    onChange={(event) => setSetupForm({ ...setupForm, audience_summary: event.target.value })}
                  />
                </Field>
                <Field label="One-liner" wide>
                  <input
                    value={setupForm.one_liner}
                    onChange={(event) => setSetupForm({ ...setupForm, one_liner: event.target.value })}
                  />
                </Field>
                <Field label="Mission" wide>
                  <textarea
                    className="small-textarea"
                    value={setupForm.mission}
                    onChange={(event) => setSetupForm({ ...setupForm, mission: event.target.value })}
                  />
                </Field>
                <Field label="Product summary" wide>
                  <textarea
                    className="small-textarea"
                    value={setupForm.product_summary}
                    onChange={(event) => setSetupForm({ ...setupForm, product_summary: event.target.value })}
                  />
                </Field>
                <Field label="Primary audience" wide>
                  <textarea
                    className="small-textarea"
                    value={setupForm.audience}
                    onChange={(event) => setSetupForm({ ...setupForm, audience: event.target.value })}
                  />
                </Field>
                <Field label="Voice rules">
                  <textarea
                    className="list-textarea"
                    value={setupForm.voice_rules}
                    onChange={(event) => setSetupForm({ ...setupForm, voice_rules: event.target.value })}
                  />
                </Field>
                <Field label="Content pillars">
                  <textarea
                    className="list-textarea"
                    value={setupForm.content_pillars}
                    onChange={(event) => setSetupForm({ ...setupForm, content_pillars: event.target.value })}
                  />
                </Field>
                <Field label="Preferred phrases">
                  <textarea
                    className="list-textarea"
                    value={setupForm.preferred_phrases}
                    onChange={(event) => setSetupForm({ ...setupForm, preferred_phrases: event.target.value })}
                  />
                </Field>
                <Field label="Banned phrases">
                  <textarea
                    className="list-textarea"
                    value={setupForm.banned_phrases}
                    onChange={(event) => setSetupForm({ ...setupForm, banned_phrases: event.target.value })}
                  />
                </Field>
                <Field label="Approved claims">
                  <textarea
                    className="list-textarea"
                    value={setupForm.approved_claims}
                    onChange={(event) => setSetupForm({ ...setupForm, approved_claims: event.target.value })}
                  />
                </Field>
                <Field label="Forbidden claims">
                  <textarea
                    className="list-textarea"
                    value={setupForm.forbidden_claims}
                    onChange={(event) => setSetupForm({ ...setupForm, forbidden_claims: event.target.value })}
                  />
                </Field>
              </div>
              {notice && <p className="notice">{notice}</p>}
            </section>
          )}

          <section className="panel band source-library-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Source Library</p>
                <h2>Approved company knowledge</h2>
              </div>
              <button className="icon-button primary" onClick={addSource} disabled={busy || sourceForm.raw_text.trim().length < 20 || !sourceForm.title.trim()} title="Add source">
                <Plus size={18} />
                <span>Add source</span>
              </button>
            </div>
            <div className="source-library-grid">
              <section className="source-form">
                <div className="source-form-row">
                  <Field label="Source title">
                    <input
                      value={sourceForm.title}
                      onChange={(event) => setSourceForm({ ...sourceForm, title: event.target.value })}
                    />
                  </Field>
                  <Field label="Source type">
                    <select
                      value={sourceForm.source_type}
                      onChange={(event) => setSourceForm({ ...sourceForm, source_type: event.target.value })}
                    >
                      <option value="manual_note">Manual note</option>
                      <option value="markdown">Markdown</option>
                      <option value="text">Text</option>
                      <option value="url">URL page</option>
                      <option value="github_release">GitHub release</option>
                      <option value="notion_page">Notion page</option>
                    </select>
                  </Field>
                  <Field label="Status">
                    <select
                      value={sourceForm.approval_status}
                      onChange={(event) => setSourceForm({ ...sourceForm, approval_status: event.target.value })}
                    >
                      <option value="approved">Approved</option>
                      <option value="disabled">Disabled</option>
                      <option value="archived">Archived</option>
                    </select>
                  </Field>
                  <Field label="Freshness days">
                    <input
                      value={sourceForm.freshness_days}
                      onChange={(event) => setSourceForm({ ...sourceForm, freshness_days: event.target.value })}
                    />
                  </Field>
                </div>
                <Field label="URI or filename" wide>
                  <input value={sourceForm.uri} onChange={(event) => setSourceForm({ ...sourceForm, uri: event.target.value })} />
                </Field>
                <label className="upload-target">
                  <Upload size={18} />
                  <span>Upload markdown or text</span>
                  <input type="file" accept=".md,.markdown,.txt,text/plain,text/markdown" onChange={(event) => handleSourceFile(event.target.files?.[0])} />
                </label>
                <Field label="Approved source text" wide>
                  <textarea
                    className="source-textarea"
                    value={sourceForm.raw_text}
                    onChange={(event) => setSourceForm({ ...sourceForm, raw_text: event.target.value })}
                  />
                </Field>
              </section>

              <section className="source-detail">
                {sourceDetail ? (
                  <>
                    <div className="source-detail-header">
                      <div>
                        <p className="eyebrow">Source Detail</p>
                        <h3>{sourceDetail.source.title}</h3>
                      </div>
                      <span className={`status-pill ${sourceDetail.source.approval_status}`}>{sourceDetail.source.approval_status}</span>
                    </div>
                    <div className="source-actions">
                      {["approved", "disabled", "archived"].map((status) => (
                        <button
                          className={sourceDetail.source.approval_status === status ? "active" : ""}
                          key={status}
                          onClick={() => updateSourceStatus(sourceDetail.source.id, status)}
                          disabled={busy}
                        >
                          {status}
                        </button>
                      ))}
                      <button onClick={() => refreshSource(sourceDetail.source.id)} disabled={busy}>
                        refresh
                      </button>
                    </div>
                    <div className="source-meta">
                      <span>{sourceDetail.source.source_type}</span>
                      <span>{sourceDetail.chunk_count} chunks</span>
                      <span>{sourceDetail.source.freshness_days} freshness days</span>
                    </div>
                    <p className="source-raw">{sourceDetail.raw_text}</p>
                    <div className="audit-list">
                      <h4>Audit events</h4>
                      {sourceDetail.audit_logs.map((log) => (
                        <div className="audit-row" key={log.id}>
                          <strong>{log.action}</strong>
                          <span>{new Date(log.created_at).toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="empty-detail">
                    <Library size={24} />
                    <p>Select a source to inspect text, status, chunks, and audit events.</p>
                  </div>
                )}
              </section>
            </div>
            <section className="retrieval-inspector">
              <div className="section-heading compact-heading">
                <div>
                  <p className="eyebrow">Retrieval</p>
                  <h3>Approved-source search</h3>
                </div>
                <button className="icon-button" onClick={runRetrieval} disabled={busy || retrievalQuery.trim().length < 2} title="Search approved context">
                  <RefreshCcw size={18} />
                  <span>Search</span>
                </button>
              </div>
              <div className="retrieval-query-row">
                <input value={retrievalQuery} onChange={(event) => setRetrievalQuery(event.target.value)} />
              </div>
              <div className="retrieval-results">
                {retrievalResults.length > 0 ? (
                  retrievalResults.map((result) => (
                    <article className="retrieval-result" key={result.chunk.id}>
                      <div>
                        <strong>{result.source.title}</strong>
                        <span>chunk {result.chunk.chunk_index + 1}</span>
                        <span>{Math.round(result.score * 100)}%</span>
                      </div>
                      <p>{result.chunk.chunk_text}</p>
                    </article>
                  ))
                ) : (
                  <p className="empty-results">Run a query to verify which approved chunks retrieval can use.</p>
                )}
              </div>
            </section>
          </section>

          <section className="panel band">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Opportunities</p>
                <h2>Source-backed angles</h2>
              </div>
              <button className="icon-button primary" onClick={generateOpportunities} disabled={busy} title="Generate opportunities">
                <RefreshCcw size={18} />
                <span>Generate</span>
              </button>
            </div>
            <div className="opportunity-grid">
              {opportunities.length > 0 ? (
                opportunities.map((opportunity) => (
                  <button
                    className={`opportunity-card ${selectedOpportunity?.id === opportunity.id ? "selected" : ""}`}
                    key={opportunity.id}
                    onClick={() => createBrief(opportunity)}
                  >
                    <div className="opportunity-scores">
                      <span className="score">{Math.round(opportunity.relevance_score * 100)}% relevant</span>
                      <span>{Math.round(opportunity.freshness_score * 100)}% fresh</span>
                      <span>{opportunity.source_ids.length} source{opportunity.source_ids.length === 1 ? "" : "s"}</span>
                    </div>
                    <h3>{opportunity.title}</h3>
                    <p>{opportunity.reason_today}</p>
                  </button>
                ))
              ) : (
                <div className="empty-opportunities">
                  <Sparkles size={22} />
                  <p>{opportunityMessage || "Generate opportunities after adding enough approved source context."}</p>
                </div>
              )}
            </div>
            {opportunityMessage && opportunities.length > 0 && <p className="notice">{opportunityMessage}</p>}
          </section>

          {selectedBrief && (
            <section className="panel band brief-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Brief</p>
                  <h2>Platform-independent source brief</h2>
                </div>
                <div className="format-actions">
                  <select value={formatChoice} onChange={(event) => setFormatChoice(event.target.value as FormatChoice)}>
                    <option value="linkedin_company_post">LinkedIn post</option>
                    <option value="blog_outline">Blog outline</option>
                    <option value="newsletter_email">Newsletter email</option>
                    <option value="instagram_caption">Instagram caption</option>
                    <option value="instagram_carousel_outline">Instagram carousel</option>
                  </select>
                  <button className="icon-button primary" onClick={generateDraftsFromBrief} disabled={busy} title="Generate drafts">
                    <FileCheck2 size={18} />
                    <span>Generate drafts</span>
                  </button>
                </div>
              </div>
              <div className="brief-grid">
                <section className="brief-summary">
                  <span>Objective</span>
                  <p>{selectedBrief.objective}</p>
                  <span>Audience</span>
                  <p>{selectedBrief.audience}</p>
                  <span>Key message</span>
                  <p>{selectedBrief.key_message}</p>
                </section>
                <section className="brief-list">
                  <h3>Supporting points</h3>
                  <ul className="plain-list">
                    {selectedBrief.supporting_points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </section>
                <section className="brief-list">
                  <h3>Guardrails</h3>
                  <ul className="plain-list">
                    {[...selectedBrief.do_not_say, ...selectedBrief.risks].map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>
              </div>
            </section>
          )}

          {drafts.length > 0 && (
            <section className="panel band">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Drafts</p>
                  <h2>{draftFormatLabel(selectedDraft)}</h2>
                </div>
                <Sparkles size={20} />
              </div>
              <div className="draft-tabs">
                {drafts.map((draft, index) => (
                  <button
                    key={draft.id}
                    className={selectedDraft?.id === draft.id ? "active" : ""}
                    onClick={() => setSelectedDraft(draft)}
                  >
                    Variant {index + 1}
                  </button>
                ))}
              </div>
              {selectedDraft && (
                <div className="draft-meta-row">
                  <span>{String(selectedDraft.generation_metadata.adapter_name ?? selectedDraft.platform ?? "adapter")}</span>
                  <span>{String(selectedDraft.generation_metadata.prompt_version ?? "prompt tracked")}</span>
                  <span>{selectedDraft.source_ids.length} source{selectedDraft.source_ids.length === 1 ? "" : "s"}</span>
                  <span>{Object.keys(selectedDraft.source_map).length} source map candidate{Object.keys(selectedDraft.source_map).length === 1 ? "" : "s"}</span>
                </div>
              )}
            </section>
          )}

          {reviewPackage && selectedDraft && (
            <section className="review-grid">
              <section className="panel review-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Review Desk</p>
                    <h2>{selectedDraft.status.replace("_", " ")}</h2>
                  </div>
                  <span className="review-status">{reviewPackage.suggested_action}</span>
                </div>
                <textarea value={editedBody} onChange={(event) => setEditedBody(event.target.value)} />
                <div className="review-reason-row">
                  <input
                    value={reviewReason}
                    onChange={(event) => setReviewReason(event.target.value)}
                    placeholder="Decision note or rejection reason"
                  />
                  <input type="datetime-local" value={scheduleFor} onChange={(event) => setScheduleFor(event.target.value)} />
                </div>
                <div className="action-row">
                  <button className="icon-button" onClick={saveDraftEdit} disabled={busy || editedBody === selectedDraft.body} title="Save edit">
                    <Save size={18} />
                    <span>Save edit</span>
                  </button>
                  <button
                    className="icon-button primary"
                    onClick={approveDraft}
                    disabled={busy || approvalBlocked}
                    title={approvalBlocked ? "Resolve unsupported claims before approval" : "Approve draft"}
                  >
                    <Check size={18} />
                    <span>Approve</span>
                  </button>
                  <button className="icon-button" onClick={rejectDraft} disabled={busy || !reviewReason.trim()} title="Reject draft">
                    <X size={18} />
                    <span>Reject</span>
                  </button>
                  <button className="icon-button" onClick={exportDraft} disabled={busy} title="Export draft">
                    <Clipboard size={18} />
                    <span>Export</span>
                  </button>
                  <button className="icon-button" onClick={scheduleDraft} disabled={busy || !scheduleFor} title="Schedule intent">
                    <CalendarClock size={18} />
                    <span>Schedule</span>
                  </button>
                  <button
                    className="icon-button"
                    onClick={regenerateSelectedDraft}
                    disabled={busy || !selectedDraft}
                    title="Regenerate drafts"
                  >
                    <Send size={18} />
                    <span>Regenerate</span>
                  </button>
                </div>
                {notice && <p className="notice">{notice}</p>}
              </section>

              <aside className="evidence-column">
                <InsightList title="Risk" icon={<Archive size={17} />} items={selectedDraft.risk_report} />
                <InsightList title="Quality" icon={<ShieldCheck size={17} />} items={selectedDraft.quality_report} />
                {selectedDraft.duplicate_report.similar_posts.length > 0 && (
                  <section className="panel compact">
                    <div className="panel-title">
                      <RefreshCcw size={17} />
                      <h2>Similar Memory</h2>
                    </div>
                    {selectedDraft.duplicate_report.similar_posts.map((post) => (
                      <div className="memory-match" key={post.excerpt}>
                        <strong>{Math.round(post.score * 100)}% similar</strong>
                        <p>{post.excerpt}</p>
                      </div>
                    ))}
                  </section>
                )}
                {reviewPackage.decision_history.length > 0 && (
                  <section className="panel compact">
                    <div className="panel-title">
                      <ShieldCheck size={17} />
                      <h2>Decision History</h2>
                    </div>
                    {reviewPackage.decision_history.map((decision) => (
                      <div className="decision-row" key={decision.id}>
                        <strong>{decision.decision}</strong>
                        <span>{new Date(decision.created_at).toLocaleString()}</span>
                        {decision.reason && <p>{decision.reason}</p>}
                      </div>
                    ))}
                  </section>
                )}
                <section className="panel compact">
                  <div className="panel-title">
                    <FileText size={17} />
                    <h2>Claims</h2>
                  </div>
                  <div className="claim-list">
                    {selectedDraft.claims.map((claim) => (
                      <div className="claim-row" key={claim.text}>
                        <span className={`dot ${claim.support_status}`} />
                        <p>{claim.text}</p>
                      </div>
                    ))}
                  </div>
                </section>
                <section className="panel compact">
                  <div className="panel-title">
                    <Library size={17} />
                    <h2>Evidence</h2>
                  </div>
                  {reviewPackage.source_chunks.slice(0, 4).map((chunk) => (
                    <p className="excerpt" key={chunk.id}>
                      {chunk.chunk_text}
                    </p>
                  ))}
                </section>
              </aside>
            </section>
          )}

          <section className="panel band">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Queue</p>
                <h2>Approved and upcoming posts</h2>
              </div>
              <CalendarClock size={20} />
            </div>
            <div className="queue-list">
              {calendarItems.length > 0 ? (
                calendarItems.map((item) => (
                  <article className="queue-row" key={item.id}>
                    <div>
                      <strong>{item.hook || item.body.slice(0, 80)}</strong>
                      <span>{item.status}</span>
                    </div>
                    <p>{item.body}</p>
                    <small>
                      {item.scheduled_for
                        ? `Scheduled ${new Date(item.scheduled_for).toLocaleString()}`
                        : item.exported_at
                          ? `Exported ${new Date(item.exported_at).toLocaleString()}`
                          : `Updated ${new Date(item.updated_at).toLocaleString()}`}
                    </small>
                  </article>
                ))
              ) : (
                <p className="empty-results">Approved, scheduled, and exported drafts will appear here.</p>
              )}
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}

function Field({ label, wide, children }: { label: string; wide?: boolean; children: React.ReactNode }) {
  return (
    <label className={`field ${wide ? "wide" : ""}`}>
      <span>{label}</span>
      {children}
    </label>
  );
}

function InsightList({ title, icon, items }: { title: string; icon: React.ReactNode; items: string[] }) {
  return (
    <section className="panel compact">
      <div className="panel-title">
        {icon}
        <h2>{title}</h2>
      </div>
      <ul className="plain-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

const rootElement = document.getElementById("root")!;
window.__quainyVouchRoot ??= createRoot(rootElement);
window.__quainyVouchRoot.render(<App />);
