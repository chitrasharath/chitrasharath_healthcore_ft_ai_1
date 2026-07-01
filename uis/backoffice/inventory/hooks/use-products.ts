"use client";

import { useEffect, useState } from "react";

import { listProducts } from "@backoffice/inventory/lib/inventory-api";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";

export const useProducts = () => {
  const [products, setProducts] = useState<MedicalSupply[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    void listProducts()
      .then((data) => {
        if (active) setProducts(data);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load supplies");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { products, loading, error };
};
