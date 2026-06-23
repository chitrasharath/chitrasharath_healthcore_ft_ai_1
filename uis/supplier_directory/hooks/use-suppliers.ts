"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createSupplier,
  listSuppliers,
  updateSupplierRate,
  updateSupplierStatus,
} from "@backoffice/supplier-directory/lib/api";
import { readApiFilterMode, writeApiFilterMode } from "@backoffice/supplier-directory/lib/api-filter-mode";
import {
  applySupplierFilters,
  filterListQuery,
  parseSupplierFilters,
  supplierListPath,
  type CountryFilter,
} from "@backoffice/supplier-directory/lib/supplier-filter-params";
import type { Supplier, SupplierCreateInput } from "@backoffice/supplier-directory/lib/types";

let clientSuppliersCache: Supplier[] | null = null;

const matchesFilters = (
  supplier: Supplier,
  countryFilter: "all" | "USA" | "UK",
  categoryFilter: string,
) => {
  if (countryFilter !== "all" && supplier.country !== countryFilter) return false;
  if (categoryFilter !== "all" && !supplier.categories.includes(categoryFilter)) return false;
  return true;
};

const syncClientCache = (suppliers: Supplier[]) => {
  clientSuppliersCache = suppliers;
};

export const useSuppliers = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { countryFilter, categoryFilter } = useMemo(
    () => parseSupplierFilters(searchParams),
    [searchParams],
  );
  const listQuery = filterListQuery(searchParams);

  const [clientReady, setClientReady] = useState(false);
  const [apiFiltersEnabled, setApiFiltersEnabled] = useState(false);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hydratedRef = useRef(false);

  useEffect(() => {
    if (hydratedRef.current) return;
    hydratedRef.current = true;

    let apiMode = readApiFilterMode();
    if (searchParams.get("api") === "1") {
      apiMode = true;
      writeApiFilterMode(true);
      router.replace(supplierListPath(searchParams), { scroll: false });
    }

    setApiFiltersEnabled(apiMode);

    if (!apiMode && clientSuppliersCache) {
      setSuppliers(clientSuppliersCache);
      setLoading(false);
    }

    setClientReady(true);
  }, [router, searchParams]);

  const updateFilters = useCallback(
    (updates: Parameters<typeof applySupplierFilters>[1]) => {
      const next = applySupplierFilters(searchParams, updates);
      router.replace(supplierListPath(next), { scroll: false });
    },
    [router, searchParams],
  );

  const setCountryFilter = useCallback(
    (value: CountryFilter) => updateFilters({ countryFilter: value }),
    [updateFilters],
  );

  const setCategoryFilter = useCallback(
    (value: string) => updateFilters({ categoryFilter: value }),
    [updateFilters],
  );

  const toggleApiFilters = useCallback(() => {
    setApiFiltersEnabled((current) => {
      const next = !current;
      writeApiFilterMode(next);
      if (!next && clientSuppliersCache) {
        setSuppliers(clientSuppliersCache);
        setLoading(false);
        setError(null);
      }
      return next;
    });
  }, []);

  const replaceSupplier = useCallback((updated: Supplier) => {
    setSuppliers((current) => {
      const next = current.map((s) => (s.id === updated.id ? updated : s));
      syncClientCache(next);
      return next;
    });
  }, []);

  useEffect(() => {
    if (!clientReady || apiFiltersEnabled) return;
    if (clientSuppliersCache) return;

    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await listSuppliers();
        if (cancelled) return;
        syncClientCache(data);
        setSuppliers(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load suppliers");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [clientReady, apiFiltersEnabled]);

  useEffect(() => {
    if (!clientReady || !apiFiltersEnabled) return;

    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await listSuppliers({
          country: countryFilter === "all" ? undefined : countryFilter,
          category: categoryFilter === "all" ? undefined : categoryFilter,
        });
        if (!cancelled) setSuppliers(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load suppliers");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [clientReady, apiFiltersEnabled, countryFilter, categoryFilter]);

  const displayed = useMemo(() => {
    if (apiFiltersEnabled) return suppliers;
    return suppliers.filter((supplier) => matchesFilters(supplier, countryFilter, categoryFilter));
  }, [suppliers, apiFiltersEnabled, countryFilter, categoryFilter]);

  const addSupplier = async (input: SupplierCreateInput): Promise<void> => {
    const created = await createSupplier(input);
    if (apiFiltersEnabled) {
      const data = await listSuppliers({
        country: countryFilter === "all" ? undefined : countryFilter,
        category: categoryFilter === "all" ? undefined : categoryFilter,
      });
      setSuppliers(data);
      return;
    }
    setSuppliers((current) => {
      const next = [...current, created];
      syncClientCache(next);
      return next;
    });
  };

  const updateRate = async (id: number, monthlyRate: number) => {
    const updated = await updateSupplierRate(id, monthlyRate);
    replaceSupplier(updated);
  };

  const toggleStatus = async (supplier: Supplier) => {
    const next = supplier.status === "active" ? "suspended" : "active";
    const updated = await updateSupplierStatus(supplier.id, next);
    replaceSupplier(updated);
  };

  const reload = useCallback(async () => {
    if (apiFiltersEnabled) {
      setLoading(true);
      setError(null);
      try {
        const data = await listSuppliers({
          country: countryFilter === "all" ? undefined : countryFilter,
          category: categoryFilter === "all" ? undefined : categoryFilter,
        });
        setSuppliers(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load suppliers");
      } finally {
        setLoading(false);
      }
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await listSuppliers();
      syncClientCache(data);
      setSuppliers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load suppliers");
    } finally {
      setLoading(false);
    }
  }, [apiFiltersEnabled, countryFilter, categoryFilter]);

  return {
    clientReady,
    suppliers: displayed,
    loading,
    error,
    countryFilter,
    categoryFilter,
    apiFiltersEnabled,
    listQuery,
    setCountryFilter,
    setCategoryFilter,
    toggleApiFilters,
    addSupplier,
    updateRate,
    toggleStatus,
    reload,
  };
};
