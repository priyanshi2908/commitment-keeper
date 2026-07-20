#!/usr/bin/env python3
"""Evaluation harness for the commitment-keeper extraction skill.

This harness is extraction-agnostic: it does NOT call Hermes. It loads
test_cases.json, validates each case's structure, and provides a
`record_response()` function that records the model/skill's actual JSON output.
When actual outputs are available (e.g. filled in by a separate runner, or by a
backend call), it compares `actual.decision` to `expected_decision` and checks
`expected_missing_fields`, computes accuracy, lists failures, and writes
`evaluation_results.json`.

Modes:
  --validate-only   only validate the dataset structure; do NOT attempt any
                    extraction. (This is what to run before wiring a model.)
  --from-json PATH  read a JSON file mapping case id -> actual extraction object
                    (e.g. produced by a backend runner) and score against it.

Without --from-json the harness validates the dataset and reports that no actual
responses are recorded yet (accuracy 0/0), then writes an empty results file.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
CASES_PATH = os.path.join(HERE, "test_cases.json")
RESULTS_PATH = os.path.join(HERE, "evaluation_results.json")

VALID_DECISIONS = {"stage", "ignore", "requires_acceptance", "possible_completion"}
VALID_MISSING = {"actor", "action", "deadline", "beneficiary"}
REQUIRED_KEYS = {
    "id", "authenticated_user", "current_datetime", "existing_commitment",
    "conversation", "expected_decision", "expected_missing_fields", "notes",
}


# --------------------------------------------------------------------------- #
# Dataset loading + validation
# --------------------------------------------------------------------------- #
def load_cases() -> Dict[str, Any]:
    with open(CASES_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_case(case: Dict[str, Any], idx: int) -> List[str]:
    """Return a list of human-readable problems with a single case."""
    problems: List[str] = []
    if not isinstance(case, dict):
        return [f"case #{idx} is not an object"]
    missing = REQUIRED_KEYS - set(case.keys())
    if missing:
        problems.append(f"case #{idx} missing keys: {sorted(missing)}")
    extra = set(case.keys()) - REQUIRED_KEYS
    if extra:
        problems.append(f"case #{idx} unexpected keys: {sorted(extra)}")

    cid = case.get("id", f"<#{idx}>")
    if not case.get("id"):
        problems.append(f"case #{idx} has empty id")

    if case.get("expected_decision") not in VALID_DECISIONS:
        problems.append(f"{cid}: expected_decision not in {sorted(VALID_DECISIONS)}")

    mf = case.get("expected_missing_fields", None)
    if not isinstance(mf, list) or any(m not in VALID_MISSING for m in mf):
        problems.append(f"{cid}: expected_missing_fields must be a list of {sorted(VALID_MISSING)}")

    conv = case.get("conversation", None)
    if not isinstance(conv, list) or len(conv) == 0:
        problems.append(f"{cid}: conversation must be a non-empty list")
    else:
        for j, m in enumerate(conv):
            if not isinstance(m, dict) or "speaker" not in m or "text" not in m:
                problems.append(f"{cid}: conversation[{j}] needs speaker+text")
            elif not isinstance(m.get("speaker"), str) or not isinstance(m.get("text"), str):
                problems.append(f"{cid}: conversation[{j}] speaker/text must be strings")

    if not isinstance(case.get("authenticated_user"), str) or not case["authenticated_user"]:
        problems.append(f"{cid}: authenticated_user must be a non-empty string")
    if not isinstance(case.get("current_datetime"), str) or not case["current_datetime"]:
        problems.append(f"{cid}: current_datetime must be a non-empty string")
    if case.get("existing_commitment") is not None and not isinstance(case["existing_commitment"], str):
        problems.append(f"{cid}: existing_commitment must be null or a string")
    if not isinstance(case.get("notes"), str):
        problems.append(f"{cid}: notes must be a string")
    return problems


def validate_dataset(data: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    if not isinstance(data, dict) or "cases" not in data:
        return ["top-level object must contain 'cases'"]
    cases = data["cases"]
    if not isinstance(cases, list):
        return ["'cases' must be a list"]
    ids = [c.get("id") for c in cases]
    if len(ids) != len(set(ids)):
        problems.append(f"duplicate case ids detected: {ids}")
    for i, case in enumerate(cases):
        problems.extend(validate_case(case, i))
    return problems


# --------------------------------------------------------------------------- #
# Recording + scoring
# --------------------------------------------------------------------------- #
def record_response(results: Dict[str, Any], case_id: str, actual: Dict[str, Any]) -> None:
    """Record the model's actual extraction JSON for a case.

    `actual` is the full extraction object (decision, task_title, actor, ...).
    This stores it under results['actuals'][case_id].
    """
    results.setdefault("actuals", {})[case_id] = actual


def _missing_fields_of(actual: Dict[str, Any]) -> List[str]:
    mf = actual.get("missing_fields", [])
    return list(mf) if isinstance(mf, list) else []


def score(data: Dict[str, Any], actuals: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Compare recorded actuals against expected values."""
    total = 0
    correct_dec = 0
    correct_full = 0
    failures = []

    for case in data["cases"]:
        cid = case["id"]
        if cid not in actuals:
            continue  # not evaluated
        total += 1
        actual = actuals[cid]
        act_dec = actual.get("decision")
        exp_dec = case["expected_decision"]

        dec_ok = act_dec == exp_dec
        if dec_dec_ok := dec_ok:
            correct_dec += 1

        exp_mf = set(case["expected_missing_fields"])
        act_mf = set(_missing_fields_of(actual))
        mf_ok = exp_mf == act_mf
        if dec_ok and mf_ok:
            correct_full += 1
        else:
            failures.append({
                "id": cid,
                "expected_decision": exp_dec,
                "actual_decision": act_dec,
                "expected_missing_fields": sorted(exp_mf),
                "actual_missing_fields": sorted(act_mf),
                "decision_match": dec_ok,
                "missing_fields_match": mf_ok,
            })

    decision_accuracy = (correct_dec / total) if total else 0.0
    full_accuracy = (correct_full / total) if total else 0.0
    return {
        "evaluated": total,
        "decision_correct": correct_dec,
        "full_correct": correct_full,
        "decision_accuracy": round(decision_accuracy, 4),
        "full_accuracy": round(full_accuracy, 4),
        "failures": failures,
    }


# --------------------------------------------------------------------------- #
# Modes
# --------------------------------------------------------------------------- #
def run_validate_only(data: Dict[str, Any]) -> int:
    problems = validate_dataset(data)
    print("=" * 70)
    print("DATASET VALIDATION (validate-only mode — no extraction performed)")
    print("=" * 70)
    n = len(data.get("cases", []))
    print(f"cases found: {n}")
    if problems:
        print(f"FAILED: {len(problems)} problem(s)")
        for p in problems:
            print("  -", p)
        return 1
    print("PASSED: dataset structure is valid for all cases.")
    return 0


def run_from_json(data: Dict[str, Any], path: str) -> int:
    with open(path, encoding="utf-8") as f:
        actuals = json.load(f)
    if not isinstance(actuals, dict):
        print(f"ERROR: --from-json file must map case id -> actual object ({path})")
        return 2
    # Validate dataset first (so structure errors are reported even when scoring).
    ds_problems = validate_dataset(data)
    if ds_problems:
        print("DATASET STRUCTURE PROBLEMS:")
        for p in ds_problems:
            print("  -", p)
    summary = score(data, actuals)
    results = {
        "skill": data.get("skill"),
        "source": path,
        "summary": summary,
        "actuals": actuals,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    _print_summary(summary)
    return 0 if summary["failures"] == [] else 1


def run_empty(data: Dict[str, Any]) -> int:
    """No actuals available yet: validate, write an empty results file, explain."""
    problems = validate_dataset(data)
    print("=" * 70)
    print("EVALUATION (no actual responses recorded yet)")
    print("=" * 70)
    if problems:
        print(f"DATASET PROBLEMS: {len(problems)}")
        for p in problems:
            print("  -", p)
    print("No --from-json supplied and no actual responses recorded.")
    print("Use record_response() in a runner, or pass --from-json <file> to score.")
    results = {
        "skill": data.get("skill"),
        "note": "no actual responses recorded; dataset-only run",
        "summary": {"evaluated": 0, "decision_correct": 0, "full_correct": 0,
                    "decision_accuracy": 0.0, "full_accuracy": 0.0, "failures": []},
        "actuals": {},
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Wrote (empty) results to {RESULTS_PATH}")
    return 0


def _print_summary(summary: Dict[str, Any]) -> None:
    print("=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print(f"evaluated cases : {summary['evaluated']}")
    print(f"decision correct: {summary['decision_correct']}/{summary['evaluated']} "
          f"(accuracy {summary['decision_accuracy']:.2%})")
    print(f"full correct    : {summary['full_correct']}/{summary['evaluated']} "
          f"(accuracy {summary['full_accuracy']:.2%})")
    if summary["failures"]:
        print("-" * 70)
        print("FAILED CASES:")
        for f in summary["failures"]:
            print(f"  {f['id']:<8} expected={f['expected_decision']:<18} "
                  f"actual={f['actual_decision']}")
            if not f["missing_fields_match"]:
                print(f"           missing_fields expected={f['expected_missing_fields']} "
                      f"actual={f['actual_missing_fields']}")
    print("-" * 70)
    print(f"Saved to {RESULTS_PATH}")


def category_counts(data: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for c in data["cases"]:
        counts[c["id"].split("-")[0]] = counts.get(c["id"].split("-")[0], 0) + 1
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate commitment-keeper extraction.")
    ap.add_argument("--validate-only", action="store_true",
                    help="only validate the dataset; perform no extraction")
    ap.add_argument("--from-json", metavar="PATH",
                    help="JSON file mapping case id -> actual extraction object")
    args = ap.parse_args()

    data = load_cases()

    if args.validate_only:
        return run_validate_only(data)

    if args.from_json:
        return run_from_json(data, args.from_json)

    return run_empty(data)


if __name__ == "__main__":
    raise SystemExit(main())
