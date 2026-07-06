import { createOutboundOrder, listProducts } from "@backoffice/inventory/lib/inventory-api";
import { CONSUMPTION_TYPES } from "@backoffice/inventory/lib/constants";
import { isInsufficientStockError, parseSupplyId } from "@backoffice/inventory/lib/form-helpers";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";

export const emptyOutbound = () => ({
  supplyId: null as number | null,
  quantity: "",
  consumptionType: CONSUMPTION_TYPES[0].value,
  clinicId: 1,
});

export const loadOutboundProducts = async (
  supplyIdParam: string | null,
): Promise<{ products: MedicalSupply[]; supplyId: number | null }> => {
  const products = await listProducts();
  const preselect = parseSupplyId(supplyIdParam);
  const supplyId = preselect && products.some((p) => p.id === preselect) ? preselect : null;
  return { products, supplyId };
};

export const submitOutboundOrder = async (fields: ReturnType<typeof emptyOutbound>) => {
  if (!fields.supplyId) throw new Error("Please select a medical supply.");
  const qty = Number(fields.quantity);
  if (!Number.isInteger(qty) || qty < 1) throw new Error("Quantity must be a positive integer.");
  await createOutboundOrder({
    supply_id: fields.supplyId,
    quantity: qty,
    consumption_type: fields.consumptionType,
    clinic_id: fields.clinicId,
  });
};

export const classifyOutboundError = (err: unknown): { formError: string | null; quantityError: string | null } => {
  const message = err instanceof Error ? err.message : "Failed to log consumption";
  if (isInsufficientStockError(message)) return { formError: null, quantityError: message };
  return { formError: message, quantityError: null };
};
