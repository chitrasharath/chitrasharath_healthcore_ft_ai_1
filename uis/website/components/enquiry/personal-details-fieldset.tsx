"use client";

import { FormField, inputClass, invalidAttrs } from "@/components/enquiry/form-field";
import type { EnquiryFormApi } from "@/hooks/use-enquiry-form";
import { useLanguage } from "@/lib/i18n/language-context";

type Props = { form: EnquiryFormApi };

export const PersonalDetailsFieldset = ({ form }: Props) => {
  const { t } = useLanguage();
  const { values, errors, dateLocale, firstNameRef, onBlur, onChange } = form;
  const dateAttrs = { lang: dateLocale.lang, placeholder: dateLocale.placeholder, title: dateLocale.title };

  return (
    <fieldset className="space-y-4 rounded-xl border border-slate-200 p-4 sm:p-5">
      <legend className="px-2 text-lg font-semibold text-slate-900">{t("personalLegend")}</legend>
      <div className="grid gap-4 md:grid-cols-2">
        <FormField id="first_name" label={t("firstNameLabel")} error={errors.first_name}>
          <input ref={firstNameRef} id="first_name" name="first_name" type="text" required minLength={2} maxLength={50} autoComplete="given-name" className={inputClass} value={values.first_name} onBlur={() => onBlur("first_name")} onChange={(e) => onChange("first_name", e.target.value)} {...invalidAttrs(errors.first_name)} />
        </FormField>
        <FormField id="last_name" label={t("lastNameLabel")} error={errors.last_name}>
          <input id="last_name" name="last_name" type="text" required minLength={2} maxLength={50} autoComplete="family-name" className={inputClass} value={values.last_name} onBlur={() => onBlur("last_name")} onChange={(e) => onChange("last_name", e.target.value)} {...invalidAttrs(errors.last_name)} />
        </FormField>
        <FormField id="date_of_birth" label={t("dobLabel")} error={errors.date_of_birth}>
          <input id="date_of_birth" name="date_of_birth" type="date" required className={inputClass} value={values.date_of_birth} onChange={(e) => onChange("date_of_birth", e.target.value)} {...dateAttrs} {...invalidAttrs(errors.date_of_birth)} />
        </FormField>
        <FormField id="email" label={t("emailLabel")} error={errors.email}>
          <input id="email" name="email" type="email" required autoComplete="email" className={inputClass} value={values.email} onBlur={() => onBlur("email")} onChange={(e) => onChange("email", e.target.value)} {...invalidAttrs(errors.email)} />
        </FormField>
        <div className="md:col-span-2">
          <FormField id="phone" label={t("phoneLabel")} error={errors.phone}>
            <input id="phone" name="phone" type="tel" required placeholder="+1 305 555 0191" autoComplete="tel" className={inputClass} value={values.phone} onBlur={() => onBlur("phone")} onChange={(e) => onChange("phone", e.target.value)} {...invalidAttrs(errors.phone)} />
          </FormField>
        </div>
      </div>
    </fieldset>
  );
};
