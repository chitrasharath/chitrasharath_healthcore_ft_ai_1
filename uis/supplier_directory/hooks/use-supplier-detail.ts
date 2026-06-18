"use client";

import { useCallback, useEffect, useState } from "react";

import { getSupplier, updateSupplierDetails } from "@/lib/api";
import type { Supplier, SupplierDetailsInput } from "@/lib/types";

export const useSupplierDetail = (supplierId: number) => {
  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSupplier(await getSupplier(supplierId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load supplier");
      setSupplier(null);
    } finally {
      setLoading(false);
    }
  }, [supplierId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const saveDetails = async (details: SupplierDetailsInput) => {
    const updated = await updateSupplierDetails(supplierId, details);
    setSupplier(updated);
    return updated;
  };

  return { supplier, loading, error, saveDetails, reload: load };
};
