import { countryToJurisdiction } from "@backoffice/inventory/lib/jurisdiction";
import { emptyOutbound } from "@backoffice/inventory/lib/outbound-form-logic";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";
import { flush, track } from "@backoffice/shared/lib/telemetry";

export type OutboundFields = ReturnType<typeof emptyOutbound>;

const hasSupplySelected = (fields: OutboundFields): boolean => fields.supplyId !== null;
const hasQuantityEntered = (fields: OutboundFields): boolean => fields.quantity !== "";

/** Partial form: exactly one of supply or quantity filled, not both. */
export const isOutboundDirty = (fields: OutboundFields): boolean =>
  hasSupplySelected(fields) !== hasQuantityEntered(fields);

export const buildAbandonProperties = (
  fields: OutboundFields,
  products: MedicalSupply[],
  trigger: "navigation" | "tab_hidden",
): Record<string, unknown> => {
  const props: Record<string, unknown> = {
    clinic_id: fields.clinicId,
    had_supply_selected: fields.supplyId !== null,
    had_quantity: fields.quantity !== "",
    abandon_trigger: trigger,
  };
  if (fields.supplyId) {
    const supply = products.find((product) => product.id === fields.supplyId);
    if (supply) props.jurisdiction = countryToJurisdiction(supply.country);
  }
  return props;
};

export const trackOutboundAbandon = (
  fields: OutboundFields,
  products: MedicalSupply[],
  trigger: "navigation" | "tab_hidden",
): boolean => {
  if (!isOutboundDirty(fields)) return false;
  track("supply_consumption_form_abandoned", buildAbandonProperties(fields, products, trigger));
  void flush();
  return true;
};
