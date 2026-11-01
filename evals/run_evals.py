"""Runs the golden dataset through the pipeline and scores every case in LangSmith.

Run from the project root with the venv active:
    python evals/run_evals.py --label baseline --cases C01 C33     # smoke test on two cases
    python evals/run_evals.py --label baseline                     # all 40 cases
    python evals/run_evals.py --label improved-v2                  # after your changes

Each case runs until the graph pauses for the credit officer; the AI's recommendation
at that point is what gets scored (no human decision is needed).
Every case gets one LangSmith trace tagged with its case ID, scenario and the label
you pass as the prompt version. Results are also saved to evals/results/<label>.csv.
"""
import argparse
import csv
import json
import math
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)  # the agents read data files by relative path
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evals"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from langsmith import Client  # noqa: E402
from langchain_core.callbacks import get_usage_metadata_callback  # noqa: E402

from graph import build_graph  # noqa: E402
from evaluators import ALL_EVALUATORS  # noqa: E402

DATASET = "sme-loan-golden"
POLICY = json.loads((ROOT / "data" / "lending_policy.json").read_text(encoding="utf-8"))
PAUSE_SECONDS = float(os.getenv("EVAL_PAUSE_SECONDS", "2"))  # eases Groq rate limits between cases
GRAPH = build_graph()

PASS_BARS = {  # metric: (target, higher_is_better)
    "decision_accuracy": (0.95, True),
    "high_severity_recall": (1.00, True),
    "breach_recall": (0.95, True),
    "trajectory_correct": (1.00, True),
    "narrative_faithfulness": (0.90, True),
    "no_false_alarms": (0.95, True),
    "extraction_accuracy": (0.95, True),
    "no_error": (1.00, True),
}
P95_LATENCY_TARGET = 30.0
AVG_COST_TARGET_USD = 0.01  # average model cost per application

# Groq list prices, USD per million tokens (input, output), checked October 2026.
# The free tier costs nothing; list prices show what production use would cost.
PRICES_PER_MILLION = {
    "openai/gpt-oss-120b": (0.15, 0.60),
    "openai/gpt-oss-20b": (0.075, 0.30),
}


def cost_usd(usage_by_model: dict):
    """Model cost of one pipeline run, from the token counts of every LLM call (judge excluded)."""
    total = 0.0
    for model, u in usage_by_model.items():
        price = PRICES_PER_MILLION.get(model) or next(
            (p for name, p in PRICES_PER_MILLION.items() if model.endswith(name.split("/")[-1])), None)
        if price is None:
            return None
        total += u.get("input_tokens", 0) / 1e6 * price[0] + u.get("output_tokens", 0) / 1e6 * price[1]
    return round(total, 6)


def initial_state(document: str) -> dict:
    return {
        "document": document, "policy": POLICY,
        "completeness": None, "terms": None, "compliance_results": None, "risk": None,
        "human_decision": None, "next_step": None, "extraction_retries": 0, "audit_log": [],
    }


def make_target(label: str):
    def target(inputs: dict) -> dict:
        case_id = inputs["case_id"]
        config = {
            "configurable": {"thread_id": f"{label}-{case_id}-{uuid.uuid4().hex[:6]}"},
            "run_name": f"pipeline {case_id}",
            "metadata": {"case_id": case_id, "scenario": inputs.get("scenario"), "prompt_version": label},
            "tags": [label, case_id, inputs.get("scenario", "")],
        }
        start = time.perf_counter()
        error = None
        with get_usage_metadata_callback() as usage:  # counts tokens for every LLM call in this run
            try:
                GRAPH.invoke(initial_state(inputs["document"]), config)  # returns at the credit officer pause
            except Exception as err:
                error = f"{type(err).__name__}: {err}"[:500]
        elapsed = round(time.perf_counter() - start, 2)
        usage_by_model = dict(usage.usage_metadata)
        input_tokens = sum(u.get("input_tokens", 0) for u in usage_by_model.values())
        output_tokens = sum(u.get("output_tokens", 0) for u in usage_by_model.values())

        values, pack = {}, {}
        try:
            snapshot = GRAPH.get_state(config)
            values = snapshot.values or {}
            if snapshot.tasks and snapshot.tasks[0].interrupts:
                pack = snapshot.tasks[0].interrupts[0].value
        except Exception as err:
            error = error or f"Could not read state: {err}"

        completeness = values.get("completeness") or {}
        risk = values.get("risk") or {}
        rules = values.get("compliance_results") or []
        log = values.get("audit_log") or []
        time.sleep(PAUSE_SECONDS)
        return {
            "recommendation": pack.get("ai_recommendation") or risk.get("recommendation"),
            "risk_rating": risk.get("risk_rating"),
            "route": "short_circuit" if completeness and not completeness.get("is_complete") else "full",
            "tool_called": any("Tool call: lookup_company" in e.get("message", "") for e in log),
            "non_pass_rules": [r["rule_id"] for r in rules if r["status"] != "PASS"],
            "rule_results": rules,
            "terms": values.get("terms"),
            "key_risks": risk.get("key_risks"),
            "mitigants": risk.get("mitigants"),
            "summary": risk.get("summary"),
            "audit_log": [f"{e['agent']}: {e['message']}" for e in log],
            "latency_s": elapsed,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd(usage_by_model),
            "error": error,
        }
    return target


def percentile(values, pct):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    k = (len(values) - 1) * pct
    lo, hi = math.floor(k), math.ceil(k)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="Run name and prompt version, e.g. baseline or improved-v2")
    parser.add_argument("--cases", nargs="*", help="Only run these case IDs, e.g. C01 C33")
    args = parser.parse_args()

    client = Client()
    try:
        examples = list(client.list_examples(dataset_name=DATASET, as_of="v1"))
    except Exception:
        examples = list(client.list_examples(dataset_name=DATASET))
    if args.cases:
        wanted = {c.upper() for c in args.cases}
        examples = [e for e in examples if e.inputs["case_id"] in wanted]
    examples.sort(key=lambda e: e.inputs["case_id"])
    print(f"Running {len(examples)} cases as '{args.label}'...")

    results = client.evaluate(
        make_target(args.label),
        data=examples,
        evaluators=ALL_EVALUATORS,
        experiment_prefix=args.label,
        metadata={"prompt_version": args.label, "model": os.getenv("GROQ_MODEL"),
                  "judge_model": os.getenv("JUDGE_MODEL") or os.getenv("GROQ_MODEL"), "dataset_version": "v1"},
        max_concurrency=1,
    )

    # ---- Case-level results to CSV, for the spreadsheet deliverable
    rows, scores = [], {}
    for row in results:
        ex, out = row["example"], row["run"].outputs or {}
        ref = ex.outputs
        line = {
            "case_id": ex.inputs["case_id"], "scenario": ex.inputs.get("scenario"),
            "expected_recommendation": ref["expected_recommendation"],
            "predicted_recommendation": out.get("recommendation"),
            "expected_non_pass_rules": " ".join(ref["expected_non_pass_rules"]),
            "predicted_non_pass_rules": " ".join(out.get("non_pass_rules") or []),
            "expected_route": ref["expected_route"], "predicted_route": out.get("route"),
            "risk_rating": out.get("risk_rating"), "latency_s": out.get("latency_s"),
            "total_tokens": (out.get("input_tokens") or 0) + (out.get("output_tokens") or 0),
            "cost_usd": out.get("cost_usd"), "error": out.get("error") or "",
        }
        for ev in row["evaluation_results"]["results"]:
            line[ev.key] = ev.score
            if ev.key == "narrative_faithfulness":
                line["judge_comment"] = ev.comment
            if ev.score is not None:
                scores.setdefault(ev.key, []).append(ev.score)
        rows.append(line)
    rows.sort(key=lambda r: r["case_id"])

    out_dir = ROOT / "evals" / "results"
    out_dir.mkdir(exist_ok=True)
    columns = []
    for r in rows:
        columns += [k for k in r if k not in columns]
    csv_path = out_dir / f"{args.label}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    # ---- Summary against the pass bars
    print(f"\n=== {args.label}: {len(rows)} cases ===")
    print(f"{'Metric':<24}{'Score':>8}{'Target':>9}{'Cases':>7}  Result")
    summary = {}
    for metric, (target, _) in PASS_BARS.items():
        vals = scores.get(metric)
        if not vals:
            continue
        mean = sum(vals) / len(vals)
        summary[metric] = round(mean, 3)
        print(f"{metric:<24}{mean:>8.1%}{target:>9.0%}{len(vals):>7}  {'PASS' if mean >= target else 'below bar'}")
    lat = [r["latency_s"] for r in rows]
    p50, p95 = percentile(lat, 0.5), percentile(lat, 0.95)
    summary.update({"p50_latency_s": p50, "p95_latency_s": p95})
    print(f"{'p50 latency':<24}{p50:>7.1f}s")
    print(f"{'p95 latency':<24}{p95:>7.1f}s{P95_LATENCY_TARGET:>8.0f}s{len(lat):>7}  {'PASS' if p95 <= P95_LATENCY_TARGET else 'below bar'}")
    costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]
    if costs:
        avg_cost, max_cost = sum(costs) / len(costs), max(costs)
        avg_tokens = sum(r["total_tokens"] for r in rows) / len(rows)
        summary.update({"avg_cost_usd": round(avg_cost, 6), "max_cost_usd": max_cost, "avg_tokens": round(avg_tokens)})
        print(f"{'avg cost / application':<24}${avg_cost:>6.4f}  ${AVG_COST_TARGET_USD:.2f}{len(costs):>7}  {'PASS' if avg_cost <= AVG_COST_TARGET_USD else 'below bar'}")
        print(f"{'max cost / application':<24}${max_cost:>6.4f}")
        print(f"{'avg tokens / application':<24}{avg_tokens:>7,.0f}")
    else:
        print("Cost not calculated: model not in PRICES_PER_MILLION")
    (out_dir / f"{args.label}_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nCase results: {csv_path}")
    print(f"LangSmith experiment: {results.experiment_name} (Datasets & Experiments > {DATASET})")


if __name__ == "__main__":
    main()