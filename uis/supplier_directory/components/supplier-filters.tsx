import { ApiFilterToggle } from "@backoffice/supplier-directory/components/api-filter-toggle";
import { CATEGORY_LABELS, VALID_CATEGORIES } from "@backoffice/supplier-directory/lib/categories";

type SupplierFiltersProps = {
  countryFilter: "all" | "USA" | "UK";
  categoryFilter: string;
  apiFiltersEnabled: boolean;
  onCountryChange: (value: "all" | "USA" | "UK") => void;
  onCategoryChange: (value: string) => void;
  onApiFiltersToggle: () => void;
};

export const SupplierFilters = ({
  countryFilter,
  categoryFilter,
  apiFiltersEnabled,
  onCountryChange,
  onCategoryChange,
  onApiFiltersToggle,
}: SupplierFiltersProps) => (
  <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
    <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
      Country
      <select
        value={countryFilter}
        onChange={(e) => onCountryChange(e.target.value as "all" | "USA" | "UK")}
        className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
      >
        <option value="all">All</option>
        <option value="USA">USA</option>
        <option value="UK">UK</option>
      </select>
    </label>
    <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
      Category
      <select
        value={categoryFilter}
        onChange={(e) => onCategoryChange(e.target.value)}
        className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
      >
        <option value="all">All</option>
        {VALID_CATEGORIES.map((category) => (
          <option key={category} value={category}>
            {CATEGORY_LABELS[category]}
          </option>
        ))}
      </select>
    </label>
    <ApiFilterToggle enabled={apiFiltersEnabled} onToggle={onApiFiltersToggle} />
  </div>
);
