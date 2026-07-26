import type { Metadata } from "next";

import { ConditionalLandingFooter } from "@/components/layout/conditional-landing-footer";
import { ThemeScript } from "@/components/layout/theme-script";
import "./globals.css";

export const metadata: Metadata = {
  title: "HealthCore | Back Office",
  description: "Secure portal for HealthCore internal tools and administration.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <div className="flex flex-1 flex-col">{children}</div>
        <ConditionalLandingFooter />
      </body>
    </html>
  );
}
