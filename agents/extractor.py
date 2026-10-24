from langchain_core.prompts import ChatPromptTemplate

from llm import get_llm
from models import LoanTerms
from state import DealState, log_entry

# The boxes that MUST be filled for a proper review.
# If any come back empty, the orchestrator can ask for a retry.
MANDATORY_FIELDS = [
    "borrower_name", "sector", "years_trading", "loan_amount",
    "tenor_years", "ltv_percent", "dscr",
]


def missing_mandatory(terms: dict) -> list[str]:
    """Returns the names of any mandatory fields that are empty."""
    return [field for field in MANDATORY_FIELDS if terms.get(field) is None]


PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a credit analyst at a UK bank extracting loan terms from an SME loan application. "
     "Rules:\n"
     "- Extract only what the document states. Never guess, estimate or calculate values.\n"
     "- If a value is not stated, return null.\n"
     "- Write money as a plain number in GBP (e.g. £1,200,000 becomes 1200000).\n"
     "- Write percentages and ratios as plain numbers (e.g. 64.9% becomes 64.9, 1.65x becomes 1.65).\n"
     "- personal_guarantee is true only if a guarantee is actually offered; "
     "'None offered' or 'Not applicable' means false.\n"
     "- financial_covenants is null if covenants are not yet agreed (e.g. 'To be agreed').\n"
     "- kyc_complete is true only if KYC is stated as complete; 'In progress' means false.\n"
     "- guarantee_details must state exactly who gives the guarantee and any limit or cap on it.\n"
     "{retry_note}"),
    ("human", "Application document:\n{document}"),
])


def extractor_node(state: DealState) -> dict:
    # Is this a retry? If the folder already has terms, the orchestrator sent it back.
    previous_terms = state.get("terms")
    retries = state.get("extraction_retries", 0)

    retry_note = ""
    if previous_terms:
        retries += 1
        missed = missing_mandatory(previous_terms)
        retry_note = (f"\nIMPORTANT: A previous attempt missed these fields: {', '.join(missed)}. "
                      "Re-read the document carefully and extract them if they are stated.")

    llm = get_llm().with_structured_output(LoanTerms)
    chain = PROMPT | llm
    result = chain.invoke({"document": state["document"], "retry_note": retry_note})
    terms = result.model_dump()

    # Write a line for the audit log
    filled = sum(1 for value in terms.values() if value is not None)
    still_missing = missing_mandatory(terms)
    message = f"Extracted {filled} of {len(terms)} terms"
    if still_missing:
        message += f"; mandatory fields missing: {', '.join(still_missing)}"
    if retries:
        message += f" (retry {retries})"

    return {
        "terms": terms,
        "extraction_retries": retries,
        "audit_log": [log_entry("Term extractor", message)],
    }