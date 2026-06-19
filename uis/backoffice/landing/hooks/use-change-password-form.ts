import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { apiFetch, verifyCredentials, type UserProfile } from "@/lib/api";

export type ChangePasswordFieldErrors = {
  currentPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
  form?: string;
};

const validateClient = (currentPassword: string, newPassword: string, confirmPassword: string) => {
  const errors: ChangePasswordFieldErrors = {};
  if (!currentPassword) errors.currentPassword = "Current password is required.";
  if (!newPassword) errors.newPassword = "New password is required.";
  else if (newPassword.length < 8) errors.newPassword = "Password must be at least 8 characters.";
  if (!confirmPassword) errors.confirmPassword = "Please confirm your new password.";
  else if (newPassword !== confirmPassword) errors.confirmPassword = "Passwords do not match.";
  else if (newPassword === currentPassword) errors.newPassword = "New password must differ from current password.";
  return errors;
};

export const useChangePasswordForm = () => {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [fieldErrors, setFieldErrors] = useState<ChangePasswordFieldErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let active = true;

    const loadUser = async () => {
      try {
        const response = await apiFetch("/auth/me");
        if (!response.ok) return;
        const data = (await response.json()) as UserProfile;
        if (active) setUser(data);
      } finally {
        if (active) setLoading(false);
      }
    };

    void loadUser();
    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!user) return;

    const form = new FormData(event.currentTarget);
    const currentPassword = String(form.get("currentPassword") ?? "");
    const newPassword = String(form.get("newPassword") ?? "");
    const confirmPassword = String(form.get("confirmPassword") ?? "");
    const clientErrors = validateClient(currentPassword, newPassword, confirmPassword);
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      return;
    }

    setFieldErrors({});
    setSubmitting(true);
    setSuccess(false);

    const verifyResult = await verifyCredentials(user.email, currentPassword);
    if (verifyResult === "invalid") {
      setFieldErrors({ currentPassword: "Current password is incorrect." });
      setSubmitting(false);
      return;
    }
    if (verifyResult === "error") {
      setFieldErrors({ form: "Something went wrong. Please try again." });
      setSubmitting(false);
      return;
    }

    try {
      const response = await apiFetch(`/users/${user.id}`, {
        method: "PUT",
        body: JSON.stringify({ password: newPassword }),
      });
      if (!response.ok) {
        setFieldErrors({ form: "Something went wrong. Please try again." });
        return;
      }
      setSuccess(true);
      window.setTimeout(() => router.push("/account/profile"), 1200);
    } catch {
      setFieldErrors({ form: "Something went wrong. Please try again." });
    } finally {
      setSubmitting(false);
    }
  };

  return { loading, fieldErrors, submitting, success, handleSubmit };
};
