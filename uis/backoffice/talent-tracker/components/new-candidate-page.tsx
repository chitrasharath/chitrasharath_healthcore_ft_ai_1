"use client";

import { useSearchParams } from "next/navigation";

import { NewCandidateFields } from "@backoffice/talent-tracker/components/new-candidate/new-candidate-fields";
import { SaveCandidateBar } from "@backoffice/talent-tracker/components/new-candidate/save-candidate-bar";
import { useNewCandidateForm } from "@backoffice/talent-tracker/components/new-candidate/use-new-candidate-form";
import { PageHeader } from "@backoffice/talent-tracker/components/page-header";
import { TALENT_TRACKER_HOME } from "@backoffice/talent-tracker/lib/paths";

export const NewCandidatePageClient = () => {
  const searchParams = useSearchParams();
  const source = searchParams.get("source");
  const returnTo = searchParams.get("returnTo") || TALENT_TRACKER_HOME;
  const sourceLabel = source === "referral" ? "Referral" : "Direct";
  const { form, submitting, showSuccessModal, message, errors, setField, submit, acknowledgeSuccess } = useNewCandidateForm(returnTo);

  return (
    <>
      <PageHeader title="New Candidate" subtitle="Registration form" backHref={returnTo} />
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {source === "referral" ? <p className="rounded-md border border-sky-200 bg-sky-50 p-3 text-sm text-[var(--hc-brand-strong)]">Referral path active. Source mode is for intake context only and is not persisted by the API.</p> : null}

        <section className="rounded-xl border border-[var(--hc-border)] bg-white p-4">
          <NewCandidateFields
            sourceLabel={sourceLabel}
            fullName={form.fullName}
            email={form.email}
            phone={form.phone}
            position={form.position}
            linkedinUrl={form.linkedinUrl}
            cvUrl={form.cvUrl}
            experienceYears={form.experienceYears}
            errors={errors}
            onFullNameChange={(value) => setField("fullName", value)}
            onEmailChange={(value) => setField("email", value)}
            onPhoneChange={(value) => setField("phone", value)}
            onPositionChange={(value) => setField("position", value)}
            onLinkedinUrlChange={(value) => setField("linkedinUrl", value)}
            onCvUrlChange={(value) => setField("cvUrl", value)}
            onExperienceYearsChange={(value) => setField("experienceYears", value)}
          />

          {message ? <p className="mt-2 text-sm text-[var(--hc-danger)]" role="alert">{message}</p> : null}
        </section>

        <SaveCandidateBar submitting={submitting} onSubmit={submit} />
      </main>

      {showSuccessModal ? (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-sm rounded-xl border border-[var(--hc-border)] bg-white p-5 shadow-lg">
            <h2 className="text-lg font-semibold text-[var(--hc-text)]">Candidate Saved</h2>
            <p className="mt-2 text-sm text-[var(--hc-text-muted)]">The candidate was saved successfully.</p>
            <button
              type="button"
              onClick={acknowledgeSuccess}
              className="mt-4 w-full rounded-md bg-[var(--hc-brand)] px-3 py-2 text-sm font-semibold text-white hover:bg-[var(--hc-brand-strong)]"
            >
              OK
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
};
