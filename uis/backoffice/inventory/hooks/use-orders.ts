"use client";

import { useEffect, useState } from "react";

import { listOrders } from "@backoffice/inventory/lib/inventory-api";
import type { OrderRead } from "@backoffice/inventory/types/inventory";

export const useOrders = () => {
  const [orders, setOrders] = useState<OrderRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    void listOrders()
      .then((data) => {
        if (active) setOrders(data);
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
