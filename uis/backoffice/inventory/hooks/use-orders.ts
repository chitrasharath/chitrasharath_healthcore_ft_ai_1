"use client";

import { useEffect, useRef, useState } from "react";

import { listOrders } from "@backoffice/inventory/lib/inventory-api";
import type { OrderRead } from "@backoffice/inventory/types/inventory";
import { track } from "@backoffice/shared/lib/telemetry";

const LIST_VIEW_DEBOUNCE_MS = 30_000;

export const useOrders = () => {
  const [orders, setOrders] = useState<OrderRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const lastTrackedAtRef = useRef(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    void listOrders()
      .then((data) => {
        if (!active) return;
        setOrders(data);
        const now = Date.now();
        if (now - lastTrackedAtRef.current >= LIST_VIEW_DEBOUNCE_MS) {
          track("orders_list_viewed", { item_count: data.length });
          lastTrackedAtRef.current = now;
        }
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load orders");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { orders, loading, error };
};
