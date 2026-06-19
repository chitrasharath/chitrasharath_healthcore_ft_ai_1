import { useState, type FormEvent } from "react";

import { apiFetch } from "@/lib/api";

export const FORGOT_PASSWORD_CONFIRMATION =
  "If that address is registered, you'll receive a link shortly.";

export const useForgotPasswordForm = () => {
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitted) return;

    setSubmitting(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");

    try {
      const response = await apiFetch("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      if (!response.ok) {
        setError("Something went wrong. Please try again.");
        return;
      }
      setSubmitted(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return { submitted, submitting, error, handleSubmit };
};
