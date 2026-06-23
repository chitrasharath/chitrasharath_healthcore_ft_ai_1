"use client";

import { usePathname } from "next/navigation";

import { LandingFooter } from "@/components/layout/landing-footer";

export const ConditionalLandingFooter = () => {
  const pathname = usePathname();
  if (pathname.startsWith("/talent-tracker")) return null;
  return <LandingFooter />;
};
