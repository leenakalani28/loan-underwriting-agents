import json
from datetime import date
from pathlib import Path

from langchain_core.tools import tool

# A mock company registry. In production this would be the Companies House API.
REGISTRY = json.loads(Path("data/company_registry.json").read_text(encoding="utf-8"))


@tool
def lookup_company(company_number: str) -> dict:
    """Looks up a UK company in the company registry by its company number.
    Returns the registered name, status (e.g. Active, Dissolved), incorporation date,
    years since incorporation and current directors.
    Use this to verify the borrower's identity and trading history against the application."""
    number = company_number.strip()
    record = REGISTRY.get(number)
    if record is None:
        return {"found": False, "company_number": number}

    incorporated = date.fromisoformat(record["incorporated_on"])
    years = round((date.today() - incorporated).days / 365.25, 1)
    return {"found": True, "company_number": number, **record, "years_since_incorporation": years}