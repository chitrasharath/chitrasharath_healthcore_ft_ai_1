import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { apiFetch } from "@/lib/api";

export type ResetPasswordFieldErrors = {
  newPassword?: string;
  confirmPassword?: string;
  form?: string;
};

const validateClient = (newPassword: string, confirmPassword: string) => {
  const errors: ResetPasswordFieldErrors = {};
  if (!newPassword) errors.newPassword = "New password is required.";
  else if (newPassword.length < 8) errors.newPassword = "Password must be at least 8 characters.";
  if (!confirmPassword) errors.confirmPassword = "Please confirm your new password.";
  else if (newPassword !== confirmPassword) errors.confirmPassword = "Passwords do not match.";
  return errors;
};

export const useResetPasswordForm = (token: string | null) => {
  const router = useRouter();
  const [fieldErrors, setFieldErrors] = useState<ResetPasswordFieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;

    const form = new FormData(event.currentTarget);
    const newPassword = String(form.get("newPassword") ?? "");
    const confirmPassword = String(form.get("confirmPassword") ?? "");
    const clientErrors = validateClient(newPassword, confirmPassword);
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      return;
    }

    setFieldErrors({});
    setSubmitting(true);

    try {
      const response = await apiFetch("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: newPassword }),
      });
      if (response.status === 400) {
        setFieldErrors({
          form: "This reset link has expired or is invalid.",
        });
        return;
      }
      if (!response.ok) {
        setFieldErrors({ form: "Something went wrong. Please try again." });
        return;
      }
      router.push("/login?reset=success");
    } catch {
      setFieldErrors({ form: "Something went wrong. Please try again." });
    } finally {
      setSubmitting(false);
    }
  };

  return { fieldErrors, submitting, handleSubmit };
};
