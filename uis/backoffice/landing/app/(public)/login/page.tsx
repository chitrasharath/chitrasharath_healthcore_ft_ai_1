"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { LoginForm } from "@/components/auth/login-form";
import { ResetSuccessBanner } from "@/components/auth/reset-success-banner";

const LoginPageContent = () => {
  const searchParams = useSearchParams();
  const showResetBanner = searchParams.get("reset") === "success";

  return (
    <>
      {showResetBanner ? (
        <div className="px-4 pt-8 sm:px-6">
          <ResetSuccessBanner />
        </div>
      ) : null}
      <LoginForm />
    </>
  );
};

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="py-12 text-center text-sm text-slate-500">Loading…</p>}>
      <LoginPageContent />
    </Suspense>
  );
}
