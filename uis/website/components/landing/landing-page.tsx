"use client";

import { AuthorSection } from "@/components/landing/author-section";
import { ContactSection } from "@/components/landing/contact-section";
import { EvidenceSection } from "@/components/landing/evidence-section";
import { FaqSection } from "@/components/landing/faq-section";
import { HeroSection } from "@/components/landing/hero-section";
import { LocationsSection } from "@/components/landing/locations-section";
import { ServicesSection } from "@/components/landing/services-section";
import { WhySection } from "@/components/landing/why-section";

export const LandingPage = () => (
  <main id="main-content" className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8" role="main">
    <HeroSection />
    <ServicesSection />
    <WhySection />
    <EvidenceSection />
    <LocationsSection />
    <ContactSection />
    <FaqSection />
    <AuthorSection />
  </main>
);
