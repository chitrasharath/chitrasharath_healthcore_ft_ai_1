import { CLINICS, CONSUMPTION_TYPES } from "@backoffice/inventory/lib/constants";
import { FORM_INPUT_CLASS, FORM_LABEL_CLASS } from "@backoffice/inventory/lib/form-helpers";

type OutboundMetaFieldsProps = {
  consumptionType: string;
  onConsumptionTypeChange: (value: string) => void;
  clinicId: number;
  onClinicIdChange: (value: number) => void;
  disabled?: boolean;
};

export const OutboundMetaFields = ({
  consumptionType,
  onConsumptionTypeChange,
  clinicId,
  onClinicIdChange,
  disabled,
}: OutboundMetaFieldsProps) => (
  <>
    <label className="block space-y-1">
      <span className={FORM_LABEL_CLASS}>Consumption Type</span>
      <select
        required
        disabled={disabled}
        value={consumptionType}
        onChange={(e) => onConsumptionTypeChange(e.target.value)}
        className={FORM_INPUT_CLASS}
      >
        {CONSUMPTION_TYPES.map((type) => (
          <option key={type.value} value={type.value}>
            {type.label}
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
