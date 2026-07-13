import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { apiFetch, fetchCurrentUser, NETWORK_ERROR_MESSAGE, type TokenResponse } from "@/lib/api";
import {
  initTelemetrySession,
  setTelemetryUserId,
  track,
} from "@backoffice/shared/lib/telemetry";

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
      initTelemetrySession(crypto.randomUUID());
      const user = await fetchCurrentUser();
      if (user) setTelemetryUserId(String(user.id));
      track("user_login_succeeded", {});
      router.push("/");
    } catch (err) {
      if (err instanceof Error && err.message === "Unauthorized") {
        track("user_login_failed", { reason: "invalid_credentials" });
        setError("Invalid email or password.");
        return;
      }
      if (err instanceof Error && err.message === NETWORK_ERROR_MESSAGE) {
        track("user_login_failed", { reason: "network_error" });
      }
      setError(
        err instanceof Error && err.message === NETWORK_ERROR_MESSAGE
          ? NETWORK_ERROR_MESSAGE
          : "Something went wrong. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return { error, submitting, handleSubmit };
};
