import type { ParameterDefinition, RawParamValue } from "@/lib/operation-types";

type ParamFieldProps = {
  operationId: string;
  param: ParameterDefinition;
  value: RawParamValue | undefined;
  onChange: (key: string, value: RawParamValue) => void;
};

export function ParamField({ operationId, param, value, onChange }: ParamFieldProps) {
  const inputId = `param-${operationId}-${param.key}`;

  if (param.type === "select") {
    return (
      <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500" htmlFor={inputId}>
        {param.label}
        <select
          id={inputId}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(param.key, e.target.value)}
          className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
        >
          {(param.options ?? []).map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>
    );
  }

  if (param.type === "multiselect") {
    const selected = Array.isArray(value) ? value : [];
    return (
      <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500" htmlFor={inputId}>
        {param.label}
        <select
          id={inputId}
          multiple
          size={5}
          value={selected}
          onChange={(e) =>
            onChange(
              param.key,
              Array.from(e.target.selectedOptions).map((o) => o.value)
            )
          }
          className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
        >
          {(param.options ?? []).map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500" htmlFor={inputId}>
      {param.label}
      <input
        id={inputId}
        type={param.type}
        value={typeof value === "string" ? value : ""}
        placeholder={param.placeholder ?? ""}
        onChange={(e) => onChange(param.key, e.target.value)}
        className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
      />
    </label>
  );
}
