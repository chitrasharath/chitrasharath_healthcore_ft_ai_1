import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "HealthCore Backoffice | Milestone 2 Manual Test",
  description: "Internal manual test dashboard for HealthCore Milestone 2 utility functions.",
  icons: { icon: "/icon.svg", shortcut: "/icon.svg", apple: "/icon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-50 text-slate-900">{children}</body>
    </html>
  );
}
