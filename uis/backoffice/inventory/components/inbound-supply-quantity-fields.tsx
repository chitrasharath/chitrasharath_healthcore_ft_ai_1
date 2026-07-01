import { FORM_INPUT_CLASS, FORM_LABEL_CLASS } from "@backoffice/inventory/lib/form-helpers";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";

type SupplyQuantityFieldsProps = {
  products: MedicalSupply[];
  supplyId: number | null;
  onSupplyIdChange: (id: number | null) => void;
  quantity: string;
  onQuantityChange: (value: string) => void;
  disabled?: boolean;
};

export const InboundSupplyQuantityFields = ({
  products,
  supplyId,
  onSupplyIdChange,
  quantity,
  onQuantityChange,
  disabled,
}: SupplyQuantityFieldsProps) => (
  <>
    <label className="block space-y-1">
      <span className={FORM_LABEL_CLASS}>Medical Supply</span>
      <select
        required
        disabled={disabled}
        value={supplyId ?? ""}
        onChange={(e) => onSupplyIdChange(e.target.value ? Number(e.target.value) : null)}
        className={FORM_INPUT_CLASS}
      >
        <option value="">Select a supply…</option>
        {products.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
    </label>
    <label className="block space-y-1">
      <span className={FORM_LABEL_CLASS}>Quantity</span>
      <input
        required
        type="number"
        min={1}
        disabled={disabled}
        value={quantity}
        onChange={(e) => onQuantityChange(e.target.value)}
        className={FORM_INPUT_CLASS}
      />
    </label>
  </>
);
