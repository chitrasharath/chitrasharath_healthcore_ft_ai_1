const enquiryWebPageLd = {
  "@context": "https://schema.org",
  "@type": "WebPage",
  name: "HealthCore Patient Enquiry Form",
  url: "https://www.healthcore.com/application.html",
  inLanguage: ["en", "es"],
  about: {
    "@type": "MedicalOrganization",
    name: "HealthCore",
  },
};

const JsonLdScript = ({ data }: { data: object }) => (
  <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
);

export const EnquiryFormJsonLd = () => <JsonLdScript data={enquiryWebPageLd} />;
