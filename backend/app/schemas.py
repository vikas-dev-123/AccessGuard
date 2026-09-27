from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserOut(ORMModel):
    username: str
    full_name: str
    role: str


class DatasetOut(ORMModel):
    id: int
    uploaded_at: datetime
    uploaded_by: str
    systems: list[str]
    file_names: dict[str, str]
    hr_employee_count: int
    account_counts: dict[str, int]


class RunReviewRequest(BaseModel):
    dataset_id: int | None = None
    as_of_date: date | None = None


class ReviewOut(ORMModel):
    id: int
    dataset_id: int
    run_at: datetime
    run_by: str
    as_of_date: date
    systems: list[str]
    total_findings: int


class FindingOut(ORMModel):
    finding_id: str
    check_code: str
    check_name: str
    system: str
    employee_id: str | None
    username: str
    details: str
    risk_rating: str
    detected_at: datetime


class FindingsPage(BaseModel):
    total: int
    items: list[FindingOut]


class SummaryOut(BaseModel):
    review_id: int
    total: int
    by_risk: dict[str, int]
    by_check: dict[str, int]
    by_system: dict[str, int]


class CheckOut(BaseModel):
    code: str
    name: str
    condition: str
    criteria: str
    impact: str
    recommendation: str
