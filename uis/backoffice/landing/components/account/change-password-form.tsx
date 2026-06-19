"use client";

import Link from "next/link";

import { FieldError } from "@/components/auth/field-error";
import { PasswordInput } from "@/components/auth/password-input";
import { useChangePasswordForm } from "@/hooks/use-change-password-form";

export const ChangePasswordForm = () => {
  const { loading, fieldErrors, submitting, success, handleSubmit } = useChangePasswordForm();

  if (loading) {
    return (
      <main className="mx-auto w-full max-w-md flex-1 px-4 py-8 sm:px-6">
        <p className="text-center text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-md flex-1 px-4 py-8 sm:px-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
        <h1 className="text-xl font-bold text-slate-900">Change Password</h1>
        {success ? (
          <p className="mt-4 rounded-lg bg-teal-50 px-3 py-2 text-sm text-teal-800" role="status">
            Password updated successfully.
          </p>
        ) : null}
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div>
            <PasswordInput
              id="currentPassword"
              name="currentPassword"
              label="Current Password"
              autoComplete="current-password"
              required
            />
            <FieldError message={fieldErrors.currentPassword} />
          </div>
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
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-gradient-to-r from-sky-900 to-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {submitting ? "Updating…" : "Update Password"}
          </button>
        </form>
        <p className="mt-6 text-sm">
          <Link href="/account/profile" className="font-medium text-sky-700 hover:text-sky-900">
            ← Back to Profile
          </Link>
        </p>
      </div>
    </main>
  );
};
