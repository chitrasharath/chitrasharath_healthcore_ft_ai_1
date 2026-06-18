"use client";

import { FormField, inputClass, invalidAttrs } from "@/components/enquiry/form-field";
import type { EnquiryFormApi } from "@/hooks/use-enquiry-form";
import { useLanguage } from "@/lib/i18n/language-context";

type Props = { form: EnquiryFormApi };

export const HealthConcernFieldset = ({ form }: Props) => {
  const { t } = useLanguage();
  const { values, errors, concernLength, onBlur, onChange } = form;

  return (
    <fieldset className="space-y-4 rounded-xl border border-slate-200 p-4 sm:p-5">
      <legend className="px-2 text-lg font-semibold text-slate-900">{t("concernLegend")}</legend>
      <FormField
        id="health_concern"
        label={t("healthConcernLabel")}
        error={errors.health_concern}
        describedBy="health_concern_counter"
      >
        <textarea
          id="health_concern"
          name="health_concern"
          rows={5}
          minLength={20}
          maxLength={500}
          required
          className={inputClass}
          value={values.health_concern}
          onBlur={() => onBlur("health_concern")}
          onChange={(e) => onChange("health_concern", e.target.value)}
          {...invalidAttrs(errors.health_concern)}
        />
        <p id="health_concern_counter" className="mt-1 text-sm text-slate-600" aria-live="polite">
          {concernLength} / 500
        </p>
      </FormField>
      <div>
        <label className="inline-flex items-start gap-2 text-sm text-slate-700">
          <input
            id="contact_consent"
            name="contact_consent"
            type="checkbox"
            required
            className="mt-1 h-4 w-4"
            checked={values.contact_consent}
            onChange={(e) => onChange("contact_consent", e.target.checked)}
            {...invalidAttrs(errors.contact_consent)}
          />
          <span>{t("consentLabel")}</span>
        </label>
        {errors.contact_consent ? (
          <p id="contact_consent_error" className="mt-1 text-sm font-medium text-red-700" role="alert" aria-live="polite">
            {errors.contact_consent}
          </p>
        ) : null}
      </div>
    </fieldset>
  );
};
