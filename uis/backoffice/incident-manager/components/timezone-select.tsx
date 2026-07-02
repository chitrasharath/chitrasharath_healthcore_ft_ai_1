import { DISPLAY_TIMEZONES } from "@backoffice/incident-manager/lib/timezones";

type TimezoneSelectProps = {
  value: string;
  onChange: (timezone: string) => void;
  id?: string;
};

const selectClassName =
  "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500";

export const TimezoneSelect = ({ value, onChange, id = "incident-timezone" }: TimezoneSelectProps) => (
  <label htmlFor={id} className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
    <span className="font-medium">Timezone</span>
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={selectClassName}
    >
      {DISPLAY_TIMEZONES.map((tz) => (
        <option key={tz.value} value={tz.value}>
          {tz.label}
        </option>
      ))}
    </select>
  </label>
);
