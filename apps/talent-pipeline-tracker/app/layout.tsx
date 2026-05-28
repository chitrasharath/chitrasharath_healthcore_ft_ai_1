import type { Metadata } from "next";
import { Suspense } from "react";

import { StickyFooter } from "@/components/sticky-footer";
import "./globals.css";

export const metadata: Metadata = {
  title: "HealthCore Talent Pipeline Tracker",
  description: "Mobile-first recruiting workflow for HealthCore teams.",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <div className="flex-1 pb-16">{children}</div>
        <Suspense fallback={null}>
          <StickyFooter />
        </Suspense>
      </body>
    </html>
  );
}
