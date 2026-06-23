import type { Metadata } from "next";
import { Suspense } from "react";

import { PortalFooter } from "@/components/layout/portal-footer";
import { LanguageProvider } from "@/lib/i18n/language-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "HealthCore | Outpatient Care Network",
  description:
    "HealthCore is an outpatient healthcare network with 12 clinics across the US and UK offering same-day appointments, extended hours, and bilingual care.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-50 text-slate-900">
        <Suspense fallback={null}>
          <LanguageProvider>
            {children}
            <PortalFooter />
          </LanguageProvider>
        </Suspense>
      </body>
    </html>
  );
}
