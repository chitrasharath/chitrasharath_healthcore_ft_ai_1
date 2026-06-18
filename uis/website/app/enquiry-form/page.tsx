import type { Metadata } from "next";
import { Suspense } from "react";

import { EnquiryFormPage } from "@/components/enquiry/enquiry-form-page";
import { PortalHeader } from "@/components/layout/portal-header";
import { SkipLink } from "@/components/layout/skip-link";
import { EnquiryFormJsonLd } from "@/components/schema-org/enquiry-form-json-ld";

export const metadata: Metadata = {
  title: "HealthCore | Patient Enquiry Form",
  description:
    "Submit a patient enquiry to HealthCore so our front desk team can contact you and confirm appointment details.",
  robots: { index: true, follow: true },
  authors: [{ name: "HealthCore Digital" }],
  alternates: {
    canonical: "/enquiry-form",
    languages: {
      en: "/enquiry-form?lang=en",
      es: "/enquiry-form?lang=es",
      "x-default": "/enquiry-form?lang=en",
    },
  },
  openGraph: {
    type: "website",
    title: "HealthCore | Patient Enquiry Form",
    description: "Securely submit a patient enquiry and get a callback within 1 business day.",
    url: "/enquiry-form",
    images: [
      {
        url: "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=1200&q=80",
      },
    ],
  },
  twitter: { card: "summary_large_image" },
};

export default function EnquiryFormRoute() {
  return (
    <>
      <EnquiryFormJsonLd />
      <Suspense fallback={null}>
        <SkipLink />
        <PortalHeader onLanding={false} />
        <EnquiryFormPage />
      </Suspense>
    </>
  );
}
