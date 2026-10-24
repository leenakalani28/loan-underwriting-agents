from models import LoanTerms, RiskAssessment
from state import DealState

terms = LoanTerms(borrower_name="Test Ltd", loan_amount=1200000, ltv_percent=64.9)
print(terms.model_dump())

state: DealState = {
    "document": "sample",
    "policy": {},
    "completeness": None,
    "terms": terms.model_dump(),
    "compliance_results": None,
    "risk": None,
    "human_decision": None,
    "extraction_retries": 0,
    "audit_log": [],
}
print("State OK, keys:", list(state.keys()))