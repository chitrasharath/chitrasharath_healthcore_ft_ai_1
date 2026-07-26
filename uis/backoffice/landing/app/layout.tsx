import type { Metadata } from "next";

import { ConditionalLandingFooter } from "@/components/layout/conditional-landing-footer";
import "./globals.css";

export const metadata: Metadata = {
  title: "HealthCore | Back Office",
  description: "Secure portal for HealthCore internal tools and administration.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900">
        <div className="flex flex-1 flex-col">{children}</div>
        <ConditionalLandingFooter />
      </body>
    </html>
  );
}
