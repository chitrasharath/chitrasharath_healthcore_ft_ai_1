import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "HealthCore | Incident Analyzer",
  description: "Patient incident report analysis dashboard for HealthCore operations.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-100 text-slate-900">{children}</body>
    </html>
  );
}
