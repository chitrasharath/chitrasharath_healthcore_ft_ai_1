import { OutboundMetaFields } from "@backoffice/inventory/components/outbound-meta-fields";
import { OutboundQuantityField } from "@backoffice/inventory/components/outbound-quantity-field";
import { OutboundSupplyField } from "@backoffice/inventory/components/outbound-supply-field";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";

type OutboundFormFieldsProps = {
  products: MedicalSupply[];
  supplyId: number | null;
  onSupplyIdChange: (id: number | null) => void;
  quantity: string;
  onQuantityChange: (value: string) => void;
  consumptionType: string;
  onConsumptionTypeChange: (value: string) => void;
  clinicId: number;
  onClinicIdChange: (value: number) => void;
  stock: number | null;
  unit: string;
  loadingStock: boolean;
  showStockWarning: boolean;
  quantityError: string | null;
  disabled?: boolean;
};

export const OutboundFormFieldsShell = (props: OutboundFormFieldsProps) => (
  <div className="space-y-4">
    <OutboundSupplyField
      products={props.products}
      supplyId={props.supplyId}
      onSupplyIdChange={props.onSupplyIdChange}
      stock={props.stock}
      unit={props.unit}
      loadingStock={props.loadingStock}
      disabled={props.disabled}
    />
    <OutboundQuantityField
      quantity={props.quantity}
      onQuantityChange={props.onQuantityChange}
      showStockWarning={props.showStockWarning}
      stock={props.stock}
      quantityError={props.quantityError}
      disabled={props.disabled}
    />
    <OutboundMetaFields
      consumptionType={props.consumptionType}
      onConsumptionTypeChange={props.onConsumptionTypeChange}
      clinicId={props.clinicId}
      onClinicIdChange={props.onClinicIdChange}
      disabled={props.disabled}
    />
  </div>
);
