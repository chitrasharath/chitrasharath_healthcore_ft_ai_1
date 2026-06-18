import type { ReactNode } from "react";

type FormFieldProps = {
  id: string;
  label: string;
  error?: string;
  describedBy?: string;
  children: ReactNode;
};

export const FormField = ({ id, label, error, describedBy, children }: FormFieldProps) => {
  const errorId = `${id}_error`;
  const ariaDescribedBy = [describedBy, error ? errorId : undefined].filter(Boolean).join(" ") || undefined;

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-semibold text-slate-800">
        {label}
      </label>
      <div className="mt-1" aria-describedby={ariaDescribedBy}>
        {children}
      </div>
      {error ? (
        <p id={errorId} className="mt-1 text-sm font-medium text-red-700" role="alert" aria-live="polite">
          {error}
        </p>
      ) : null}
    </div>
  );
};

export const inputClass =
  "w-full rounded-md border border-slate-300 px-3 py-2 focus:border-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-200";

export const invalidAttrs = (error?: string) =>
  error ? ({ "aria-invalid": true as const }) : {};
