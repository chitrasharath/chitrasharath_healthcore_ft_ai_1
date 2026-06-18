"use client";

import { FormField, inputClass, invalidAttrs } from "@/components/enquiry/form-field";
import type { EnquiryFormApi } from "@/hooks/use-enquiry-form";
import { useLanguage } from "@/lib/i18n/language-context";

type Props = { form: EnquiryFormApi };

const FieldError = ({ id, message }: { id: string; message?: string }) =>
  message ? (
    <p id={id} className="mt-1 text-sm font-medium text-red-700" role="alert" aria-live="polite">
      {message}
    </p>
  ) : null;

export const PatientStatusFieldset = ({ form }: Props) => {
  const { t } = useLanguage();
  const { values, errors, showPatientId, showInsuranceFields, onBlur, onChange } = form;
  const radioLabel = "inline-flex items-center gap-2 text-sm text-slate-700";
  const yesNo = (name: string, value: string, onPick: (v: string) => void, invalid?: boolean) => (
    <div className="mt-2 flex flex-wrap gap-4">
      {(["Yes", "No"] as const).map((v) => (
        <label key={v} className={radioLabel}>
          <input type="radio" name={name} className="h-4 w-4" value={v} checked={value === v} onChange={() => onPick(v)} {...(invalid ? { "aria-invalid": true as const } : {})} />
          <span>{t(v === "Yes" ? "yes" : "no")}</span>
        </label>
      ))}
    </div>
  );

  return (
    <fieldset className="space-y-4 rounded-xl border border-slate-200 p-4 sm:p-5">
      <legend className="px-2 text-lg font-semibold text-slate-900">{t("coverageLegend")}</legend>
      <div>
        <p className="text-sm font-semibold text-slate-800">{t("newPatientQuestion")}</p>
        {yesNo("new_patient", values.new_patient, (v) => onChange("new_patient", v), Boolean(errors.new_patient))}
        <FieldError id="new_patient_error" message={errors.new_patient} />
      </div>
      {showPatientId ? (
        <FormField id="patient_id" label={t("patientIdLabel")} error={errors.patient_id}>
          <input id="patient_id" name="patient_id" type="text" placeholder="HC-A3F291" className={inputClass} value={values.patient_id} onBlur={() => onBlur("patient_id")} onChange={(e) => onChange("patient_id", e.target.value)} {...invalidAttrs(errors.patient_id)} />
        </FormField>
      ) : null}
      <div>
        <p className="text-sm font-semibold text-slate-800">{t("insuranceQuestion")}</p>
        {yesNo("has_insurance", values.has_insurance, (v) => onChange("has_insurance", v), Boolean(errors.has_insurance))}
        <FieldError id="has_insurance_error" message={errors.has_insurance} />
      </div>
      {showInsuranceFields ? (
        <div className="grid gap-4 md:grid-cols-2">
          <FormField id="insurance_provider" label={t("insuranceProviderLabel")} error={errors.insurance_provider}>
            <input id="insurance_provider" name="insurance_provider" type="text" maxLength={100} className={inputClass} value={values.insurance_provider} onBlur={() => onBlur("insurance_provider")} onChange={(e) => onChange("insurance_provider", e.target.value)} {...invalidAttrs(errors.insurance_provider)} />
          </FormField>
          <FormField id="insurance_member_id" label={t("memberIdLabel")} error={errors.insurance_member_id}>
            <input id="insurance_member_id" name="insurance_member_id" type="text" className={inputClass} value={values.insurance_member_id} onBlur={() => onBlur("insurance_member_id")} onChange={(e) => onChange("insurance_member_id", e.target.value)} {...invalidAttrs(errors.insurance_member_id)} />
          </FormField>
        </div>
      ) : null}
    </fieldset>
  );
};
