import { Suspense } from "react";

import { LandingJsonLd } from "@/components/schema-org/landing-json-ld";
import { SkipLink } from "@/components/layout/skip-link";
import { PortalHeader } from "@/components/layout/portal-header";
import { LandingPage } from "@/components/landing/landing-page";

export default function HomePage() {
  return (
    <>
      <LandingJsonLd />
      <Suspense fallback={null}>
        <SkipLink />
        <PortalHeader onLanding />
        <LandingPage />
      </Suspense>
    </>
  );
}
