import type { Supplier, SupplierCreateInput } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  const url = `${API_URL}/api/v1/suppliers${query ? `?${query}` : ""}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<Supplier[]>;
};

export const createSupplier = async (body: SupplierCreateInput): Promise<Supplier> => {
  const response = await fetch(`${API_URL}/api/v1/suppliers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<Supplier>;
};

export const updateSupplierRate = async (id: number, monthlyRate: number): Promise<Supplier> => {
  const response = await fetch(`${API_URL}/api/v1/suppliers/${id}/rate`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ monthly_rate: monthlyRate }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<Supplier>;
};

export const updateSupplierStatus = async (
  id: number,
  status: "active" | "suspended",
): Promise<Supplier> => {
  const response = await fetch(`${API_URL}/api/v1/suppliers/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<Supplier>;
};
