"""Failure alerting for Airflow tasks (used as `on_failure_callback`)."""

import logging
import os

import requests

log = logging.getLogger(__name__)


def format_failure(context: dict) -> str:
    ti = context.get("task_instance")
    exception = context.get("exception")
    return (
        f":rotating_light: DZ News Pulse - task failed\n"
        f"DAG: {ti.dag_id} | task: {ti.task_id} | try {ti.try_number}\n"
        f"Run: {context.get('run_id')}\n"
        f"Error: {str(exception)[:300]}"
    )


def notify_failure(context: dict) -> None:
    """Post to ALERT_WEBHOOK_URL if configured (Slack/Discord compatible), else just log."""
    message = format_failure(context)
    log.error(message)

    url = os.getenv("ALERT_WEBHOOK_URL")
    if not url:
        return
    try:
        # "text" is read by Slack, "content" by Discord.
        requests.post(url, json={"text": message, "content": message}, timeout=10)
    except requests.RequestException:  # an alert must never crash the callback
        log.exception("Could not deliver the failure alert")
