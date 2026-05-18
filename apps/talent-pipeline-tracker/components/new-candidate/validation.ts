export type NewCandidateErrors = {
  fullName?: string;
  email?: string;
  phone?: string;
  position?: string;
  linkedinUrl?: string;
  cvUrl?: string;
  experienceYears?: string;
};

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const phoneRegex = /^\+?[0-9\s()\-]{7,}$/;

const validUrl = (value: string) => {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
};

export const validateCandidate = (form: {
  fullName: string;
  email: string;
  phone: string;
  position: string;
  linkedinUrl: string;
  cvUrl: string;
  experienceYears: number;
}) => {
  const errors: NewCandidateErrors = {};
  if (form.fullName.trim().length < 2) errors.fullName = "Enter a full name with at least 2 characters.";
  if (!emailRegex.test(form.email.trim())) errors.email = "Enter a valid email address.";
  if (!phoneRegex.test(form.phone.trim())) errors.phone = "Enter a valid phone number with country code.";
  if (form.position.trim().length < 2) errors.position = "Enter the role or position applied for.";
  if (form.linkedinUrl.trim() && !validUrl(form.linkedinUrl.trim())) errors.linkedinUrl = "LinkedIn URL must start with http:// or https://.";
  if (form.cvUrl.trim() && !validUrl(form.cvUrl.trim())) errors.cvUrl = "CV URL must start with http:// or https://.";
  if (form.experienceYears < 0) errors.experienceYears = "Experience years cannot be negative.";
  return errors;
};