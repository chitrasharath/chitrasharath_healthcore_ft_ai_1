"use client";

import Link from "next/link";

import { FieldError } from "@/components/auth/field-error";
import { AUTH_INPUT_CLASS } from "@/hooks/use-login-form";
import { formatAccountDate, useProfileForm } from "@/hooks/use-profile-form";

export const ProfileForm = () => {
  const { user, name, setName, loading, saving, saved, error, handleSave, logout } = useProfileForm();

  if (loading) {
    return (
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-8 sm:px-6">
        <p className="text-center text-sm text-slate-500">Loading profile…</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-8 sm:px-6">
        <p className="text-center text-sm text-red-600" role="alert">
          {error || "Could not load profile."}
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-8 sm:px-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
        <h1 className="text-xl font-bold text-slate-900">My Profile</h1>
        <div className="mt-6 space-y-5">
          <div>
            <label htmlFor="name" className="mb-1 block text-sm font-medium text-slate-700">
              Name
            </label>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <input
                id="name"
                name="name"
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                className={AUTH_INPUT_CLASS}
              />
              <button
                type="button"
                onClick={() => void handleSave()}
                disabled={saving}
                className="rounded-lg bg-gradient-to-r from-sky-900 to-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
            {saved ? (
              <p className="mt-2 text-sm text-teal-700" role="status">
                Saved
              </p>
            ) : null}
            <FieldError message={error} />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-700">Email</p>
            <p className="mt-1 text-sm text-slate-600">{user.email}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-slate-700">Member since</p>
            <p className="mt-1 text-sm text-slate-600">{formatAccountDate(user.created_at)}</p>
          </div>
        </div>
        <div className="mt-8 flex flex-wrap items-center gap-4 border-t border-slate-200 pt-6">
          <Link href="/account/change-password" className="text-sm font-medium text-sky-700 hover:text-sky-900">
            Change Password
          </Link>
          <button
            type="button"
            onClick={logout}
            className="text-sm font-medium text-slate-600 hover:text-slate-900"
          >
            Log Out
          </button>
          <Link href="/" className="text-sm text-slate-500 hover:text-slate-700">
            ← Back to Back Office
          </Link>
        </div>
      </div>
    </main>
  );
};
