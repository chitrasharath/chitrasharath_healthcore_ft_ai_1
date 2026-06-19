"use client";

import Link from "next/link";

import { AuthFormCard } from "@/components/auth/auth-form-card";
import { AUTH_INPUT_CLASS, useLoginForm } from "@/hooks/use-login-form";

export const LoginForm = () => {
  const { error, submitting, handleSubmit } = useLoginForm();

  return (
    <AuthFormCard title="Log In">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
            Email
          </label>
          <input id="email" name="email" type="email" required autoComplete="email" className={AUTH_INPUT_CLASS} />
        </div>
        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            required
            autoComplete="current-password"
            className={AUTH_INPUT_CLASS}
          />
          <p className="mt-2 text-sm">
            <Link href="/forgot-password" className="text-sky-700 hover:text-sky-900">
              Forgot your password?
            </Link>
          </p>
        </div>
        {error ? (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-gradient-to-r from-sky-900 to-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {submitting ? "Signing in…" : "Log In"}
        </button>
        <p className="text-center text-sm text-slate-600">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-medium text-sky-700 hover:text-sky-900">
            Register
          </Link>
        </p>
      </form>
    </AuthFormCard>
  );
};
