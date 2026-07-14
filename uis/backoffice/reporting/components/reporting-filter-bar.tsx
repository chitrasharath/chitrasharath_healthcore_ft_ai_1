"use client";

import { FilterSelect } from "@backoffice/reporting/components/filter-select";
import { formatClinicName, formatSupplyName } from "@backoffice/reporting/lib/display-names";
import type { ReportFilters } from "@backoffice/reporting/lib/report-filters";
import { lastTwelveMonthKeys } from "@backoffice/reporting/lib/report-window";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

type Props = {
  filters: ReportFilters;
  jurisdictions: string[];
  clinics: number[];
  supplies: number[];
  supplyNames: Record<number, string>;
  showSupply?: boolean;
};

export const ReportingFilterBar = ({
  filters,
  jurisdictions,
  clinics,
  supplies,
  supplyNames,
  showSupply = true,
}: Props) => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams.toString());
    if (!value) next.delete(key);
    else next.set(key, value);
    if (key === "jurisdiction") next.delete("clinic");
    router.replace(`${pathname}?${next.toString()}`);
  };

  return (
    <div className="rounded-xl border border-sky-100 bg-sky-50/60 p-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <FilterSelect
          label="Month"
          value={filters.month ?? ""}
          onChange={(value) => setParam("month", value)}
          allLabel="Last 12 months"
          options={lastTwelveMonthKeys().map((month) => ({ value: month, label: month }))}
        />
        <FilterSelect
          label="Jurisdiction"
          value={filters.jurisdiction ?? ""}
          onChange={(value) => setParam("jurisdiction", value)}
          allLabel="All jurisdictions"
          options={jurisdictions.map((j) => ({ value: j, label: j.toUpperCase() }))}
        />
        <FilterSelect
          label="Clinic"
          value={filters.clinicId === null ? "" : String(filters.clinicId)}
          onChange={(value) => setParam("clinic", value)}
          allLabel="All clinics"
          options={clinics.map((id) => ({ value: String(id), label: formatClinicName(id) }))}
        />
        {showSupply ? (
          <FilterSelect
            label="Supply"
            value={filters.supplyId === null ? "" : String(filters.supplyId)}
            onChange={(value) => setParam("supply", value)}
            allLabel="All supplies"
            options={supplies.map((id) => ({
              value: String(id),
              label: formatSupplyName(id, supplyNames),
            }))}
          />
        ) : null}
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Filters apply across tabs. Auth respects month only; supply applies to stock failures.
      </p>
    </div>
  );
};
