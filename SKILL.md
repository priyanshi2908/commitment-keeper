---
name: commitment-keeper
description: Extraction-only MVP. Analyse conversation text and return a structured commitment CANDIDATE. Does NOT save, store, complete, schedule, or send anything. Use when the user wants commitments detected from messages, transcripts, or statements for later human review.
---

# Commitment Keeper (Extraction MVP)

This skill detects and classifies commitment candidates in conversation text. It is
**extraction-only**: it reads text and emits a structured JSON candidate. It never
acts on the result.

## Hard constraints — the skill must NEVER

- directly save a commitment as a final task
- append records to `commitments.jsonl`
- mark a task complete automatically
- create cron jobs
- send messages / notifications
- call external task managers (Todoist, Linear, reminders, etc.)

The output is a candidate for human review. Persisting, staging, or completing is
someone else's job (or a later, separate skill).

## Input

Raw conversation text (one or more messages). Identify the **authenticated user**
(= "the user") separately from other participants.

## Supported decisions (exactly these four)

- `stage`
  The authenticated user clearly **made or accepted** a concrete commitment.
- `ignore`
  No real operational commitment is present.
- `requires_acceptance`
  Someone assigns or requests work from the authenticated user, but the user has
  **not** accepted it.
- `possible_completion`
  A new message may be **evidence that an existing commitment was completed**.

## Decision rules

**stage** — use when the authenticated user clearly made or accepted a concrete
commitment. Requires: an identifiable actor (the user), a concrete actionable task,
accepted responsibility, and an explicit/inferable deadline when available.

**ignore** — use when there is no real operational commitment: casual future wishes,
vague suggestions, hypothetical/conditional statements, unaccepted requests,
acknowledgements ("okay") with unclear responsibility, and social plans without a
concrete operational obligation.

**requires_acceptance** — use when someone assigns or requests work from the
authenticated user but the user has not accepted it. The actor is "other" (the
assigner); the user is the prospective beneficiary/assignee, not yet obligated.

**possible_completion** — use when a new message may be evidence that an existing
commitment was completed (e.g. "sent it", "done", "shipped the report"). This does
not auto-close anything; it only flags possible completion for review.

## What makes a strong commitment

A strong commitment normally contains:
- an identifiable actor
- a concrete actionable task
- accepted responsibility
- an explicit or inferable deadline when available

## Avoiding false positives

Do NOT emit `stage` for:
- casual future wishes ("I wish I could…", "someday I'll…")
- vague suggestions ("maybe we should look into…")
- hypothetical or conditional statements ("if we had time, I'd…")
- unaccepted requests (someone asks the user; user hasn't said yes)
- social plans without a concrete operational obligation ("let's grab coffee")

(For short acknowledgements like "okay"/"sure"/"got it"/"alright", see the
**Context-sensitive acknowledgement rule** below — they are NOT always vague and
NOT always explicit.)

## Context-sensitive acknowledgement rule

Words such as "okay", "sure", "got it", and "alright" are **not** inherently vague
or inherently explicit. Classify them by context:

Treat the acknowledgement as **acceptance** (`stage`) ONLY when ALL hold:
- it directly follows a clear request or assignment;
- the authenticated user is clearly the intended actor;
- the requested action is concrete;
- there is no refusal, hesitation, condition, or ambiguity in the reply.

If any condition fails, do NOT treat it as acceptance:
- If the preceding message is not a clear request/assignment aimed at the user
  (e.g. "Someone should review this."), the acknowledgement is `ignore`.
- If the acknowledgement adds a condition, hesitation, or deferral (e.g. "Okay,
  maybe later."), it is `requires_acceptance`, not `stage`.

Illustrative mappings:
- "Can you review the report today?" → "Okay."  ⇒ `stage`
- "Priyanshi, please send the invoice tomorrow." → "Sure."  ⇒ `stage`
- "Someone should review this." → "Okay."  ⇒ `ignore`
- "We may need to revisit this later." → "Got it."  ⇒ `ignore`
- "Can you review this?" → "Okay, maybe later."  ⇒ `requires_acceptance`

When signals are weak, prefer `ignore` or `requires_acceptance` over `stage`.

## Output format

Return **valid JSON only** — no markdown fences, no prose, no explanation outside the
JSON object. The object must conform to `schemas/commitment.schema.json`.

Top-level fields (exactly these):

- `decision`: one of `stage` | `ignore` | `requires_acceptance` | `possible_completion`
- `task_title`: short actionable title (string; may be empty for `ignore`)
- `actor`: `{ "type": "user" | "other" | "team" | "unknown", "name": string | null }`
- `beneficiary`: string | null
- `due_at`: ISO-8601 datetime string | null
- `due_text`: raw deadline phrasing from the text (string; empty if none)
- `confidence`: number 0.0–1.0
- `source_evidence`: verbatim excerpt supporting the extraction
- `signals`: `{ "actionable_verb": bool, "actor_identified": bool, "timeline_present": bool, "explicit_acceptance": bool }`
- `missing_fields`: array of only `actor` | `action` | `deadline` | `beneficiary`

### Examples of valid output

`stage`:
{"decision":"stage","task_title":"Send Q3 report to Priya","actor":{"type":"user","name":null},"beneficiary":"Priya","due_at":"2026-07-24T17:00:00","due_text":"by Friday","confidence":0.95,"source_evidence":"I'll send the Q3 report to Priya by Friday","signals":{"actionable_verb":true,"actor_identified":true,"timeline_present":true,"explicit_acceptance":true},"missing_fields":[]}

`requires_acceptance`:
{"decision":"requires_acceptance","task_title":"Review the open PR","actor":{"type":"other","name":"Bob"},"beneficiary":"user","due_at":null,"due_text":"","confidence":0.9,"source_evidence":"Bob: can you review the PR?","signals":{"actionable_verb":true,"actor_identified":true,"timeline_present":false,"explicit_acceptance":false},"missing_fields":["deadline"]}

## Schema

Validate the emitted JSON against `schemas/commitment.schema.json` (draft-07) before
returning it. If it fails, fix the object, do not emit invalid JSON.

## Examples

See `references/examples.md` for worked extraction transcripts (explicit promise,
accepted request, unaccepted assignment, casual suggestion, hypothetical statement,
commitment without deadline, possible completion).
