from typing import Optional, Literal
from pydantic import BaseModel, Field


# ---------- Agent 1: Completeness checker ----------
class CompletenessResult(BaseModel):
    is_complete: bool = Field(description="True only if all required sections are present")
    missing_sections: list[str] = Field(default_factory=list, description="Names of required sections not found")


# ---------- Agent 2: Term extractor ----------
class LoanTerms(BaseModel):
    reference: Optional[str] = Field(None, description="Application reference, e.g. CR-2026-0141")
    borrower_name: Optional[str] = None
    sector: Optional[str] = Field(None, description="Business sector, e.g. Manufacturing")
    years_trading: Optional[float] = None
    loan_amount: Optional[float] = Field(None, description="Loan amount in GBP as a plain number, e.g. 1200000")
    tenor_years: Optional[float] = None
    ltv_percent: Optional[float] = Field(None, description="Loan-to-value as a percentage, e.g. 64.9")
    dscr: Optional[float] = Field(None, description="Debt service coverage ratio, e.g. 1.65")
    net_debt_to_ebitda: Optional[float] = None
    personal_guarantee: Optional[bool] = Field(None, description="True if a personal guarantee is offered")
    financial_covenants: Optional[str] = Field(None, description="Covenant text, or null if none agreed")
    kyc_complete: Optional[bool] = Field(None, description="True only if KYC checks are complete")
    audited_accounts_provided: Optional[bool] = None
    guarantee_details: Optional[str] = Field(None, description="Who gives the guarantee and any limit, e.g. 'Sarah Mitchell, limited to £300,000'. Null if no guarantee.")
    collateral_description: Optional[str] = Field(None, description="What the security is and its ranking, e.g. 'First legal charge over freehold factory, Bristol'")


# ---------- Agent 3: Compliance checker ----------
class RuleResult(BaseModel):
    rule_id: str
    description: str
    status: Literal["PASS", "FAIL", "UNABLE_TO_VERIFY"]
    actual_value: str
    severity: Literal["high", "medium"]


# ---------- Agent 4: Risk and summary ----------
class RiskAssessment(BaseModel):
    risk_rating: Literal["Low", "Medium", "High"]
    recommendation: Literal["Approve", "Refer", "Decline"]
    key_risks: list[str] = Field(description="Main risks identified, one sentence each")
    mitigants: list[str] = Field(description="Factors that reduce the risk, one sentence each")
    summary: str = Field(description="Executive summary for the credit officer, 3-5 sentences")