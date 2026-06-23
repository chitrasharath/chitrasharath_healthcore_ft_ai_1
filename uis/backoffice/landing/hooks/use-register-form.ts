import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { apiFetch, type TokenResponse } from "@/lib/api";

export type RegisterFieldErrors = {
  name?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  form?: string;
};

type ValidationDetail = { loc: (string | number)[]; msg: string };

const parseApiErrors = (payload: { detail?: string | ValidationDetail[] }): RegisterFieldErrors => {
  if (typeof payload.detail === "string") {
    if (payload.detail === "Email already registered") return { email: payload.detail };
    return { form: payload.detail };
  }
  if (!Array.isArray(payload.detail)) return { form: "Something went wrong. Please try again." };
  const errors: RegisterFieldErrors = {};
  for (const item of payload.detail) {
    const field = String(item.loc[item.loc.length - 1] ?? "");
    if (field === "name" || field === "email" || field === "password") {
      errors[field] = item.msg;
    }
  }
  return errors;
};

const validateClient = (name: string, email: string, password: string, confirmPassword: string) => {
  const errors: RegisterFieldErrors = {};
  if (!name.trim()) errors.name = "Name is required.";
  if (!email.trim()) errors.email = "Email is required.";
  if (!password) errors.password = "Password is required.";
  else if (password.length < 8) errors.password = "Password must be at least 8 characters.";
  if (!confirmPassword) errors.confirmPassword = "Please confirm your password.";
  else if (password !== confirmPassword) errors.confirmPassword = "Passwords do not match.";
  return errors;
};

export const useRegisterForm = () => {
  const router = useRouter();
  const [fieldErrors, setFieldErrors] = useState<RegisterFieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "");
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    const confirmPassword = String(form.get("confirmPassword") ?? "");
    const clientErrors = validateClient(name, email, password, confirmPassword);
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      return;
    }

    setFieldErrors({});
    setSubmitting(true);
    try {
      const response = await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string | ValidationDetail[] };
        setFieldErrors(parseApiErrors(payload));
        return;
      }
      const data = (await response.json()) as TokenResponse;
      localStorage.setItem("token", data.access_token);
      router.push("/");
    } catch {
      setFieldErrors({ form: "Something went wrong. Please try again." });
    } finally {
      setSubmitting(false);
    }
  };

  return { fieldErrors, submitting, handleSubmit };
};
