import { formatClinicName as inventoryClinicName } from "@backoffice/inventory/lib/format";
import { listProducts } from "@backoffice/inventory/lib/inventory-api";

export const formatClinicName = inventoryClinicName;

export const formatSupplyName = (
  supplyId: number,
  names: Record<number, string> | undefined,
): string => (names ?? {})[supplyId] ?? `Unknown supply (${supplyId})`;

export const loadSupplyNameMap = async (): Promise<Record<number, string>> => {
  const products = await listProducts();
  const map: Record<number, string> = {};
  for (const product of products) map[product.id] = product.name;
  return map;
};

export type NameLabels = {
  clinicName: (id: number) => string;
  supplyName: (id: number) => string;
};

export const defaultLabels = (supplyNames: Record<number, string> = {}): NameLabels => ({
  clinicName: formatClinicName,
  supplyName: (id) => formatSupplyName(id, supplyNames),
});
