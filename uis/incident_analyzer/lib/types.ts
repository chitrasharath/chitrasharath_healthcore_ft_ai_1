export type Totals = {
  total: number;
  valid: number;
  invalid: number;
};

export type InvalidBreakdownItem = {
  rule: string;
  label: string;
  count: number;
};

export type BreakdownItem = {
  label: string;
  count: number;
  percentage: number | null;
};

export type SatisfactionDistributionItem = {
  score: number;
  label: string;
  count: number;
};

export type Satisfaction = {
  scored_cases: number;
  total_closed: number;
  average: number | null;
  max_score: number;
  distribution: SatisfactionDistributionItem[];
};

export type IncidentAnalysisResponse = {
  source_filename: string;
  analyzed_at: string;
  totals: Totals;
  invalid_breakdown: InvalidBreakdownItem[];
  by_category: BreakdownItem[];
  by_status: BreakdownItem[];
  by_country: BreakdownItem[];
  satisfaction: Satisfaction;
};
