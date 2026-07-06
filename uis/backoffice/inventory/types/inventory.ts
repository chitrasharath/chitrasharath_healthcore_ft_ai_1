export type MedicalSupply = {
  id: number;
  name: string;
  sku: string;
  category: string;
  unit: string;
  country: string;
  current_stock: number;
};

export type SupplyDeliveryCreate = {
  supply_id: number;
  quantity: number;
  vendor_name: string;
  clinic_id: number;
};

export type SupplyConsumptionCreate = {
  supply_id: number;
  quantity: number;
  consumption_type: string;
  clinic_id: number;
};

export type OrderRead = {
  id: number;
  order_type: "inbound" | "outbound";
  supply_id: number;
  supply_name: string;
  quantity: number;
  user_uuid: string;
  created_at: string;
  vendor_name: string | null;
  consumption_type: string | null;
  clinic_id: number;
};
