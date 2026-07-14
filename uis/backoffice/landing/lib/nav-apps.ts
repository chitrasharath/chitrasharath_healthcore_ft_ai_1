import { PUBLIC_WEBSITE_URL } from "@/lib/public-website-url";

export type NavApp = {
  title: string;
  description: string;
  url: string;
  protected: boolean;
  tag?: string;
  tagVariant?: "new" | "deprecated";
};

export const NAV_APPS: NavApp[] = [
  {
    title: "Incident Analyzer",
    description: "Legacy CSV upload and incident report analysis dashboard",
    url: "/incident-analyzer",
    protected: true,
    tag: "To be deprecated",
    tagVariant: "deprecated",
  },
  {
    title: "Incident Manager",
    description: "Log, track, and manage patient incidents across all clinics",
    url: "/incident-manager",
    protected: true,
    tag: "New",
    tagVariant: "new",
  },
  {
    title: "Supplier Directory",
    description: "Manage and search healthcare suppliers",
    url: "/supplier-directory",
    protected: true,
  },
  {
    title: "Inventory Management",
    description: "Track medical supply stock, deliveries, and clinical consumption",
    url: "/inventory",
    protected: true,
  },
  {
    title: "Reporting",
    description: "Materialized telemetry KPIs and pipeline health",
    url: "/reporting",
    protected: true,
    tag: "New",
    tagVariant: "new",
  },
  {
    title: "Talent Pipeline Tracker",
    description: "Track recruitment and hiring pipeline",
    url: "/talent-tracker",
    protected: true,
  },
  {
    title: "Back Office Functions",
    description: "Milestone 2 utility function test dashboard",
    url: "/backoffice-functions",
    protected: true,
  },
  {
    title: "Public Website",
    description: "HealthCore public-facing website",
    url: PUBLIC_WEBSITE_URL,
    protected: false,
  },
];
