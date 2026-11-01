import json
import re

from langchain_core.prompts import ChatPromptTemplate

from llm import get_llm
from models import RiskAssessment
from state import DealState, log_entry

# Lets us compare outcomes: a higher number means stricter
STRICTNESS = {"Approve": 0, "Refer": 1, "Decline": 2}
MAX_ATTEMPTS = 2  # F2: ask again if the model returns an incomplete answer


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
     "Medium = minor breaches or thin headroom; High = serious breaches or several weaknesses. "
     "Residual risks on a deal with no breaches and comfortable headroom do not raise the rating above Low.\n\n"
     "Grounding rules:\n"
     "- Every FAILED compliance rule must appear as a key risk.\n"
     "- Every statement must be supported by the extracted loan terms. Never invent facts.\n"
     "- Describe guarantees and security exactly as stated in guarantee_details and "
     "collateral_description, including any limits or amounts.\n"
     "- Always list at least one key risk. Even strong deals carry residual risks, "
     "such as partial guarantees, sector exposure or concentration of security.\n"
     "- Measure headroom against the POLICY limits shown in the compliance results "
     "(LTV 75%, DSCR 1.25x, net debt/EBITDA 3.5x), never against covenant levels.\n\n"
     "Mitigant rules (a mitigant is a fact that genuinely reduces the chance or size of a loss):\n"
     "- GENUINE mitigants, always stated with the figure and the limit: LTV at least 5 points below 75%; "
     "DSCR at least 0.15x above 1.25x; net debt/EBITDA at least 0.5x below 3.5x; "
     "trading history of 5 years or more; collateral value well above the loan; "
     "a personal guarantee or extra security; covenants TIGHTER than policy on every measure.\n"
     "- NEVER list these as mitigants, not even as part of another point: KYC complete; audited accounts "
     "provided; sector not excluded; tenor within the limit; borrower matches the registry; covenants "
     "agreed or documented; covenants set at policy; trading history under 5 years; any metric that "
     "only just meets its limit.\n"
     "- Never cite as a mitigant anything a FAILED rule contradicts (for example the borrower's stated "
     "trading history when the registry check failed, or a stated LTV when the LTV rule failed).\n"
     "- One fact per mitigant. Fewer genuine mitigants are better than padded ones; an empty list is "
     "acceptable.\n"
     "Write in clear, professional language a credit committee would expect.\n"
     "Always fill in all five fields: risk_rating, recommendation, key_risks, mitigants, summary."),
    ("human",
     "Extracted loan terms:\n{terms}\n\n"
     "Compliance results:\n{compliance}{retry_note}"),
])


def format_compliance(results: list) -> str:
    return "\n".join(
        f"{r['rule_id']} [{r['status']}, {r['severity']} severity] {r['description']}: {r['actual_value']}"
        for r in results
    )


# ---------------------------------------------------------------- F1: mitigant filter (code)
# Entry requirements that are never genuine mitigants, whatever the wording
ENTRY_REQUIREMENT_WORDS = [
    r"\bkyc\b", r"know your customer", r"audited accounts", r"\baccounts (?:have been |were )?(?:provided|supplied)",
    r"not (?:an )?excluded", r"permitted sector", r"within (?:the )?(?:policy |maximum )?(?:tenor|term)",
    r"tenor .*(?:within|below|under)", r"match(?:es)? (?:the )?(?:company )?regist",
    r"covenants? .*(?:documented|agreed|in place|meet|at policy)",
]

# Metric -> (words that identify it, rule ID, function that says whether headroom is clear)
METRICS = {
    "ltv": ([r"\bltv\b", r"loan[- ]to[- ]value"], "R1",
            lambda t: t.get("ltv_percent") is not None and t["ltv_percent"] <= 70),
    "dscr": ([r"\bdscr\b", r"debt service"], "R2",
             lambda t: t.get("dscr") is not None and t["dscr"] >= 1.40),
    "leverage": ([r"net debt", r"ebitda"], "R6",
                 lambda t: t.get("net_debt_to_ebitda") is not None and t["net_debt_to_ebitda"] <= 3.0),
    "trading": ([r"years? (?:of )?trading", r"trading history", r"years? in business", r"established"], "R5",
                lambda t: t.get("years_trading") is not None and t["years_trading"] >= 5),
}


def _mentions(text: str, patterns: list) -> bool:
    return any(re.search(p, text) for p in patterns)


def filter_mitigants(mitigants: list, terms: dict, results: list):
    """Removes mitigants that are entry requirements, thin headroom, or contradicted by a failed rule.
    Returns (kept, removed_with_reason)."""
    failed = {r["rule_id"] for r in results if r["status"] != "PASS"}
    kept, removed = [], []
    for m in mitigants:
        text = m.lower()
        reason = None
        if _mentions(text, ENTRY_REQUIREMENT_WORDS):
            reason = "entry requirement, not a mitigant"
        else:
            for name, (patterns, rule_id, clear_headroom) in METRICS.items():
                if not _mentions(text, patterns):
                    continue
                if rule_id in failed or (name == "trading" and "R10" in failed):
                    reason = f"contradicted by failed rule {('R10' if name == 'trading' and 'R10' in failed else rule_id)}"
                elif not clear_headroom(terms):
                    reason = f"{name} headroom too thin to count as a mitigant"
                if reason:
                    break
        (removed if reason else kept).append((m, reason) if reason else m)
    return kept, removed


# ---------------------------------------------------------------- F2: safe fallback
def fallback_assessment(floor: str, results: list) -> RiskAssessment:
    """Used only if the model fails to give a complete answer after every attempt.
    Never approves: a case without an AI assessment always goes to the officer as Refer or stricter."""
    failed = [r for r in results if r["status"] != "PASS"]
    return RiskAssessment(
        risk_rating="High" if floor == "Decline" else "Medium",
        recommendation=floor if floor != "Approve" else "Refer",
        key_risks=[f"{r['rule_id']} {r['status']}: {r['description']}" for r in failed]
                  + ["AI risk assessment unavailable: manual credit assessment required"],
        mitigants=[],
        summary="The AI risk assessment could not be completed. The recommendation is based on the "
                "lending policy rule results only, and the credit officer should assess the deal manually.",
    )


def risk_node(state: DealState) -> dict:
    terms = state["terms"]
    results = state["compliance_results"]
    floor = policy_floor(results)
    log_lines = []

    chain = PROMPT | get_llm().with_structured_output(RiskAssessment)
    assessment, retry_note = None, ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            assessment = chain.invoke({
                "floor": floor,
                "terms": json.dumps(terms, indent=2),
                "compliance": format_compliance(results),
                "retry_note": retry_note,
            })
            break
        except Exception as err:  # incomplete or badly formatted answer
            log_lines.append(log_entry(
                "Risk and summary", f"Attempt {attempt} failed ({type(err).__name__}); retrying"))
            retry_note = ("\n\nYour previous answer was incomplete. Reply again and fill in all five fields: "
                          "risk_rating, recommendation, key_risks, mitigants, summary.")

    if assessment is None:
        assessment = fallback_assessment(floor, results)
        log_lines.append(log_entry(
            "Risk and summary", "AI assessment unavailable after retries; policy-based fallback used"))

    # F1: remove padded or contradicted mitigants (deterministic, logged for audit)
    kept, removed = filter_mitigants(assessment.mitigants, terms, results)
    for text, reason in removed:
        log_lines.append(log_entry("Mitigant filter", f"Removed '{text[:80]}': {reason}"))
    assessment.mitigants = kept

    # Guardrail: the LLM can be stricter than policy, never more lenient
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