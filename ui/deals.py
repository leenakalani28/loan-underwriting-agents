import re
from pathlib import Path

DATA_DIR = Path("data")


def _field(text: str, label: str):
    """Finds a line like 'Borrower: Harbourside Ltd' and returns the part after the colon."""
    match = re.search(rf"^{label}:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else None


def _short_amount(raw):
    """Turns '£1,200,000' into '£1.2M' and '£600,000' into '£600k' for the tiles."""
    if not raw:
        return "Amount not stated"
    digits = re.sub(r"[^\d.]", "", raw)
    if not digits:
        return raw
    value = float(digits)
    if value >= 1_000_000:
        return f"£{value / 1_000_000:.1f}M".replace(".0M", "M")
    if value >= 1_000:
        return f"£{value / 1_000:.0f}k"
    return f"£{value:,.0f}"


def parse_deal(deal_id: str, text: str) -> dict:
    """Reads the tile details straight from the document. No AI needed, so the queue loads instantly."""
    sector = _field(text, "Sector") or "Sector not stated"
    borrower = _field(text, "Borrower") or "Unknown borrower"
    return {
        "id": deal_id,
        "document": text,
        "reference": _field(text, "Reference") or "No reference",
        "borrower": borrower.replace(" Ltd", ""),
        "sector": sector.split("(")[0].strip(),
        "amount": _short_amount(_field(text, "Loan amount")),
        "purpose": _field(text, "Purpose") or "",
    }


def load_sample_deals() -> list[dict]:
    return [parse_deal(path.name, path.read_text(encoding="utf-8"))
            for path in sorted(DATA_DIR.glob("deal_*.txt"))]