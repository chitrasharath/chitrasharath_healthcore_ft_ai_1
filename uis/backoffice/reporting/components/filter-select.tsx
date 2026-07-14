"use client";

type Props = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  allLabel: string;
};

const selectClass =
  "w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800";

export const FilterSelect = ({ label, value, onChange, options, allLabel }: Props) => (
  <label className="space-y-1 text-sm">
    <span className="font-medium text-slate-700">{label}</span>
    <select className={selectClass} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{allLabel}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  </label>
);
