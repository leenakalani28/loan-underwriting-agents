"""Uploads the golden dataset (evals/expected.json) to LangSmith and tags it v1.

Run once, from the project root with the venv active:
    python evals/upload_dataset.py

Running it again does nothing if the dataset already exists, so the
baseline and the improved run always use exactly the same cases.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATASET = "sme-loan-golden"

# The answer-key fields each example carries as its expected output
REFERENCE_FIELDS = [
    "expected_route", "expected_tool_call", "expected_recommendation", "acceptable_recommendations",
    "expected_non_pass_rules", "expected_terms", "narrative_check", "rationale",
]


def main():
    key = json.loads((ROOT / "evals" / "expected.json").read_text(encoding="utf-8"))
    client = Client()

    if client.has_dataset(dataset_name=DATASET):
        print(f"Dataset '{DATASET}' already exists, nothing uploaded. Delete it in LangSmith first to re-upload.")
        sys.exit(0)

    dataset = client.create_dataset(
        DATASET,
        description=(f"Golden dataset {key['dataset_version']} for the SME loan underwriting pipeline: "
                     "40 labelled applications (20 happy path, 12 edge, 6 known failures, 2 adversarial). "
                     f"{key.get('reviewed_by', '')}"),
    )

    inputs, outputs, metadata = [], [], []
    for case in key["cases"]:
        inputs.append({
            "case_id": case["case_id"],
            "scenario": case["scenario"],
            "document": (ROOT / case["file"]).read_text(encoding="utf-8"),
        })
        outputs.append({field: case[field] for field in REFERENCE_FIELDS})
        metadata.append({
            "case_id": case["case_id"],
            "scenario": case["scenario"],
            "title": case["title"],
            "dataset_version": key["dataset_version"],
        })

    client.create_examples(inputs=inputs, outputs=outputs, metadata=metadata, dataset_id=dataset.id)
    print(f"Uploaded {len(inputs)} examples to '{DATASET}'.")

    try:
        client.update_dataset_tag(dataset_name=DATASET, as_of=datetime.now(timezone.utc), tag="v1")
        print("Tagged this version of the dataset as 'v1'.")
    except Exception as err:  # tagging is a convenience; the run still works without it
        print(f"Could not tag the dataset ({err}). You can add the tag in the LangSmith UI.")


if __name__ == "__main__":
    main()
