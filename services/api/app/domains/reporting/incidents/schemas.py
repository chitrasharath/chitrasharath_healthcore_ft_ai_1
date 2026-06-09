from pydantic import BaseModel, ConfigDict


class TotalsResponse(BaseModel):
    total: int
    valid: int
    invalid: int


class InvalidBreakdownItem(BaseModel):
    rule: str
    label: str
    count: int


class BreakdownItem(BaseModel):
    label: str
    count: int
    percentage: float | None = None


class SatisfactionDistributionItem(BaseModel):
    score: int
    label: str
    count: int


class SatisfactionResponse(BaseModel):
    scored_cases: int
    total_closed: int
    average: float | None
    max_score: int = 5
    distribution: list[SatisfactionDistributionItem]


class IncidentAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_filename: str
    analyzed_at: str
    totals: TotalsResponse
    invalid_breakdown: list[InvalidBreakdownItem]
    by_category: list[BreakdownItem]
    by_status: list[BreakdownItem]
    by_country: list[BreakdownItem]
    satisfaction: SatisfactionResponse
