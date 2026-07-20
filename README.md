# Commitment Keeper

Commitment Keeper is a Hermes-powered agent that detects actionable commitments
from conversations and returns structured candidates for human approval.

## Current MVP

- Hermes skill for commitment extraction
- Four supported decisions:
  - `stage`
  - `ignore`
  - `requires_acceptance`
  - `possible_completion`
- JSON Schema validation
- FastAPI `/extract` endpoint
- Automated evaluation suite
- 30/30 curated evaluation cases passing
- Local Hermes subprocess integration

## Architecture

```text
Conversation
    ↓
FastAPI /extract
    ↓
Hermes Agent
    ↓
commitment-keeper skill
    ↓
Schema validation
    ↓
Structured commitment candidate

