"use client";

import { useCallback, useEffect, useState } from "react";

import {
  createSupplier,
  listSuppliers,
  updateSupplierRate,
  updateSupplierStatus,
} from "@/lib/api";
import type { Supplier, SupplierCreateInput } from "@/lib/types";

export const useSuppliers = () => {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [countryFilter, setCountryFilter] = useState<"all" | "USA" | "UK">("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSuppliers(
        await listSuppliers({
          country: countryFilter === "all" ? undefined : countryFilter,
          category: categoryFilter === "all" ? undefined : categoryFilter,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load suppliers");
    } finally {
      setLoading(false);
    }
  }, [countryFilter, categoryFilter]);

  useEffect(() => {
    // Refetch when filters change — server applies country/category query params.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const replaceSupplier = (updated: Supplier) => {
    setSuppliers((current) => current.map((s) => (s.id === updated.id ? updated : s)));
  };

  const addSupplier = async (input: SupplierCreateInput): Promise<void> => {
    await createSupplier(input);
    await load();
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

  return {
    suppliers,
    loading,
    error,
    countryFilter,
    categoryFilter,
    setCountryFilter,
    setCategoryFilter,
    addSupplier,
    updateRate,
    toggleStatus,
    reload: load,
  };
};
