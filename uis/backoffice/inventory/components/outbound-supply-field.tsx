import { FORM_INPUT_CLASS, FORM_LABEL_CLASS, pluralUnit } from "@backoffice/inventory/lib/form-helpers";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";

type OutboundSupplyFieldProps = {
  products: MedicalSupply[];
  supplyId: number | null;
  onSupplyIdChange: (id: number | null) => void;
  stock: number | null;
  unit: string;
  loadingStock: boolean;
  disabled?: boolean;
};

export const OutboundSupplyField = ({
  products,
  supplyId,
  onSupplyIdChange,
  stock,
  unit,
  loadingStock,
  disabled,
}: OutboundSupplyFieldProps) => (
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
    {supplyId ? (
      <p className="text-sm font-medium text-slate-700">
        {loadingStock
          ? "Loading stock…"
          : stock !== null
            ? `Available stock: ${stock} ${pluralUnit(unit, stock)}`
            : "Stock unavailable"}
      </p>
    ) : null}
  </>
);
