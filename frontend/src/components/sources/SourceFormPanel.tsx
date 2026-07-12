import { Upload } from "lucide-react";
import type { SourceForm } from "../../types";
import { Field } from "../ui/Field";
import { type SourceCopy } from "./sourceConfig";

type SourceFormPanelProps = {
  sourceForm: SourceForm;
  sourceCopy: SourceCopy;
  fieldErrors?: Partial<Record<"title" | "uri" | "raw_text" | "freshness_days", string>>;
  onFieldTouched?: (field: "title" | "uri" | "raw_text" | "freshness_days") => void;
  onCommitSourceForm: (form: SourceForm) => void;
  onSourceFile: (file: File | undefined) => void | Promise<void>;
};

export function SourceFormPanel({
  sourceForm,
  sourceCopy,
  fieldErrors = {},
  onFieldTouched,
  onCommitSourceForm,
  onSourceFile,
}: SourceFormPanelProps) {
  return (
    <section className="source-form">
      <div className="source-primary-grid">
        <Field label="Knowledge title" required error={fieldErrors.title}>
          <input
            value={sourceForm.title}
            onChange={(event) => onCommitSourceForm({ ...sourceForm, title: event.target.value })}
            onBlur={() => onFieldTouched?.("title")}
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
        <Field label={sourceCopy.uriLabel} wide required error={fieldErrors.uri}>
          <input
            value={sourceForm.uri}
            onChange={(event) => onCommitSourceForm({ ...sourceForm, uri: event.target.value })}
            onBlur={() => onFieldTouched?.("uri")}
            placeholder={sourceCopy.uriPlaceholder}
          />
        </Field>
      )}
      <Field label={sourceCopy.textLabel} wide required error={fieldErrors.raw_text}>
        <textarea
          className="source-textarea"
          value={sourceForm.raw_text}
          onChange={(event) => onCommitSourceForm({ ...sourceForm, raw_text: event.target.value })}
          onBlur={() => onFieldTouched?.("raw_text")}
          placeholder={sourceCopy.textPlaceholder}
        />
      </Field>
      <div className="source-refresh-panel">
        <div className="source-availability-copy">
          <span>Refresh policy</span>
          <p>Set how often this source should be reviewed for freshness.</p>
        </div>
        <label className="refresh-field">
          <span>Refresh days</span>
          <input
            className={fieldErrors.freshness_days ? "input-error" : ""}
            value={sourceForm.freshness_days}
            onChange={(event) => onCommitSourceForm({ ...sourceForm, freshness_days: event.target.value })}
            onBlur={() => onFieldTouched?.("freshness_days")}
            inputMode="numeric"
          />
          {fieldErrors.freshness_days && <small>{fieldErrors.freshness_days}</small>}
        </label>
      </div>
    </section>
  );
}
