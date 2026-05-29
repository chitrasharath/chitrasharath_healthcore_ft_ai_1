"use client";

import { FormField, inputClass, invalidAttrs } from "@/components/enquiry/form-field";
import type { EnquiryFormApi } from "@/hooks/use-enquiry-form";
import { US_CLINICS } from "@/lib/clinics";
import { SERVICE_OPTIONS, TIME_OPTIONS } from "@/lib/enquiry-form-options";
import { useLanguage } from "@/lib/i18n/language-context";

type Props = { form: EnquiryFormApi };

export const AppointmentPreferencesFieldset = ({ form }: Props) => {
  const { t } = useLanguage();
  const { values, errors, dateLocale, onChange } = form;

  return (
    <fieldset className="space-y-4 rounded-xl border border-slate-200 p-4 sm:p-5">
      <legend className="px-2 text-lg font-semibold text-slate-900">{t("visitLegend")}</legend>
      <div className="grid gap-4 md:grid-cols-2">
        <FormField id="preferred_language" label={t("preferredLanguageLabel")} error={errors.preferred_language}>
          <select id="preferred_language" name="preferred_language" required className={inputClass} value={values.preferred_language} onChange={(e) => onChange("preferred_language", e.target.value)} {...invalidAttrs(errors.preferred_language)}>
            <option value="">{t("selectOption")}</option>
            <option value="English">{t("langEnglish")}</option>
            <option value="Spanish">{t("langSpanish")}</option>
          </select>
        </FormField>
        <FormField id="preferred_clinic" label={t("preferredClinicLabel")} error={errors.preferred_clinic}>
          <select id="preferred_clinic" name="preferred_clinic" required className={inputClass} value={values.preferred_clinic} onChange={(e) => onChange("preferred_clinic", e.target.value)} {...invalidAttrs(errors.preferred_clinic)}>
            <option value="">{t("selectOption")}</option>
            {US_CLINICS.map((c) => (
              <option key={c.name} value={c.name}>{c.name}</option>
            ))}
          </select>
        </FormField>
        <FormField id="preferred_date" label={t("preferredDateLabel")} error={errors.preferred_date}>
          <input id="preferred_date" name="preferred_date" type="date" required className={inputClass} value={values.preferred_date} onChange={(e) => onChange("preferred_date", e.target.value)} lang={dateLocale.lang} placeholder={dateLocale.placeholder} title={dateLocale.title} {...invalidAttrs(errors.preferred_date)} />
        </FormField>
        <FormField id="preferred_time" label={t("preferredTimeLabel")} error={errors.preferred_time}>
          <select id="preferred_time" name="preferred_time" required className={inputClass} value={values.preferred_time} onChange={(e) => onChange("preferred_time", e.target.value)} {...invalidAttrs(errors.preferred_time)}>
            <option value="">{t("selectOption")}</option>
            {TIME_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{t(opt.key)}</option>
            ))}
          </select>
        </FormField>
        <div className="md:col-span-2">
          <FormField id="service_type" label={t("serviceTypeLabel")} error={errors.service_type}>
            <select id="service_type" name="service_type" required className={inputClass} value={values.service_type} onChange={(e) => onChange("service_type", e.target.value)} {...invalidAttrs(errors.service_type)}>
              <option value="">{t("selectOption")}</option>
              {SERVICE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{t(opt.key)}</option>
              ))}
            </select>
          </FormField>
        </div>
      </div>
    </fieldset>
  );
};
