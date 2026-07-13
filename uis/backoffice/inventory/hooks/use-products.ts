"use client";

import { useEffect, useRef, useState } from "react";

import { listProducts } from "@backoffice/inventory/lib/inventory-api";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";
import { track } from "@backoffice/shared/lib/telemetry";

const LIST_VIEW_DEBOUNCE_MS = 30_000;

export const useProducts = () => {
  const [products, setProducts] = useState<MedicalSupply[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const lastTrackedAtRef = useRef(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    void listProducts()
      .then((data) => {
        if (!active) return;
        setProducts(data);
        const now = Date.now();
        if (now - lastTrackedAtRef.current >= LIST_VIEW_DEBOUNCE_MS) {
          track("supply_list_viewed", { item_count: data.length });
          lastTrackedAtRef.current = now;
        }
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
