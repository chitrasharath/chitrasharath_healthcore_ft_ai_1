export type Incident = {
  id: number;
  title: string;
  description: string;
  category: string;
  status: string;
  origin: string;
  branch: string;
  created_at: string;
  updated_at: string;
};

export type IncidentCreate = {
  title: string;
  description: string;
  category: string;
  origin: string;
  branch: string;
};

export type StatusUpdate = {
  status: string;
};

export type IncidentSummary = {
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_origin: Record<string, number>;
  by_branch: Record<string, number>;
};

export type IncidentFilters = {
  status?: string;
  origin?: string;
  branch?: string;
  category?: string;
};
