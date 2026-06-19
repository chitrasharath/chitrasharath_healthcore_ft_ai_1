import { Suspense } from "react";

import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<p className="py-12 text-center text-sm text-slate-500">Loading…</p>}>
      <ResetPasswordForm />
    </Suspense>
  );
}
