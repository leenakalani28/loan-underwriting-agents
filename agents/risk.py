import json
from langchain_core.prompts import ChatPromptTemplate

from llm import get_llm
from models import RiskAssessment
from state import DealState, log_entry

# Lets us compare outcomes: a higher number means stricter
STRICTNESS = {"Approve": 0, "Refer": 1, "Decline": 2}


def policy_floor(compliance_results: list) -> str:
    """The most lenient outcome the lending policy allows, based on the rule results."""
    if any(r["status"] == "FAIL" and r["severity"] == "high" for r in compliance_results):
        return "Decline"
    if any(r["status"] in ("FAIL", "UNABLE_TO_VERIFY") for r in compliance_results):
        return "Refer"
    return "Approve"


PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a senior credit risk analyst at a UK bank preparing a recommendation "
     "for a credit officer on an SME secured loan.\n"
     "The lending policy sets the most lenient outcome allowed for this deal: {floor}. "
     "You may recommend a stricter outcome if the overall risk justifies it, but never a more lenient one.\n"
     "Risk rating guide: Low = no breaches and comfortable headroom; "
     "Medium = minor breaches or thin headroom; High = serious breaches or several weaknesses.\n\n"
     "Residual risks on a deal with no breaches and comfortable headroom do not raise the rating above Low.\n\n"
     "Grounding rules:\n"
     "- Every statement must be supported by the extracted loan terms. Never invent facts.\n"
      "- Every FAILED compliance rule must appear as a key risk.\n"
     "- Describe guarantees and security exactly as stated in guarantee_details and "
     "collateral_description, including any limits or amounts.\n"
     "- Always list at least one key risk. Even strong deals carry residual risks, "
     "such as partial guarantees, sector exposure or concentration of security.\n"
     "- A mitigant is a fact that genuinely reduces the chance or size of a loss, for example "
     "substantial headroom against a policy limit, strong cash-flow cover, or additional security. "
     "Simply meeting a minimum requirement (for example, tenor within the limit or the sector not excluded) "
     "is NOT a mitigant.\n"
     "Write in clear, professional language a credit committee would expect."),
    ("human",
     "Extracted loan terms:\n{terms}\n\n"
     "Compliance results:\n{compliance}"),
])


def format_compliance(results: list) -> str:
    return "\n".join(
        f"{r['rule_id']} [{r['status']}, {r['severity']} severity] {r['description']}: {r['actual_value']}"
        for r in results
    )


def risk_node(state: DealState) -> dict:
    terms = state["terms"]
    results = state["compliance_results"]
    floor = policy_floor(results)

    llm = get_llm().with_structured_output(RiskAssessment)
    assessment = (PROMPT | llm).invoke({
        "floor": floor,
        "terms": json.dumps(terms, indent=2),
        "compliance": format_compliance(results),
    })

    # Guardrail: the LLM can be stricter than policy, never more lenient
    log_lines = []
    if STRICTNESS[assessment.recommendation] < STRICTNESS[floor]:
        log_lines.append(log_entry(
            "Policy guardrail",
            f"AI recommended {assessment.recommendation}; overridden to {floor} by lending policy",
        ))
        assessment.recommendation = floor

    log_lines.append(log_entry(
        "Risk and summary",
        f"Risk rating {assessment.risk_rating}; recommendation {assessment.recommendation}",
    ))

    return {
        "risk": assessment.model_dump(),
        "audit_log": log_lines,
    }