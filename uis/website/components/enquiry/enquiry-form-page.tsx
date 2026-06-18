"use client";

import { AppointmentPreferencesFieldset } from "@/components/enquiry/appointment-preferences-fieldset";
import { EnquiryHeroSection } from "@/components/enquiry/enquiry-hero-section";
import { EveningWarning } from "@/components/enquiry/evening-warning";
import { HealthConcernFieldset } from "@/components/enquiry/health-concern-fieldset";
import { PersonalDetailsFieldset } from "@/components/enquiry/personal-details-fieldset";
import { PatientStatusFieldset } from "@/components/enquiry/patient-status-fieldset";
import { SuccessModal } from "@/components/enquiry/success-modal";
import { useEnquiryForm } from "@/hooks/use-enquiry-form";
import { useLanguage } from "@/lib/i18n/language-context";

export const EnquiryFormPage = () => {
  const { t } = useLanguage();
  const form = useEnquiryForm();

  return (
    <main id="main-content" className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8" role="main">
      <EnquiryHeroSection />
      <section className="mt-6 rounded-xl border border-slate-200 bg-slate-100 p-4" aria-label="Content quality and sources">
        <p className="text-sm font-semibold text-slate-800">{t("seoByline")}</p>
        <p className="mt-1 text-sm text-slate-700">{t("seoSources")}</p>
      </section>
      <section className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <EveningWarning visible={form.showEveningWarning} />
        <form
          id="patientEnquiryForm"
          noValidate
          className="space-y-8"
          aria-describedby="formGuidance"
          onSubmit={form.onSubmit}
        >
          <p id="formGuidance" className="text-sm text-slate-600">
            {t("requiredHint")}
          </p>
          <PersonalDetailsFieldset form={form} />
          <AppointmentPreferencesFieldset form={form} />
          <PatientStatusFieldset form={form} />
          <HealthConcernFieldset form={form} />
          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              className="rounded-md bg-sky-700 px-5 py-3 text-sm font-bold text-white transition hover:bg-sky-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
            >
              {t("submitBtn")}
            </button>
            <button
              type="button"
              onClick={form.onClear}
              className="rounded-md border border-slate-400 px-5 py-3 text-sm font-bold text-slate-700 transition hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-700"
            >
              {t("clearBtn")}
            </button>
          </div>
        </form>
      </section>
      <SuccessModal
        open={form.modalOpen}
        modalRef={form.modalRef}
        okBtnRef={form.okBtnRef}
        onClose={form.closeModal}
        onBackdropClick={form.onModalBackdropClick}
      />
    </main>
  );
};
