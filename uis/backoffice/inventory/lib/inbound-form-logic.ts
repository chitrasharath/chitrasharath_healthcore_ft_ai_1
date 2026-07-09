import { createInboundOrder, listProducts } from "@backoffice/inventory/lib/inventory-api";
import { countryToJurisdiction } from "@backoffice/inventory/lib/jurisdiction";
import { VENDORS } from "@backoffice/inventory/lib/constants";
import { parseSupplyId } from "@backoffice/inventory/lib/form-helpers";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";
import { track } from "@backoffice/shared/lib/telemetry";

export const emptyInbound = () => ({
  supplyId: null as number | null,
  quantity: "",
  vendor: VENDORS[0],
  clinicId: 1,
});

export const loadInboundProducts = async (
  supplyIdParam: string | null,
): Promise<{ products: MedicalSupply[]; supplyId: number | null }> => {
  const products = await listProducts();
  const preselect = parseSupplyId(supplyIdParam);
  const supplyId = preselect && products.some((p) => p.id === preselect) ? preselect : null;
  return { products, supplyId };
};

export const submitInboundOrder = async (
  fields: ReturnType<typeof emptyInbound>,
  products: MedicalSupply[],
) => {
  if (!fields.supplyId) throw new Error("Please select a medical supply.");
  const qty = Number(fields.quantity);
  if (!Number.isInteger(qty) || qty < 1) throw new Error("Quantity must be a positive integer.");
  await createInboundOrder({
    supply_id: fields.supplyId,
    quantity: qty,
    vendor_name: fields.vendor,
    clinic_id: fields.clinicId,
  });
  const supply = products.find((product) => product.id === fields.supplyId);
  track("supply_delivery_created", {
    supply_id: fields.supplyId,
    quantity: qty,
    clinic_id: fields.clinicId,
    jurisdiction: countryToJurisdiction(supply?.country ?? "US"),
  });
};
