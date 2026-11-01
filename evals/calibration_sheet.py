"""Builds a blind scoring sheet for judge calibration.

Pulls the risk agent's written assessment for chosen cases from a LangSmith experiment and writes
them to a CSV you can open in Excel. The judge's verdict is NOT included, so you score blind.

Run from the project root with the venv active:
    python evals/calibration_sheet.py --experiment baseline-final-695aa7e0 --cases C01 C04 C09 C14 C15 C25 C27 C33 C37 C39

Output: evals/results/calibration_blind.csv
Fill in the three yellow-header columns (your_verdict, your_failed_criteria, your_reason),
save, and send the file back.
"""
import argparse
import csv
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATASET = "sme-loan-golden"
CRITERIA = ("C1 coverage of failed rules | C2 grounded, nothing invented or contradicted | "
            "C3 genuine mitigants only | C4 accurate security | C5 case-specific check")


def bullets(items):
    return "\n".join(f"- {i}" for i in items or []) or "- (none)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--cases", nargs="+", required=True)
    args = parser.parse_args()
    wanted = {c.upper() for c in args.cases}

    client = Client()
    examples = {str(e.id): e for e in client.list_examples(dataset_name=DATASET)}
    rows = []
    for run in client.list_runs(project_name=args.experiment, is_root=True):
        ex = examples.get(str(run.reference_example_id))
        if not ex or ex.inputs["case_id"] not in wanted:
            continue
        out = run.outputs or {}
        rules = "\n".join(f"{r['rule_id']} [{r['status']}] {r['description']}: {r['actual_value']}"
                          for r in out.get("rule_results") or [])
        terms = "\n".join(f"{k}: {v}" for k, v in (out.get("terms") or {}).items() if v is not None)
        rows.append({
            "case_id": ex.inputs["case_id"],
            "case_specific_check (C5)": ex.outputs.get("narrative_check") or "none",
            "extracted_terms": terms,
            "rule_results": rules,
            "risk_rating": out.get("risk_rating"),
            "recommendation": out.get("recommendation"),
            "key_risks": bullets(out.get("key_risks")),
            "mitigants": bullets(out.get("mitigants")),
            "summary": out.get("summary"),
            "your_verdict (PASS/FAIL)": "",
            "your_failed_criteria (e.g. C3)": "",
            "your_reason": "",
        })
    rows.sort(key=lambda r: r["case_id"])

    path = ROOT / "evals" / "results" / "calibration_blind.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig so Excel shows £ correctly
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} cases to {path}")
    print("Criteria:", CRITERIA)
    missing = wanted - {r["case_id"] for r in rows}
    if missing:
        print("Not found in the experiment:", ", ".join(sorted(missing)))


if __name__ == "__main__":
    main()