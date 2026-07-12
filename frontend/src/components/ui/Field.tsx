import type React from "react";

type FieldProps = {
  label: string;
  error?: string;
  wide?: boolean;
  required?: boolean;
  children: React.ReactNode;
};

export function Field({ label, error, wide, required, children }: FieldProps) {
  return (
    <label className={`field ${wide ? "wide" : ""} ${error ? "field-error" : ""}`}>
      <span>
        {label}
        {required && <b aria-label="required">*</b>}
      </span>
      {children}
      {error && <small>{error}</small>}
    </label>
  );
}
