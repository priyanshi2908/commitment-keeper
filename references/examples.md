# Commitment Keeper — Extraction Examples

This skill is extraction-only. Each example shows the INPUT text and the exact JSON
the skill should OUTPUT (no markdown fences, no prose). The user is the authenticated
user. Validate every output against `schemas/commitment.schema.json`.

---

## 1. Explicit promise  →  decision: stage

Input: "I'll send the Q3 report to Priya by Friday."

Output:
{"decision":"stage","task_title":"Send Q3 report to Priya","actor":{"type":"user","name":null},"beneficiary":"Priya","due_at":"2026-07-24T17:00:00","due_text":"by Friday","confidence":0.96,"source_evidence":"I'll send the Q3 report to Priya by Friday","signals":{"actionable_verb":true,"actor_identified":true,"timeline_present":true,"explicit_acceptance":true},"missing_fields":[]}

---

## 2. Accepted request  →  decision: stage

Input: "Sure, I'll take care of the deployment tonight."

Output:
{"decision":"stage","task_title":"Handle the deployment","actor":{"type":"user","name":null},"beneficiary":null,"due_at":"2026-07-17T23:59:59","due_text":"tonight","confidence":0.93,"source_evidence":"Sure, I'll take care of the deployment tonight","signals":{"actionable_verb":true,"actor_identified":true,"timeline_present":true,"explicit_acceptance":true},"missing_fields":["beneficiary"]}

---

## 3. Unaccepted assignment  →  decision: requires_acceptance

Input: "Bob: can you review the PR before the standup?"

Output:
{"decision":"requires_acceptance","task_title":"Review the PR before standup","actor":{"type":"other","name":"Bob"},"beneficiary":"user","due_at":"2026-07-17T09:00:00","due_text":"before the standup","confidence":0.9,"source_evidence":"Bob: can you review the PR before the standup?","signals":{"actionable_verb":true,"actor_identified":true,"timeline_present":true,"explicit_acceptance":false},"missing_fields":[]}

Note: The user has NOT said yes. The obligated actor is Bob (the assigner / requester);
the user is the prospective assignee. Do not classify as `stage`.

---

## 4. Casual suggestion  →  decision: ignore

Input: "Maybe we should look into a redesign sometime."

Output:
{"decision":"ignore","task_title":"","actor":{"type":"unknown","name":null},"beneficiary":null,"due_at":null,"due_text":"","confidence":0.85,"source_evidence":"Maybe we should look into a redesign sometime","signals":{"actionable_verb":false,"actor_identified":false,"timeline_present":false,"explicit_acceptance":false},"missing_fields":["actor","action","deadline"]}

Note: Vague, no accepted responsibility, no concrete obligation → `ignore`.

---

## 5. Hypothetical statement  →  decision: ignore

Input: "If we had the budget, I'd hire another engineer."

Output:
{"decision":"ignore","task_title":"","actor":{"type":"unknown","name":null},"beneficiary":null,"due_at":null,"due_text":"","confidence":0.9,"source_evidence":"If we had the budget, I'd hire another engineer","signals":{"actionable_verb":false,"actor_identified":false,"timeline_present":false,"explicit_acceptance":false},"missing_fields":["actor","action","deadline"]}

Note: Conditional/hypothetical → not a real commitment.

---

## 6. Commitment without deadline  →  decision: stage

Input: "I'm responsible for writing the onboarding doc."

Output:
{"decision":"stage","task_title":"Write the onboarding doc","actor":{"type":"user","name":null},"beneficiary":null,"due_at":null,"due_text":"","confidence":0.88,"source_evidence":"I'm responsible for writing the onboarding doc","signals":{"actionable_verb":true,"actor_identified":true,"timeline_present":false,"explicit_acceptance":true},"missing_fields":["deadline"]}

Note: Accepted responsibility + concrete task, but no deadline → still `stage`;
report `deadline` in `missing_fields`.

---

## 7. Possible completion  →  decision: possible_completion

Input (new message after a known open commitment): "Just sent the Q3 report to Priya."

Output:
{"decision":"possible_completion","task_title":"Send Q3 report to Priya","actor":{"type":"user","name":null},"beneficiary":"Priya","due_at":null,"due_text":"","confidence":0.8,"source_evidence":"Just sent the Q3 report to Priya","signals":{"actionable_verb":true,"actor_identified":true,"timeline_present":false,"explicit_acceptance":true},"missing_fields":[]}

Note: This may be evidence an existing commitment was completed. The skill only
FLAGS it; it does not auto-close anything.

---

## 8. Context-sensitive acknowledgements

Short replies like "okay", "sure", "got it", "alright" are classified by context,
not by the word alone. See the **Context-sensitive acknowledgement rule** in SKILL.md.

### 8a. Clear request + "Okay"  →  decision: stage

Input:
Rahul: Can you review the report today?
Priyanshi: Okay.

Output:
{"decision":"stage","task_title":"Review the report","actor":{"type":"user","name":"Priyanshi"},"beneficiary":"Rahul","due_at":"2026-07-17T23:59:59+05:30","due_text":"today","confidence":0.9,"source_evidence":"Priyanshi: Okay.","signals":{"actionable_verb":true,"actor_identified":true,"timeline_present":true,"explicit_acceptance":true},"missing_fields":[]}

Note: Acknowledgement directly follows a clear request aimed at the user, action is
concrete, no condition → acceptance (`stage`).

### 8b. Clear assignment + "Sure"  →  decision: stage

Input:
Rahul: Priyanshi, please send the invoice tomorrow.
Priyanshi: Sure.

Output:
{"decision":"stage","task_title":"Send the invoice","actor":{"type":"user","name":"Priyanshi"},"beneficiary":"Rahul","due_at":"2026-07-18T23:59:59+05:30","due_text":"tomorrow","confidence":0.9,"source_evidence":"Priyanshi: Sure.","signals":{"actionable_verb":true,"actor_identified":true,"timeline_present":true,"explicit_acceptance":true},"missing_fields":[]}

### 8c. Vague suggestion + "Okay"  →  decision: ignore

Input:
Rahul: Someone should review this.
Priyanshi: Okay.

Output:
{"decision":"ignore","task_title":"","actor":{"type":"unknown","name":null},"beneficiary":null,"due_at":null,"due_text":"","confidence":0.8,"source_evidence":"Priyanshi: Okay.","signals":{"actionable_verb":false,"actor_identified":false,"timeline_present":false,"explicit_acceptance":false},"missing_fields":["actor","action","deadline"]}

Note: Preceding message is not a clear request/assignment aimed at the user → `ignore`.

### 8d. Ambiguous plan + "Got it"  →  decision: ignore

Input:
Rahul: We may need to revisit this later.
Priyanshi: Got it.

Output:
{"decision":"ignore","task_title":"","actor":{"type":"unknown","name":null},"beneficiary":null,"due_at":null,"due_text":"","confidence":0.8,"source_evidence":"Priyanshi: Got it.","signals":{"actionable_verb":false,"actor_identified":false,"timeline_present":false,"explicit_acceptance":false},"missing_fields":["actor","action","deadline"]}

### 8e. Request + conditional "Okay"  →  decision: requires_acceptance

Input:
Rahul: Can you review this?
Priyanshi: Okay, maybe later.

Output:
{"decision":"requires_acceptance","task_title":"Review this","actor":{"type":"other","name":"Rahul"},"beneficiary":"Rahul","due_at":null,"due_text":"maybe later","confidence":0.85,"source_evidence":"Priyanshi: Okay, maybe later.","signals":{"actionable_verb":true,"actor_identified":true,"timeline_present":false,"explicit_acceptance":false},"missing_fields":["deadline"]}

Note: "Okay, maybe later" adds a condition/deferral → not acceptance → `requires_acceptance`.
