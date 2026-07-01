export type NavApp = {
  title: string;
  description: string;
  url: string;
  protected: boolean;
};

export const NAV_APPS: NavApp[] = [
  {
    title: "Incident Analyzer",
    description: "Patient incident report analysis dashboard",
    url: "/incident-analyzer",
    protected: true,
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
    url: "http://localhost:3005",
    protected: false,
  },
];
