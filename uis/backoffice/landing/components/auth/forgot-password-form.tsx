"use client";

import Link from "next/link";

import { AuthFormCard } from "@/components/auth/auth-form-card";
import { AUTH_INPUT_CLASS } from "@/hooks/use-login-form";
import { FORGOT_PASSWORD_CONFIRMATION, useForgotPasswordForm } from "@/hooks/use-forgot-password-form";

export const ForgotPasswordForm = () => {
  const { submitted, submitting, handleSubmit } = useForgotPasswordForm();

  return (
    <AuthFormCard title="Forgot Password">
      {submitted ? (
        <p className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800" role="status">
          {FORGOT_PASSWORD_CONFIRMATION}
        </p>
      ) : (
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
              Email
            </label>
            <input id="email" name="email" type="email" required autoComplete="email" className={AUTH_INPUT_CLASS} />
          </div>
          <button
            type="submit"
            disabled={submitting || submitted}
            className="w-full rounded-lg bg-gradient-to-r from-sky-900 to-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {submitting ? "Sending…" : "Send Reset Link"}
          </button>
        </form>
      )}
      <p className="mt-6 text-center text-sm text-slate-600">
        <Link href="/login" className="font-medium text-sky-700 hover:text-sky-900">
          Back to login
        </Link>
      </p>
    </AuthFormCard>
  );
};
