import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive,
  Check,
  Clipboard,
  FileText,
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

type Claim = {
  text: string;
  support_status: string;
  supporting_chunk_ids: string[];
  risk_reason?: string;
};

type Draft = {
  id: string;
  body: string;
  hook: string;
  status: string;
  risk_report: string[];
  quality_report: string[];
  duplicate_report: { duplicate_score: number; similar_posts: Array<{ excerpt: string; score: number }> };
  claims: Claim[];
};

type SourceChunk = {
  id: string;
  source_id: string;
  chunk_text: string;
};

type ReviewerPackage = {
  draft: Draft;
  opportunity: Opportunity;
  sources: Source[];
  source_chunks: SourceChunk[];
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
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<Draft | null>(null);
  const [reviewPackage, setReviewPackage] = useState<ReviewerPackage | null>(null);
  const [editedBody, setEditedBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    api<Bootstrap>("/bootstrap").then((data) => {
      setBootstrap(data);
      setSetupForm(setupFromBootstrap(data));
      setOpportunities(data.opportunities);
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

  if (!bootstrap) {
    return <main className="loading">Quainy Vouch</main>;
  }

  async function generateOpportunities() {
    if (!bootstrap) return;
    setBusy(true);
    const result = await api<{ opportunities: Opportunity[] }>(
      `/organizations/${bootstrap.organization.id}/opportunities/generate`,
      { method: "POST" },
    );
    setOpportunities(result.opportunities);
    setSelectedOpportunity(result.opportunities[0] ?? null);
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
      setNotice(`Source marked ${approvalStatus}.`);
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
      setSelectedOpportunity(null);
      setDrafts([]);
      setSelectedDraft(null);
      setNotice("New workspace created. Add sources in the next sprint.");
    } finally {
      setBusy(false);
    }
  }

  async function generateDrafts(opportunity: Opportunity) {
    setBusy(true);
    setSelectedOpportunity(opportunity);
    const brief = await api<{ id: string }>(`/opportunities/${opportunity.id}/briefs`, { method: "POST" });
    const result = await api<{ drafts: Draft[] }>(`/briefs/${brief.id}/drafts`, { method: "POST" });
    setDrafts(result.drafts);
    setSelectedDraft(result.drafts[0] ?? null);
    setBusy(false);
  }

  async function approveDraft() {
    if (!selectedDraft) return;
    setBusy(true);
    await api(`/drafts/${selectedDraft.id}/approve`, {
      method: "POST",
      body: JSON.stringify({ edited_body: editedBody, reason: "Approved in local review desk" }),
    });
    const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
    setSelectedDraft(updated);
    setNotice("Approved and stored in memory.");
    setBusy(false);
  }

  async function rejectDraft() {
    if (!selectedDraft) return;
    setBusy(true);
    await api(`/drafts/${selectedDraft.id}/reject`, {
      method: "POST",
      body: JSON.stringify({ edited_body: editedBody, reason: "Needs stronger source support" }),
    });
    const updated = await api<Draft>(`/drafts/${selectedDraft.id}`);
    setSelectedDraft(updated);
    setNotice("Rejected with review signal.");
    setBusy(false);
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
      setNotice(copied ? "Exported and copied." : "Exported. Clipboard permission was unavailable.");
    } finally {
      setBusy(false);
    }
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
              {opportunities.map((opportunity) => (
                <button
                  className={`opportunity-card ${selectedOpportunity?.id === opportunity.id ? "selected" : ""}`}
                  key={opportunity.id}
                  onClick={() => generateDrafts(opportunity)}
                >
                  <span className="score">{Math.round(opportunity.relevance_score * 100)}%</span>
                  <h3>{opportunity.title}</h3>
                  <p>{opportunity.reason_today}</p>
                </button>
              ))}
            </div>
          </section>

          {drafts.length > 0 && (
            <section className="panel band">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Drafts</p>
                  <h2>LinkedIn company post</h2>
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
                <div className="action-row">
                  <button className="icon-button primary" onClick={approveDraft} disabled={busy} title="Approve draft">
                    <Check size={18} />
                    <span>Approve</span>
                  </button>
                  <button className="icon-button" onClick={rejectDraft} disabled={busy} title="Reject draft">
                    <X size={18} />
                    <span>Reject</span>
                  </button>
                  <button className="icon-button" onClick={exportDraft} disabled={busy} title="Export draft">
                    <Clipboard size={18} />
                    <span>Export</span>
                  </button>
                  <button
                    className="icon-button"
                    onClick={() => selectedOpportunity && generateDrafts(selectedOpportunity)}
                    disabled={busy}
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
