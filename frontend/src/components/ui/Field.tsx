import type React from "react";

type FieldProps = {
  label: string;
  wide?: boolean;
  required?: boolean;
  children: React.ReactNode;
};

export function Field({ label, wide, required, children }: FieldProps) {
  return (
    <label className={`field ${wide ? "wide" : ""}`}>
      <span>
        {label}
        {required && <b aria-label="required">*</b>}
      </span>
      {children}
    </label>
  );
}
