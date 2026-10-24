from langchain_core.prompts import ChatPromptTemplate

from llm import get_llm
from models import CompletenessResult
from state import DealState, log_entry

# The agent's instructions: who it is, and what it should (and shouldn't) do
PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a credit operations analyst at a UK bank. Your only job is to check "
     "whether an SME loan application contains all the required sections. "
     "A section counts as present only if it appears in the document with real content. "
     "Do not assess the loan itself."),
    ("human",
     "Required sections:\n{required_sections}\n\n"
     "Application document:\n{document}\n\n"
     "Identify any required sections that are missing."),
])


def completeness_node(state: DealState) -> dict:
    # 1. Get the LLM and hand it the blank form it must fill in
    llm = get_llm().with_structured_output(CompletenessResult)

    # 2. Join the instructions and the LLM into one "chain"
    chain = PROMPT | llm

    # 3. Read what it needs from the case folder, and run it
    result = chain.invoke({
        "required_sections": "\n".join(state["policy"]["required_sections"]),
        "document": state["document"],
    })

    # 4. Write a line for the audit log
    if result.is_complete:
        message = "All required sections present"
    else:
        message = f"Missing sections: {', '.join(result.missing_sections)}"

    # 5. Hand back ONLY the slots this agent is responsible for
    return {
        "completeness": result.model_dump(),
        "audit_log": [log_entry("Completeness checker", message)],
    }