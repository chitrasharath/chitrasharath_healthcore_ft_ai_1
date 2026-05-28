import { useState } from "react";
import { useRouter } from "next/navigation";

import { createCandidate } from "@/lib/api";
import type { NewCandidateErrors } from "@/components/new-candidate/validation";
import { validateCandidate } from "@/components/new-candidate/validation";

type NewCandidateForm = {
  fullName: string;
  email: string;
  phone: string;
  position: string;
  linkedinUrl: string;
  cvUrl: string;
  experienceYears: string;
};

const initialForm: NewCandidateForm = {
  fullName: "",
  email: "",
  phone: "",
  position: "",
  linkedinUrl: "",
  cvUrl: "",
  experienceYears: "0",
};

export const useNewCandidateForm = (returnTo: string) => {
  const router = useRouter();
  const [form, setForm] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [message, setMessage] = useState("");
  const [errors, setErrors] = useState<NewCandidateErrors>({});

  const setField = <K extends keyof NewCandidateForm>(field: K, value: NewCandidateForm[K]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const submit = async () => {
    const nextErrors = validateCandidate(form);
    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      setMessage("Please fix the highlighted fields.");
      return;
    }

    setSubmitting(true);
    setMessage("");

    try {
      const experienceYears = Number.parseInt(form.experienceYears, 10);

      await createCandidate({
        full_name: form.fullName,
        email: form.email,
        phone: form.phone,
        position: form.position,
        linkedin_url: form.linkedinUrl || null,
        cv_url: form.cvUrl || null,
        experience_years: experienceYears,
      });
      setShowSuccessModal(true);
    } catch (submitError) {
      setMessage(
        submitError instanceof Error
          ? submitError.message
          : "Failed to create candidate.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const acknowledgeSuccess = () => {
    setShowSuccessModal(false);
    router.push(`${returnTo}${returnTo.includes("?") ? "&" : "?"}created=1`);
  };

  return { form, submitting, showSuccessModal, message, errors, setField, submit, acknowledgeSuccess };
};
