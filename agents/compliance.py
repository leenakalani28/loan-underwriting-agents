import operator
from typing import Literal

from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate

from llm import get_llm
from models import RuleResult
from state import DealState, log_entry

# Python's built-in comparison functions, looked up by the symbol used in the policy file
COMPARISONS = {"<=": operator.le, ">=": operator.ge}


def make_result(rule: dict, status: str, actual: str) -> RuleResult:
    """Fills in one RuleResult form."""
    return RuleResult(
        rule_id=rule["id"],
        description=rule["description"],
        status=status,
        actual_value=actual,
        severity=rule["severity"],
    )


# ---------- Part 1: rules checked by plain Python ----------
def check_rule(rule: dict, terms: dict, policy: dict) -> RuleResult:
    kind = rule["operator"]
    value = terms.get(rule["field"])

    # Simple number comparisons: R1, R2, R3, R5, R6
    if kind in COMPARISONS:
        if value is None:
            return make_result(rule, "UNABLE_TO_VERIFY", "Not stated in application")
        passed = COMPARISONS[kind](value, rule["threshold"])
        return make_result(rule, "PASS" if passed else "FAIL", str(value))

    # Personal guarantee needed only for big loans: R4
    if kind == "required_if_amount_above":
        amount = terms.get("loan_amount")
        if amount is None:
            return make_result(rule, "UNABLE_TO_VERIFY", "Loan amount not stated")
        if amount <= rule["threshold"]:
            return make_result(rule, "PASS", f"Not required for a £{amount:,.0f} loan")
        if value is None:
            return make_result(rule, "UNABLE_TO_VERIFY", "Guarantee position not stated")
        return make_result(rule, "PASS" if value else "FAIL",
                           f"Guarantee offered: {'Yes' if value else 'No'} on a £{amount:,.0f} loan")

    # KYC and audited accounts both needed: R8
    if kind == "is_true":
        kyc = terms.get("kyc_complete")
        accounts = terms.get("audited_accounts_provided")
        if kyc is None or accounts is None:
            return make_result(rule, "UNABLE_TO_VERIFY", "KYC or accounts status not stated")
        return make_result(rule, "PASS" if (kyc and accounts) else "FAIL",
                           f"KYC complete: {kyc}; audited accounts: {accounts}")

    # Sector not on the excluded list: R9
    if kind == "not_in_excluded":
        if value is None:
            return make_result(rule, "UNABLE_TO_VERIFY", "Sector not stated")
        hits = [s for s in policy["excluded_sectors"] if s in value.lower()]
        return make_result(rule, "FAIL" if hits else "PASS", value)

    raise ValueError(f"Unknown rule operator: {kind}")


# ---------- Part 2: the rule that needs the LLM's judgement ----------
class CovenantReview(BaseModel):
    status: Literal["PASS", "FAIL"]
    reason: str


COVENANT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a credit risk analyst at a UK bank reviewing the financial covenants on an SME loan. "
     "Covenants PASS only if they are agreed, documented, and no weaker than these policy thresholds:\n"
     "- Minimum DSCR covenant must be at least 1.25x\n"
     "- If there is a net debt/EBITDA covenant, its maximum must be no higher than 3.5x\n"
     "A covenant set at a looser level than policy is a FAIL. Give a one-sentence reason."),
    ("human", "Financial covenants in the application:\n{covenants}"),
])


def review_covenants(rule: dict, terms: dict) -> RuleResult:
    covenants = terms.get("financial_covenants")
    if not covenants:
        return make_result(rule, "FAIL", "No financial covenants agreed")

    llm = get_llm().with_structured_output(CovenantReview)
    review = (COVENANT_PROMPT | llm).invoke({"covenants": covenants})
    return make_result(rule, review.status, f"{covenants} (AI review: {review.reason})")


# ---------- The agent itself ----------
def compliance_node(state: DealState) -> dict:
    terms = state["terms"]
    policy = state["policy"]

    results = []
    for rule in policy["rules"]:
        if rule["operator"] == "llm_review":
            results.append(review_covenants(rule, terms))
        else:
            results.append(check_rule(rule, terms, policy))

    failed = [r.rule_id for r in results if r.status == "FAIL"]
    unverified = [r.rule_id for r in results if r.status == "UNABLE_TO_VERIFY"]
    message = f"{len(results) - len(failed) - len(unverified)} passed, {len(failed)} failed"
    if failed:
        message += f" ({', '.join(failed)})"
    if unverified:
        message += f", {len(unverified)} unable to verify ({', '.join(unverified)})"

    return {
        "compliance_results": [r.model_dump() for r in results],
        "audit_log": [log_entry("Compliance checker", message)],
    }
    