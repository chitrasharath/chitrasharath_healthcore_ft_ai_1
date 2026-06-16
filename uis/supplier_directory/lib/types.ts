export type Supplier = {
  id: number;
  name: string;
  country: "USA" | "UK";
  categories: string[];
  monthly_rate: number;
  currency: "USD" | "GBP";
  rate_updated_at: string;
  status: "active" | "suspended";
  compliance_agreement: string | null;
  contract_renewal_date: string | null;
  contact_email: string | null;
  notes: string | null;
};

export type SupplierCreateInput = {
  name: string;
  country: "USA" | "UK";
  categories: string[];
  monthly_rate: number;
  currency: "USD" | "GBP";
  status: "active" | "suspended";
  compliance_agreement?: string | null;
  contract_renewal_date?: string | null;
  contact_email?: string | null;
  notes?: string | null;
};
