import { FORM_INPUT_CLASS, FORM_LABEL_CLASS } from "@backoffice/inventory/lib/form-helpers";

type OutboundQuantityFieldProps = {
  quantity: string;
  onQuantityChange: (value: string) => void;
  showStockWarning: boolean;
  stock: number | null;
  quantityError: string | null;
  disabled?: boolean;
};

export const OutboundQuantityField = ({
  quantity,
  onQuantityChange,
  showStockWarning,
  stock,
  quantityError,
  disabled,
}: OutboundQuantityFieldProps) => (
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
    {showStockWarning && stock !== null ? (
      <p className="mt-1 text-sm text-amber-800">
        Warning: quantity exceeds available stock ({stock})
      </p>
    ) : null}
    {quantityError ? <p className="mt-1 text-sm text-red-600">{quantityError}</p> : null}
  </label>
);
