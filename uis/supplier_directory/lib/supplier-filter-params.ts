import { VALID_CATEGORIES, type Category } from "@backoffice/supplier-directory/lib/categories";

export type CountryFilter = "all" | "USA" | "UK";

export type SupplierFilterState = {
  countryFilter: CountryFilter;
  categoryFilter: string;
};

const SUPPLIER_DIRECTORY_HOME = "/supplier-directory";

const isCountryFilter = (value: string): value is "USA" | "UK" =>
  value === "USA" || value === "UK";

export const parseSupplierFilters = (searchParams: URLSearchParams): SupplierFilterState => {
  const countryRaw = searchParams.get("country");
  const countryFilter: CountryFilter =
    countryRaw && isCountryFilter(countryRaw) ? countryRaw : "all";

  const categoryRaw = searchParams.get("category");
  const categoryFilter =
    categoryRaw && VALID_CATEGORIES.includes(categoryRaw as Category) ? categoryRaw : "all";

  return { countryFilter, categoryFilter };
};

export const applySupplierFilters = (
  searchParams: URLSearchParams,
  updates: Partial<SupplierFilterState>,
): URLSearchParams => {
  const current = parseSupplierFilters(searchParams);
  const merged = { ...current, ...updates };
  const next = new URLSearchParams(searchParams.toString());

  if (merged.countryFilter === "all") next.delete("country");
  else next.set("country", merged.countryFilter);

  if (merged.categoryFilter === "all") next.delete("category");
  else next.set("category", merged.categoryFilter);

  next.delete("api");

  return next;
};

export const filterListQuery = (searchParams: URLSearchParams): string => {
  const { countryFilter, categoryFilter } = parseSupplierFilters(searchParams);
  const params = new URLSearchParams();
  if (countryFilter !== "all") params.set("country", countryFilter);
  if (categoryFilter !== "all") params.set("category", categoryFilter);
  return params.toString();
};

export const supplierListPath = (searchParams: URLSearchParams): string => {
  const query = filterListQuery(searchParams);
  return query ? `${SUPPLIER_DIRECTORY_HOME}?${query}` : SUPPLIER_DIRECTORY_HOME;
};

export const supplierDetailPath = (id: number, listQuery: string): string => {
  if (!listQuery) return `${SUPPLIER_DIRECTORY_HOME}/suppliers/${id}`;
  return `${SUPPLIER_DIRECTORY_HOME}/suppliers/${id}?return=${encodeURIComponent(listQuery)}`;
};

export const supplierListPathFromReturn = (returnQuery: string | null): string => {
  if (!returnQuery) return SUPPLIER_DIRECTORY_HOME;
  const params = new URLSearchParams(returnQuery);
  params.delete("api");
  const query = params.toString();
  return query ? `${SUPPLIER_DIRECTORY_HOME}?${query}` : SUPPLIER_DIRECTORY_HOME;
};
