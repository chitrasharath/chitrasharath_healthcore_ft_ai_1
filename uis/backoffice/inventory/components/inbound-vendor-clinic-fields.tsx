import { CLINICS, VENDORS } from "@backoffice/inventory/lib/constants";
import { FORM_INPUT_CLASS, FORM_LABEL_CLASS } from "@backoffice/inventory/lib/form-helpers";

type VendorClinicFieldsProps = {
  vendor: string;
  onVendorChange: (value: string) => void;
  clinicId: number;
  onClinicIdChange: (value: number) => void;
  disabled?: boolean;
};

export const InboundVendorClinicFields = ({
  vendor,
  onVendorChange,
  clinicId,
  onClinicIdChange,
  disabled,
}: VendorClinicFieldsProps) => (
  <>
    <label className="block space-y-1">
      <span className={FORM_LABEL_CLASS}>Vendor</span>
      <select
        required
        disabled={disabled}
        value={vendor}
        onChange={(e) => onVendorChange(e.target.value)}
        className={FORM_INPUT_CLASS}
      >
        {VENDORS.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </label>
    <label className="block space-y-1">
      <span className={FORM_LABEL_CLASS}>Clinic</span>
      <select
        required
        disabled={disabled}
        value={clinicId}
        onChange={(e) => onClinicIdChange(Number(e.target.value))}
        className={FORM_INPUT_CLASS}
      >
        {CLINICS.map((clinic) => (
          <option key={clinic.id} value={clinic.id}>
            {clinic.name}
          </option>
        ))}
      </select>
    </label>
  </>
);
