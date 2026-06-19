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
    url: "http://localhost:3002",
    protected: true,
  },
  {
    title: "Supplier Directory",
    description: "Manage and search healthcare suppliers",
    url: "http://localhost:3003",
    protected: true,
  },
  {
    title: "Talent Pipeline Tracker",
    description: "Track recruitment and hiring pipeline",
    url: "http://localhost:3000",
    protected: true,
  },
  {
    title: "Back Office Functions",
    description: "Milestone 2 utility function test dashboard",
    url: "http://localhost:3001",
    protected: true,
  },
  {
    title: "Public Website",
    description: "HealthCore public-facing website",
    url: "http://localhost:3005",
    protected: false,
  },
];
