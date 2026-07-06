"use client";

import { useEffect, useState } from "react";

import { getProduct } from "@backoffice/inventory/lib/inventory-api";

export const useProductStock = (supplyId: number | null) => {
  const [stock, setStock] = useState<number | null>(null);
  const [unit, setUnit] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!supplyId) {
      setStock(null);
      setUnit("");
      setError(null);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);
    void getProduct(supplyId)
      .then((product) => {
        if (!active) return;
        setStock(product.current_stock);
        setUnit(product.unit);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setStock(null);
        setUnit("");
        setError(err instanceof Error ? err.message : "Failed to load stock");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [supplyId]);

  return { stock, unit, loading, error };
};
