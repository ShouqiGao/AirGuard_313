"""Service for AQI email subscription validation and persistence."""
import os
import re
from datetime import datetime
from database.connection import get_db
from services.utils import normalize_city

SUBSCRIPTION_TABLE_NAME = os.getenv("SUBSCRIPTION_TABLE_NAME", "email_subscriptions")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TIME_FORMAT = "%H:%M"


def validate_subscription_payload(payload, valid_cities):
    """Validate subscription input data and return normalized payload."""
    if not isinstance(payload, dict):
        return None, "Invalid request body"

    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    city_input = payload.get("city") or ""
    city = normalize_city(city_input)
    alert_time = (payload.get("alert_time") or "").strip()

    if not username:
        return None, "Username is required"
    if not email:
        return None, "Email is required"
    if not EMAIL_REGEX.match(email):
        return None, "Please provide a valid email address"
    if not city:
        return None, "City is required"

    normalized_valid_cities = {normalize_city(c) for c in valid_cities}
    if city not in normalized_valid_cities:
        return None, "Please select a valid city"

    if not alert_time:
        return None, "Alert time is required"

    try:
        datetime.strptime(alert_time, TIME_FORMAT)
    except ValueError:
        return None, "Alert time must be in HH:MM format"

    return {
        "username": username,
        "email": email,
        "city": city,
        "alert_time": alert_time,
        "timezone": "Asia/Kuala_Lumpur",
        "is_active": True,
    }, None


def subscription_exists(email, city, alert_time):
    """Check if active subscription exists for the same user/city/time."""
    db = get_db()
    result = (
        db.table(SUBSCRIPTION_TABLE_NAME)
        .select("id")
        .eq("email", email)
        .eq("city", city)
        .eq("alert_time", alert_time)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def create_subscription(data):
    """Create a new subscription record."""
    db = get_db()
    result = db.table(SUBSCRIPTION_TABLE_NAME).insert(data).execute()
    return result.data[0] if result.data else None


def get_due_subscriptions(current_time_hhmm):
    """Retrieve active subscriptions due for current local time."""
    db = get_db()
    result = (
        db.table(SUBSCRIPTION_TABLE_NAME)
        .select("id, username, email, city, alert_time, timezone")
        .eq("is_active", True)
        .eq("alert_time", current_time_hhmm)
        .execute()
    )
    return result.data or []


def record_notification_log(subscription_id, scheduled_for, status, error_message=None, payload_summary=None):
    """Persist notification delivery status."""
    table_name = os.getenv("NOTIFICATION_LOGS_TABLE_NAME", "notification_logs")
    db = get_db()
    data = {
        "subscription_id": subscription_id,
        "scheduled_for": scheduled_for,
        "status": status,
        "error_message": error_message,
        "payload_summary": payload_summary,
    }
    db.table(table_name).insert(data).execute()
