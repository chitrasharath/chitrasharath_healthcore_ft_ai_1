type FormFieldProps = {
  id: string;
  label: string;
  value: string | number;
  placeholder?: string;
  type?: "text" | "email" | "number";
  readOnly?: boolean;
  min?: number;
  error?: string;
  onChange?: (value: string) => void;
};

export const FormField = ({
  id,
  label,
  value,
  placeholder,
  type = "text",
  readOnly,
  min,
  error,
  onChange,
}: FormFieldProps) => {
  return (
    <label htmlFor={id} className="flex flex-col gap-1 text-sm">
      <span className="font-medium text-[var(--hc-text)]">{label}</span>
      <input
        id={id}
        value={value}
        placeholder={placeholder}
        type={type}
        readOnly={readOnly}
        min={min}
        onChange={(event) => onChange?.(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
        className="rounded-md border border-[var(--hc-border)] px-3 py-2 text-sm"
      />
      {error ? (
        <span id={`${id}-error`} className="text-xs text-[var(--hc-danger)]">
          {error}
        </span>
      ) : null}
    </label>
  );
};
