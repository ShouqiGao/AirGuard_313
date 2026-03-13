"""Lightweight scheduler to dispatch due AQI email alerts every minute."""
import os
import threading
import time
from datetime import datetime, timedelta, timezone

from services.aqi_service import get_aqi
from services.subscription_service import (
    get_due_subscriptions,
    record_notification_log,
)
from services.email_service import build_email_content, send_email

SCHEDULER_TZ = timezone(timedelta(hours=8))
_dispatch_lock = threading.Lock()
_scheduler_started = False


def _run_dispatch_once(config):
    now_local = datetime.now(SCHEDULER_TZ)
    current_time = now_local.strftime("%H:%M")
    scheduled_for = now_local.isoformat()

    try:
        subscriptions = get_due_subscriptions(current_time)
    except Exception as exc:
        print(f"⚠️  Scheduler query failed: {exc}")
        return

    for sub in subscriptions:
        try:
            aqi_result = get_aqi(sub["city"], config)
            if not aqi_result:
                record_notification_log(
                    sub["id"],
                    scheduled_for,
                    "failed",
                    "No AQI data available",
                )
                continue

            subject, text_body, html_body = build_email_content(sub, aqi_result)
            ok, send_error = send_email(sub["email"], subject, text_body, html_body)

            status = "sent" if ok else "failed"
            record_notification_log(
                sub["id"],
                scheduled_for,
                status,
                send_error,
                {
                    "city": aqi_result.get("city"),
                    "aqi": aqi_result.get("aqi"),
                    "dominentpol": aqi_result.get("dominentpol"),
                },
            )
        except Exception as exc:
            record_notification_log(sub["id"], scheduled_for, "failed", str(exc))


def _scheduler_loop(config):
    last_run_minute = None
    while True:
        now_local = datetime.now(SCHEDULER_TZ)
        minute_token = now_local.strftime("%Y-%m-%d %H:%M")
        if minute_token != last_run_minute:
            with _dispatch_lock:
                _run_dispatch_once(config)
            last_run_minute = minute_token
        time.sleep(1)


def start_scheduler(config):
    """Start scheduler thread once when enabled by environment variable."""
    global _scheduler_started
    enabled = os.getenv("ENABLE_EMAIL_SCHEDULER", "false").lower() == "true"
    if not enabled or _scheduler_started:
        return

    thread = threading.Thread(target=_scheduler_loop, args=(config,), daemon=True)
    thread.start()
    _scheduler_started = True
    print("✓ Email scheduler started")
