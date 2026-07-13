"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useOutboundAbandonTelemetry } from "@backoffice/inventory/hooks/use-outbound-abandon-telemetry";
import { useProductStock } from "@backoffice/inventory/hooks/use-product-stock";
import { countryToJurisdiction } from "@backoffice/inventory/lib/jurisdiction";
import {
  classifyOutboundError,
  emptyOutbound,
  loadOutboundProducts,
  submitOutboundOrder,
} from "@backoffice/inventory/lib/outbound-form-logic";
import { isInsufficientStockError } from "@backoffice/inventory/lib/form-helpers";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";
import { track } from "@backoffice/shared/lib/telemetry";

export const useOutboundForm = () => {
  const searchParams = useSearchParams();
  const [products, setProducts] = useState<MedicalSupply[]>([]);
  const [fields, setFields] = useState(emptyOutbound);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [quantityError, setQuantityError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const { stock, unit, loading: loadingStock } = useProductStock(fields.supplyId);

  useOutboundAbandonTelemetry(fields, products, submitted);

  useEffect(() => {
    void loadOutboundProducts(searchParams.get("supplyId"))
      .then(({ products: data, supplyId }) => {
        setProducts(data);
        if (supplyId) setFields((current) => ({ ...current, supplyId }));
      })
      .catch((err: unknown) => {
        setFormError(err instanceof Error ? err.message : "Failed to load supplies");
      })
      .finally(() => setLoadingProducts(false));
  }, [searchParams]);

  const qty = Number(fields.quantity);
  const showStockWarning =
    stock !== null && Number.isInteger(qty) && qty > 0 && qty > stock;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    setQuantityError(null);
    setSuccess(null);
    try {
      await submitOutboundOrder(fields, products);
      setSubmitted(true);
      setFields(emptyOutbound());
      setSuccess("Consumption logged successfully.");
    } catch (err) {
      const classified = classifyOutboundError(err);
      setFormError(classified.formError);
      setQuantityError(classified.quantityError);
      if (fields.supplyId) {
        const supply = products.find((product) => product.id === fields.supplyId);
        const message = err instanceof Error ? err.message : "";
        track("supply_consumption_failed", {
          error_code: isInsufficientStockError(message) ? "INSUFFICIENT_STOCK" : "VALIDATION_ERROR",
          supply_id: fields.supplyId,
          clinic_id: fields.clinicId,
          jurisdiction: countryToJurisdiction(supply?.country ?? "US"),
        });
      }
    } finally {
      setSaving(false);
    }
  };

  return {
    products,
    ...fields,
    setSupplyId: (value: number | null) => setFields((c) => ({ ...c, supplyId: value })),
    setQuantity: (value: string) => setFields((c) => ({ ...c, quantity: value })),
    setConsumptionType: (value: string) => setFields((c) => ({ ...c, consumptionType: value })),
    setClinicId: (value: number) => setFields((c) => ({ ...c, clinicId: value })),
    loadingProducts,
    loadingStock,
    stock,
    unit,
    showStockWarning,
    saving,
    formError,
    quantityError,
    success,
    handleSubmit,
  };
};
