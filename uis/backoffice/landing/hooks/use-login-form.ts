import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { apiFetch, type TokenResponse } from "@/lib/api";

export const AUTH_INPUT_CLASS =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:ring-1 focus:ring-sky-500";

export const useLoginForm = () => {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");

    try {
      const response = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        setError("Something went wrong. Please try again.");
        return;
      }
      const data = (await response.json()) as TokenResponse;
      localStorage.setItem("token", data.access_token);
      router.push("/");
    } catch (err) {
      setError(
        err instanceof Error && err.message === "Unauthorized"
          ? "Invalid email or password."
          : "Something went wrong. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return { error, submitting, handleSubmit };
};
