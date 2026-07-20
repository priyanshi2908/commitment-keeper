# Commitment Keeper — Evaluation

Automated evaluation setup for the **commitment-keeper** extraction skill. It checks
whether a commitment-extraction implementation classifies conversation snippets into
the four skill decisions (`stage`, `ignore`, `requires_acceptance`, `possible_completion`)
and reports the expected `missing_fields`.

This harness is **model-agnostic and does not call Hermes**. It validates the dataset,
records actual model outputs, scores them, and writes results.

## Files

```
evaluation/
  test_cases.json          # 30 labelled cases (the dataset)
  evaluate.py              # loader, validator, recorder, scorer
  evaluation_results.json  # written by evaluate.py (created on run)
  README.md
```

## Dataset shape

`test_cases.json` is `{ "skill", "schema", "case_count", "cases": [...] }`.
Each case:

```json
{
  "id": "EC-01",
  "authenticated_user": "Priyanshi",
  "current_datetime": "2026-07-17T18:15:00+05:30",
  "existing_commitment": null,
  "conversation": [
    { "speaker": "Rahul", "text": "Can you review the report today?" },
    { "speaker": "Priyanshi", "text": "Okay." }
  ],
  "expected_decision": "stage",
  "expected_missing_fields": [],
  "notes": "Clear request to the user + bare 'Okay' -> acceptance."
}
```

`conversation` is a **list of `{speaker, text}` objects** (matches the backend's
`ExtractionRequest`). `existing_commitment` is a string for `possible_completion`
cases, else `null`.

## Category breakdown (30 cases)

- 7 explicit commitments (EC-01..EC-07) → `stage`
- 5 contextual short acknowledgements (ACK-01..ACK-05)
  - clear request + "Okay"/"Sure" → `stage`
  - vague/ambiguous + "Okay"/"Got it" → `ignore`
  - "Okay, if I get time" → `requires_acceptance`
- 5 unaccepted requests/assignments (UA-01..UA-05) → `requires_acceptance`
- 4 casual/social statements (CS-01..CS-04) → `ignore`
- 3 hypothetical/conditional statements (HY-01..HY-03) → `ignore`
- 3 commitments without deadlines (ND-01..ND-03) → `stage` (deadline in `expected_missing_fields`)
- 3 possible-completion cases (PC-01..PC-03) → `possible_completion`

## Acknowledgement rules encoded in the dataset

1. "Okay"/"Sure"/"Got it"/"Alright" **counts as acceptance** when it directly follows
   a clear, concrete request addressed to the authenticated user.
   - e.g. "Can you review the report today?" → "Okay." ⇒ `stage`
2. It must **not** count as acceptance when:
   - the actor is unclear ("Someone should review this." → "Okay." ⇒ `ignore`);
   - the request is hypothetical;
   - the statement is merely a suggestion;
   - the response contains hesitation or a condition ("Okay, if I get time." ⇒ `requires_acceptance`).

## Usage

### 1. Validate the dataset only (no extraction)

```bash
python3 evaluate.py --validate-only
```

This checks every case's structure and reports problems. Use it before wiring any model.

### 2. Score against recorded actuals

Produce a JSON file mapping each case id to the model's actual extraction object, e.g.:

```json
{
  "EC-01": {"decision": "stage", "task_title": "...", "actor": {...}, "missing_fields": []},
  "ACK-03": {"decision": "ignore", "missing_fields": ["actor","action","deadline"]}
}
```

Then:

```bash
python3 evaluate.py --from-json actuals.json
```

This prints per-case accuracy, lists failed IDs with expected vs. actual decisions,
and writes `evaluation_results.json`.

### 3. Programmeuse use (record responses in code)

```python
from evaluate import load_cases, validate_dataset, record_response, score

data = load_cases()
assert not validate_dataset(data), "dataset invalid"
results = {}
for case in data["cases"]:
    actual = call_your_extractor(case)       # returns the full extraction object
    record_response(results, case["id"], actual)
summary = score(data, results["actuals"])
```

`record_response(results, case_id, actual)` stores the model's actual JSON under
`results["actuals"][case_id]`. `score()` compares decisions and missing_fields,
returns accuracy + a failures list. (You wire `call_your_extractor`; this package
never calls Hermes.)

## Output

`evaluation_results.json` contains `summary` (evaluated count, decision/full accuracy,
failures with expected vs. actual) and the recorded `actuals`.

## Notes

- This setup does **not** modify or execute the commitment-keeper skill itself.
- The backend's current `/extract` uses a naive mock extractor and will not match the
  skill's nuanced rules; `evaluation_results.json` will reflect that gap until a real
  extractor is wired in.
