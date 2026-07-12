import { Upload } from "lucide-react";
import type { SourceForm } from "../../types";
import { Field } from "../ui/Field";
import { sourceStatuses, type SourceCopy } from "./sourceConfig";

type SourceFormPanelProps = {
  sourceForm: SourceForm;
  sourceCopy: SourceCopy;
  onCommitSourceForm: (form: SourceForm) => void;
  onSourceFile: (file: File | undefined) => void | Promise<void>;
};

export function SourceFormPanel({ sourceForm, sourceCopy, onCommitSourceForm, onSourceFile }: SourceFormPanelProps) {
  return (
    <section className="source-form">
      <div className="source-primary-grid">
        <Field label="Knowledge title" required>
          <input
            value={sourceForm.title}
            onChange={(event) => onCommitSourceForm({ ...sourceForm, title: event.target.value })}
            placeholder={sourceCopy.titlePlaceholder}
          />
        </Field>
        {sourceCopy.showUpload ? (
          <label className="upload-target">
            <Upload size={18} />
            <span>Upload file</span>
            <input type="file" accept=".md,.markdown,.txt,text/plain,text/markdown" onChange={(event) => void onSourceFile(event.target.files?.[0])} />
          </label>
        ) : (
          <div className="source-mode-note">
            <span>{sourceForm.source_type.replace("_", " ")}</span>
            <p>No file needed for this source type.</p>
          </div>
        )}
      </div>
      {sourceCopy.uriLabel && (
        <Field label={sourceCopy.uriLabel} wide required>
          <input
            value={sourceForm.uri}
            onChange={(event) => onCommitSourceForm({ ...sourceForm, uri: event.target.value })}
            placeholder={sourceCopy.uriPlaceholder}
          />
        </Field>
      )}
      <Field label={sourceCopy.textLabel} wide required>
        <textarea
          className="source-textarea"
          value={sourceForm.raw_text}
          onChange={(event) => onCommitSourceForm({ ...sourceForm, raw_text: event.target.value })}
          placeholder={sourceCopy.textPlaceholder}
        />
      </Field>
      <div className="source-availability-panel">
        <div className="source-availability-copy">
          <span>Availability</span>
          <p>Choose whether this source can be used as active evidence.</p>
        </div>
        <div className="source-availability-controls">
          <div className="source-status-options" aria-label="Source availability">
            {sourceStatuses.map((status) => (
              <button
                className={sourceForm.approval_status === status ? "active" : ""}
                key={status}
                onClick={() => onCommitSourceForm({ ...sourceForm, approval_status: status })}
                type="button"
              >
                {status}
              </button>
            ))}
          </div>
          <label className="refresh-field">
            <span>Refresh days</span>
            <input
              value={sourceForm.freshness_days}
              onChange={(event) => onCommitSourceForm({ ...sourceForm, freshness_days: event.target.value })}
              inputMode="numeric"
            />
          </label>
        </div>
      </div>
    </section>
  );
}
