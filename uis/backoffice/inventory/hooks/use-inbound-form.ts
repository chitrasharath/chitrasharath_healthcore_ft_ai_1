"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  emptyInbound,
  loadInboundProducts,
  submitInboundOrder,
} from "@backoffice/inventory/lib/inbound-form-logic";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";

export const useInboundForm = () => {
  const searchParams = useSearchParams();
  const [products, setProducts] = useState<MedicalSupply[]>([]);
  const [fields, setFields] = useState(emptyInbound);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    void loadInboundProducts(searchParams.get("supplyId"))
      .then(({ products: data, supplyId }) => {
        setProducts(data);
        if (supplyId) setFields((current) => ({ ...current, supplyId }));
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load supplies");
      })
      .finally(() => setLoadingProducts(false));
  }, [searchParams]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await submitInboundOrder(fields, products);
      setFields(emptyInbound());
      setSuccess("Delivery logged successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log delivery");
    } finally {
      setSaving(false);
    }
  };

  return {
    products,
    ...fields,
    setSupplyId: (value: number | null) => setFields((c) => ({ ...c, supplyId: value })),
    setQuantity: (value: string) => setFields((c) => ({ ...c, quantity: value })),
    setVendor: (value: string) => setFields((c) => ({ ...c, vendor: value })),
    setClinicId: (value: number) => setFields((c) => ({ ...c, clinicId: value })),
    loadingProducts,
    saving,
    error,
    success,
    handleSubmit,
  };
};
