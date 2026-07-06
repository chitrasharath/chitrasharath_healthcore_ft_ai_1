import { InboundSupplyQuantityFields } from "@backoffice/inventory/components/inbound-supply-quantity-fields";
import { InboundVendorClinicFields } from "@backoffice/inventory/components/inbound-vendor-clinic-fields";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";

type InboundFormFieldsProps = {
  products: MedicalSupply[];
  supplyId: number | null;
  onSupplyIdChange: (id: number | null) => void;
  quantity: string;
  onQuantityChange: (value: string) => void;
  vendor: string;
  onVendorChange: (value: string) => void;
  clinicId: number;
  onClinicIdChange: (value: number) => void;
  disabled?: boolean;
};

export const InboundFormFields = (props: InboundFormFieldsProps) => (
  <div className="space-y-4">
    <InboundSupplyQuantityFields
      products={props.products}
      supplyId={props.supplyId}
      onSupplyIdChange={props.onSupplyIdChange}
      quantity={props.quantity}
      onQuantityChange={props.onQuantityChange}
      disabled={props.disabled}
    />
    <InboundVendorClinicFields
      vendor={props.vendor}
      onVendorChange={props.onVendorChange}
      clinicId={props.clinicId}
      onClinicIdChange={props.onClinicIdChange}
      disabled={props.disabled}
    />
  </div>
);
