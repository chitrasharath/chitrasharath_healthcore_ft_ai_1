"use client";

import Link from "next/link";

import { AuthFormCard } from "@/components/auth/auth-form-card";
import { FieldError } from "@/components/auth/field-error";
import { PasswordInput } from "@/components/auth/password-input";
import { AUTH_INPUT_CLASS } from "@/hooks/use-login-form";
import { useRegisterForm } from "@/hooks/use-register-form";

export const RegisterForm = () => {
  const { fieldErrors, submitting, handleSubmit } = useRegisterForm();

  return (
    <AuthFormCard title="Register">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="name" className="mb-1 block text-sm font-medium text-slate-700">
            Name
          </label>
          <input id="name" name="name" type="text" required autoComplete="name" className={AUTH_INPUT_CLASS} />
          <FieldError message={fieldErrors.name} />
        </div>
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
            Email
          </label>
          <input id="email" name="email" type="email" required autoComplete="email" className={AUTH_INPUT_CLASS} />
          <FieldError message={fieldErrors.email} />
        </div>
        <div>
          <PasswordInput id="password" name="password" label="Password" autoComplete="new-password" minLength={8} required />
          <FieldError message={fieldErrors.password} />
        </div>
        <div>
          <PasswordInput
            id="confirmPassword"
            name="confirmPassword"
            label="Confirm Password"
            autoComplete="new-password"
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
          {submitting ? "Creating account…" : "Register"}
        </button>
        <p className="text-center text-sm text-slate-600">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-sky-700 hover:text-sky-900">
            Log in
          </Link>
        </p>
      </form>
    </AuthFormCard>
  );
};
