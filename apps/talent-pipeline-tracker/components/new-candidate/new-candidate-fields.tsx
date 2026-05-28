import { FormField } from "@/components/new-candidate/form-field";

type NewCandidateFieldsProps = {
  sourceLabel: string;
  fullName: string;
  email: string;
  phone: string;
  position: string;
  linkedinUrl: string;
  cvUrl: string;
  experienceYears: string;
  errors: {
    fullName?: string;
    email?: string;
    phone?: string;
    position?: string;
    linkedinUrl?: string;
    cvUrl?: string;
    experienceYears?: string;
  };
  onFullNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  onPositionChange: (value: string) => void;
  onLinkedinUrlChange: (value: string) => void;
  onCvUrlChange: (value: string) => void;
  onExperienceYearsChange: (value: string) => void;
};

export const NewCandidateFields = ({
  sourceLabel,
  fullName,
  email,
  phone,
  position,
  linkedinUrl,
  cvUrl,
  experienceYears,
  errors,
  onFullNameChange,
  onEmailChange,
  onPhoneChange,
  onPositionChange,
  onLinkedinUrlChange,
  onCvUrlChange,
  onExperienceYearsChange,
}: NewCandidateFieldsProps) => {
  return (
    <div className="mt-4 grid gap-3 sm:grid-cols-2">
      <FormField id="fullName" label="Full name" value={fullName} placeholder="Ava Chen" error={errors.fullName} onChange={onFullNameChange} />
      <FormField id="email" label="Email" value={email} type="email" placeholder="ava.chen@example.com" error={errors.email} onChange={onEmailChange} />
      <FormField id="phone" label="Phone" value={phone} placeholder="+1 305 555 0191" error={errors.phone} onChange={onPhoneChange} />
      <FormField id="position" label="Position" value={position} placeholder="Frontend Engineer" error={errors.position} onChange={onPositionChange} />
      <FormField id="linkedinUrl" label="LinkedIn URL" value={linkedinUrl} placeholder="https://linkedin.com/in/ava-chen" error={errors.linkedinUrl} onChange={onLinkedinUrlChange} />
      <FormField id="cvUrl" label="CV URL" value={cvUrl} placeholder="https://example.com/cv.pdf" error={errors.cvUrl} onChange={onCvUrlChange} />
      <FormField id="experienceYears" label="Experience years" value={experienceYears} type="number" min={0} error={errors.experienceYears} onChange={onExperienceYearsChange} />
      <FormField id="status" label="Default status" value="received" readOnly />
      <FormField id="stage" label="Default stage" value="pending" readOnly />
      <FormField id="applicationDate" label="Application date" value={new Date().toISOString().slice(0, 10)} readOnly />
      <FormField id="sourceMode" label="Intake source mode" value={sourceLabel} readOnly />
    </div>
  );
};
