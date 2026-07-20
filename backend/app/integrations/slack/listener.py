"""Slack Socket Mode listener for Commitment Keeper.

Run with: python -m app.integrations.slack.listener
Requires the FastAPI backend (uvicorn) already running.
"""
from __future__ import annotations

import logging
logging.basicConfig(level=logging.INFO)

import re
from datetime import datetime, timezone

import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.config import get_settings
from app.repositories import commitments as commitments_repo

settings = get_settings()

if not settings.slack_bot_token or not settings.slack_app_token:
    raise SystemExit("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in .env")

app = App(token=settings.slack_bot_token)

CONTEXT: dict[str, list[dict]] = {}
MAX_CONTEXT = 6

APPROVE_RE = re.compile(r"^approve\s+(\d+)$", re.IGNORECASE)
DISMISS_RE = re.compile(r"^dismiss\s+(\d+)$", re.IGNORECASE)


def channel_allowed(channel_id: str) -> bool:
    if not settings.slack_allowed_channels:
        return True
    return channel_id in settings.slack_allowed_channels


@app.event("message")
def handle_message(event, say, logger):
    logger.info(f"RAW EVENT: {event}")
    if event.get("bot_id"):
        return
    if event.get("subtype") in {"message_changed", "message_deleted"}:
        return

    channel = event.get("channel")
    text = (event.get("text") or "").strip()

    if not channel_allowed(channel):
        return

    m = APPROVE_RE.match(text)
    if m:
        row = commitments_repo.update_status(int(m.group(1)), "approved")
        say(f"Approved commitment #{m.group(1)}." if row else f"No commitment #{m.group(1)} found.")
        return
    m = DISMISS_RE.match(text)
    if m:
        row = commitments_repo.update_status(int(m.group(1)), "dismissed")
        say(f"Dismissed commitment #{m.group(1)}." if row else f"No commitment #{m.group(1)} found.")
        return

    buf = CONTEXT.setdefault(channel, [])
    buf.append({"speaker": event.get("user", "unknown"), "text": text})
    CONTEXT[channel] = buf[-MAX_CONTEXT:]

    payload = {
        "authenticated_user": settings.slack_authenticated_user,
        "current_datetime": datetime.now(timezone.utc).isoformat(),
        "conversation": CONTEXT[channel],
    }

    try:
        resp = requests.post(
            f"{settings.backend_base_url}/extract",
            json=payload,
            timeout=settings.hermes_timeout_seconds + 5,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error(f"/extract call failed: {exc}")
        return

    extraction = resp.json()
    if extraction.get("decision") != "stage":
        return

    commitment_id = commitments_repo.create_commitment(extraction, source_channel=channel)
    say(
        f":clipboard: *Commitment detected* (#{commitment_id})\n"
        f"> {extraction.get('task_title')}\n"
        f"Due: {extraction.get('due_text') or 'not specified'}\n"
        f"Confidence: {extraction.get('confidence'):.2f}\n"
        f"Reply `approve {commitment_id}` or `dismiss {commitment_id}`."
    )


if __name__ == "__main__":
    handler = SocketModeHandler(app, settings.slack_app_token)
    handler.start()
