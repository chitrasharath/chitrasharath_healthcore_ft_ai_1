import { healthcoreFetch } from "@backoffice/shared/lib/healthcore-api";

import type {
  MedicalSupply,
  OrderRead,
  SupplyConsumptionCreate,
  SupplyDeliveryCreate,
} from "@backoffice/inventory/types/inventory";

const parseError = async (response: Response): Promise<string> => {
  const payload = (await response.json().catch(() => null)) as
    | { detail?: string | Array<{ msg?: string }>; message?: string }
    | null;
  if (payload?.detail) {
    if (typeof payload.detail === "string") return payload.detail;
    return payload.detail.map((item) => item.msg ?? "Validation error").join("; ");
  }
  if (payload?.message) return payload.message;
  return response.statusText || "Request failed";
};

const inventoryFetch = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await healthcoreFetch(path, init);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<T>;
};

export const listProducts = (): Promise<MedicalSupply[]> =>
  inventoryFetch<MedicalSupply[]>("/inventory/products");

export const getProduct = (id: number): Promise<MedicalSupply> =>
  inventoryFetch<MedicalSupply>(`/inventory/products/${id}`);

export const createInboundOrder = (body: SupplyDeliveryCreate): Promise<unknown> =>
  inventoryFetch("/inventory/orders/inbound", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const createOutboundOrder = (body: SupplyConsumptionCreate): Promise<unknown> =>
  inventoryFetch("/inventory/orders/outbound", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const listOrders = (): Promise<OrderRead[]> =>
  inventoryFetch<OrderRead[]>("/inventory/orders");
