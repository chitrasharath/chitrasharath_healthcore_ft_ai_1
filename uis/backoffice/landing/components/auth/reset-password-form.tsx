"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { AuthFormCard } from "@/components/auth/auth-form-card";
import { FieldError } from "@/components/auth/field-error";
import { PasswordInput } from "@/components/auth/password-input";
import { useResetPasswordForm } from "@/hooks/use-reset-password-form";

const ResetPasswordFormContent = () => {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const { fieldErrors, submitting, handleSubmit } = useResetPasswordForm(token);

  if (!token) {
    return (
      <AuthFormCard title="Reset Password">
        <p className="text-sm text-red-600" role="alert">
          Invalid reset link.
        </p>
        <p className="mt-4 text-sm">
          <Link href="/forgot-password" className="font-medium text-sky-700 hover:text-sky-900">
            Request a new reset link
          </Link>
        </p>
      </AuthFormCard>
    );
  }

  return (
    <AuthFormCard title="Reset Password">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <PasswordInput
            id="newPassword"
            name="newPassword"
            label="New Password"
            autoComplete="new-password"
            minLength={8}
            required
          />
          <FieldError message={fieldErrors.newPassword} />
        </div>
        <div>
          <PasswordInput
            id="confirmPassword"
            name="confirmPassword"
            label="Confirm New Password"
            autoComplete="new-password"
            minLength={8}
            required
          />
          <FieldError message={fieldErrors.confirmPassword} />
        </div>
        <FieldError message={fieldErrors.form} />
        {fieldErrors.form ? (
          <p className="text-sm">
            <Link href="/forgot-password" className="font-medium text-sky-700 hover:text-sky-900">
              Request a new reset link
            </Link>
          </p>
        ) : null}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-gradient-to-r from-sky-900 to-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {submitting ? "Updating…" : "Reset Password"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        <Link href="/login" className="font-medium text-sky-700 hover:text-sky-900">
          Back to login
        </Link>
      </p>
    </AuthFormCard>
  );
};

export const ResetPasswordForm = () => (
  <ResetPasswordFormContent />
);
