import { useState, type FormEvent } from "react";

import { apiFetch } from "@/lib/api";

export const FORGOT_PASSWORD_CONFIRMATION =
  "If that address is registered, you'll receive a link shortly.";

export const useForgotPasswordForm = () => {
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitted) return;

    setSubmitting(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");

    try {
      await apiFetch("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
    } catch {
      // Always show privacy-safe confirmation regardless of outcome.
    } finally {
      setSubmitting(false);
      setSubmitted(true);
    }
  };

  return { submitted, submitting, handleSubmit };
};
