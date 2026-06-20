import { healthcoreFetch } from "@backoffice/shared/lib/healthcore-api";

import type { Supplier, SupplierCreateInput, SupplierDetailsInput } from "@backoffice/supplier-directory/lib/types";

const parseError = async (response: Response): Promise<string> => {
  const payload = (await response.json().catch(() => null)) as
    | { detail?: string | Array<{ msg?: string }> }
    | null;
  if (!payload?.detail) return "Request failed";
  if (typeof payload.detail === "string") return payload.detail;
  return payload.detail.map((item) => item.msg ?? "Validation error").join("; ");
};

export type ListSuppliersParams = {
  country?: "USA" | "UK";
  category?: string;
};

export const listSuppliers = async (params?: ListSuppliersParams): Promise<Supplier[]> => {
  const search = new URLSearchParams();
  if (params?.country) search.set("country", params.country);
  if (params?.category) search.set("category", params.category);
  const query = search.toString();
  const path = `/suppliers${query ? `?${query}` : ""}`;
  const response = await healthcoreFetch(path);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<Supplier[]>;
};

export const createSupplier = async (body: SupplierCreateInput): Promise<Supplier> => {
  const response = await healthcoreFetch("/suppliers", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<Supplier>;
};

export const getSupplier = async (id: number): Promise<Supplier> => {
  const response = await healthcoreFetch(`/suppliers/${id}`);
  if (response.status === 404) throw new Error("Supplier not found");
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<Supplier>;
};

export const updateSupplierDetails = async (
  id: number,
  body: SupplierDetailsInput,
): Promise<Supplier> => {
  const response = await healthcoreFetch(`/suppliers/${id}/details`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<Supplier>;
};

export const updateSupplierRate = async (id: number, monthlyRate: number): Promise<Supplier> => {
  const response = await healthcoreFetch(`/suppliers/${id}/rate`, {
    method: "PATCH",
    body: JSON.stringify({ monthly_rate: monthlyRate }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<Supplier>;
};

export const updateSupplierStatus = async (
  id: number,
  status: "active" | "suspended",
): Promise<Supplier> => {
  const response = await healthcoreFetch(`/suppliers/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<Supplier>;
};
