const websiteLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "HealthCore",
  url: "https://www.healthcore.com",
  inLanguage: ["en", "es"],
};

const webPageLd = {
  "@context": "https://schema.org",
  "@type": "WebPage",
  name: "HealthCore Public Website",
  url: "https://www.healthcore.com/",
  isPartOf: {
    "@type": "WebSite",
    name: "HealthCore",
    url: "https://www.healthcore.com",
  },
  about: {
    "@id": "https://www.healthcore.com/#organization",
  },
  inLanguage: ["en", "es"],
};

const articleLd = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "Healthcare that fits your life",
  author: {
    "@type": "Organization",
    name: "HealthCore Digital",
  },
  publisher: {
    "@id": "https://www.healthcore.com/#organization",
  },
  dateModified: "2026-04-03",
  inLanguage: ["en", "es"],
};

const faqPageLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Can I request care online even if this is my first visit?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. Use the patient enquiry form and our front desk will contact you within 1 business day to confirm details.",
      },
    },
    {
      "@type": "Question",
      name: "Do you provide care in Spanish?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. US locations include bilingual staff in English and Spanish for better communication and follow-up.",
      },
    },
    {
      "@type": "Question",
      name: "Which clinics are shown on this public site?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "This website lists US clinics only. UK clinics serve a separate market and are not shown in this public-facing experience.",
      },
    },
  ],
};

const medicalOrgLd = {
  "@context": "https://schema.org",
  "@type": "MedicalOrganization",
  "@id": "https://www.healthcore.com/#organization",
  name: "HealthCore",
  description:
    "Outpatient healthcare network offering primary care, specialist consultations, chronic disease management, and preventive health programmes.",
  url: "https://www.healthcore.com",
  foundingDate: "2011",
  logo: "https://www.healthcore.com/logo.png",
  availableLanguage: ["English", "Spanish"],
  areaServed: ["US", "GB"],
  address: {
    "@type": "PostalAddress",
    addressLocality: "Austin",
    addressRegion: "Texas",
    addressCountry: "US",
  },
  contactPoint: {
    "@type": "ContactPoint",
    telephone: "+1-512-340-8800",
    contactType: "patient services",
    availableLanguage: ["English", "Spanish"],
  },
  sameAs: [
    "https://linkedin.com/company/healthcore",
    "https://facebook.com/healthcore",
    "https://instagram.com/healthcore",
  ],
};

const clinicsGraphLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "MedicalClinic",
      name: "HealthCore Austin Central",
      telephone: "+1-512-340-8800",
      openingHours: ["Mo-Fr 07:00-20:00", "Sa 09:00-15:00"],
      parentOrganization: { "@id": "https://www.healthcore.com/#organization" },
    },
    {
      "@type": "MedicalClinic",
      name: "HealthCore Austin North",
      telephone: "+1-512-340-8810",
      openingHours: ["Mo-Fr 08:00-19:00"],
      parentOrganization: { "@id": "https://www.healthcore.com/#organization" },
    },
    {
      "@type": "MedicalClinic",
      name: "HealthCore San Antonio",
      telephone: "+1-210-720-4400",
      openingHours: ["Mo-Fr 08:00-18:00", "Sa 09:00-13:00"],
      parentOrganization: { "@id": "https://www.healthcore.com/#organization" },
    },
    {
      "@type": "MedicalClinic",
      name: "HealthCore Miami",
      telephone: "+1-305-510-7700",
      openingHours: ["Mo-Fr 07:00-20:00", "Sa 09:00-16:00"],
      parentOrganization: { "@id": "https://www.healthcore.com/#organization" },
    },
    {
      "@type": "MedicalClinic",
      name: "HealthCore Orlando",
      telephone: "+1-407-892-6600",
      openingHours: ["Mo-Fr 08:00-18:00"],
      parentOrganization: { "@id": "https://www.healthcore.com/#organization" },
    },
    {
      "@type": "MedicalClinic",
      name: "HealthCore Atlanta",
      telephone: "+1-404-330-9900",
      openingHours: ["Mo-Fr 08:00-19:00"],
      parentOrganization: { "@id": "https://www.healthcore.com/#organization" },
    },
  ],
};

const schemas = [websiteLd, webPageLd, articleLd, faqPageLd, medicalOrgLd, clinicsGraphLd];

const JsonLdScript = ({ data }: { data: object }) => (
  <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
);

export const LandingJsonLd = () => (
  <>
    {schemas.map((schema, index) => (
      <JsonLdScript key={index} data={schema} />
    ))}
  </>
);
