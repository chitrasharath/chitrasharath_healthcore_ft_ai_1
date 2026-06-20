import { FormField } from "@backoffice/talent-tracker/components/new-candidate/form-field";
import { SaveIcon } from "@backoffice/talent-tracker/components/icons";

type CandidateCorrectionFormProps = {
  fullName: string;
  email: string;
  phone: string;
  position: string;
  linkedinUrl: string;
  cvUrl: string;
  experienceYears: string;
  saving: boolean;
  onFullNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  onPositionChange: (value: string) => void;
  onLinkedinUrlChange: (value: string) => void;
  onCvUrlChange: (value: string) => void;
  onExperienceYearsChange: (value: string) => void;
  onSave: () => void;
};

export const CandidateCorrectionForm = ({
  fullName,
  email,
  phone,
  position,
  linkedinUrl,
  cvUrl,
  experienceYears,
  saving,
  onFullNameChange,
  onEmailChange,
  onPhoneChange,
  onPositionChange,
  onLinkedinUrlChange,
  onCvUrlChange,
  onExperienceYearsChange,
  onSave,
}: CandidateCorrectionFormProps) => {
  return (
    <section className="rounded-xl border border-[var(--hc-border)] bg-white p-4">
      <h2 className="mb-3 text-base font-semibold">Correct Candidate Data</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField id="editFullName" label="Full name" value={fullName} onChange={onFullNameChange} />
        <FormField id="editEmail" label="Email" value={email} onChange={onEmailChange} />
        <FormField id="editPhone" label="Phone" value={phone} onChange={onPhoneChange} />
        <FormField id="editPosition" label="Position" value={position} onChange={onPositionChange} />
        <FormField id="editLinkedinUrl" label="LinkedIn URL" value={linkedinUrl} onChange={onLinkedinUrlChange} />
        <FormField id="editCvUrl" label="CV URL" value={cvUrl} onChange={onCvUrlChange} />
        <FormField
          id="editExperienceYears"
          label="Experience years"
          type="number"
          min={0}
          value={experienceYears}
          onChange={onExperienceYearsChange}
        />
      </div>
      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        className="mt-4 inline-flex items-center gap-2 rounded-md border border-[var(--hc-border)] bg-white px-3 py-2 text-sm font-semibold disabled:opacity-50"
      >
        <SaveIcon className="h-4 w-4" />
        {saving ? "Saving..." : "Save Candidate Data"}
      </button>
    </section>
  );
};