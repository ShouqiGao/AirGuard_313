# EPIC 4.0 Implementation Plan — Daily AQI Email Subscription

This plan translates your Epic 4.0 into practical backend + frontend tasks for the current Flask codebase.

## 1) Scope Mapping (Stories → Components)

### User Story 4.1: Subscribe to Daily AQI Alerts
Build a simple, elderly-friendly subscription flow:
- Frontend form section on home page (or separate `/subscribe` page).
- Backend API endpoint to validate and store subscriptions.
- Database table for subscriptions.

### User Story 4.2: Receive Daily AQI Notification Emails
Build scheduled outbound notifications:
- Daily scheduler job that checks due subscribers.
- AQI/weather data fetch for each subscriber city.
- Email formatter + sender service.
- Delivery log table for observability.

---

## 2) Data Model (Supabase/PostgreSQL)

Add two tables.

### `email_subscriptions`
Core subscriber records.

Suggested fields:
- `id` UUID PK
- `username` TEXT NOT NULL
- `email` TEXT NOT NULL
- `city` TEXT NOT NULL
- `alert_time` TIME NOT NULL (local Malaysia time)
- `timezone` TEXT NOT NULL DEFAULT `Asia/Kuala_Lumpur`
- `is_active` BOOLEAN NOT NULL DEFAULT TRUE
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

Suggested constraints/indexes:
- Unique active subscription per email+city+alert_time (or just email, based on product rule).
- Index on `(is_active, alert_time)` to support scheduler queries.
- Basic email format check constraint (lightweight regex).

### `notification_logs`
Track delivery attempts.

Suggested fields:
- `id` UUID PK
- `subscription_id` UUID FK → `email_subscriptions.id`
- `scheduled_for` TIMESTAMPTZ NOT NULL
- `sent_at` TIMESTAMPTZ
- `status` TEXT NOT NULL (`sent`, `failed`, `skipped`)
- `error_message` TEXT NULL
- `payload_summary` JSONB NULL (aqi, pollutant, city)

Suggested constraints/indexes:
- Unique `(subscription_id, scheduled_for)` to prevent duplicate sends.
- Index on `(status, scheduled_for)` for monitoring.

---

## 3) Backend API Design (Flask)

### New endpoint: `POST /api/subscriptions`
Request body:
```json
{
  "username": "Tan Ah Kow",
  "email": "example@email.com",
  "city": "Kuala Lumpur",
  "alert_time": "08:30"
}
```

Validation rules (acceptance criteria aligned):
- Required: `username`, `email`, `city`, `alert_time`
- Email format valid
- City must be valid (prefer whitelist from `config/settings.json` first)
- `alert_time` must be HH:MM 24-hour format

Response examples:
- 201 success: `{"ok": true, "message": "Subscription registered successfully."}`
- 400 validation: field-specific message
- 409 conflict: existing subscription (optional rule)

### Optional management endpoints (recommended)
- `GET /api/subscriptions/<email>` for support/admin checking
- `DELETE /api/subscriptions/<id>` unsubscribe
- `PATCH /api/subscriptions/<id>` edit city/time

---

## 4) Scheduler & Delivery Flow

Use **APScheduler** inside Flask process for MVP, then migrate to worker/cron in production.

### Job strategy
- Run every minute.
- Determine current Malaysia local time (`Asia/Kuala_Lumpur`).
- Query active subscribers whose `alert_time` equals current minute.
- For each subscriber:
  1. Fetch AQI data (reuse `services/aqi_service.py` patterns).
  2. Build email content: city, AQI value, main pollutant, level label.
  3. Send via provider (SendGrid, Resend, SES, or SMTP).
  4. Insert `notification_logs` record.

### Idempotency
- Before send, check if `(subscription_id, scheduled_for)` exists.
- If exists, skip send to prevent duplicates after restarts/retries.

---

## 5) Email Content for Elderly Users

Keep short, readable, and consistent daily.

Required content per acceptance criteria:
- City
- AQI value
- Main pollutant

Recommended UX:
- Simple level icon + color word in subject/body (e.g., `🟢 Good`, `🟠 Moderate`, `🔴 Unhealthy`).
- Large-font HTML email + plain-text fallback.
- One-line health advice from existing AQI classification in `settings.json`.

Example subject:
- `AirGuard Daily Alert — Kuala Lumpur AQI 72 (🟠 Moderate)`

---

## 6) Frontend UX Changes (Elderly-friendly)

### Form fields
- Username
- Email
- City (dropdown)
- Alert time (time picker)

### Accessibility and usability
- Large input height and buttons.
- High contrast labels and helper text.
- Placeholder examples:
  - `Enter username`
  - `example@email.com`
  - `08:30`
- Inline field-level validation messages.
- Clear success state banner: `Subscription registered successfully.`

### Progressive enhancement
- Client-side validation first, backend validation always enforced.
- Disable submit button during request; show loading text.

---

## 7) Security, Privacy, and Reliability

- Store email credentials in env vars only.
- Never log SMTP/API keys.
- Add rate limit for subscription endpoint (basic anti-spam).
- Use double opt-in later (Phase 2) for consent assurance.
- Add unsubscribe link token later (Phase 2) for compliance.

---

## 8) Implementation Phases

### Phase 1 (MVP — 2 to 4 days)
1. DB migration for `email_subscriptions` + `notification_logs`.
2. `POST /api/subscriptions` with full validation.
3. Frontend form and success/error handling.
4. Scheduler (minute tick) + simple email template.
5. Manual end-to-end test with 1-2 test recipients.

### Phase 2 (Hardening — 2 to 3 days)
1. Duplicate prevention + idempotency lock checks.
2. Retry policy for transient send failures.
3. Admin/support visibility endpoint(s).
4. Better HTML email template + Malay/English language option.

### Phase 3 (Production readiness)
1. Move scheduler to dedicated worker or cron-triggered endpoint.
2. Delivery metrics dashboard and alerting.
3. Double opt-in and self-service unsubscribe/update flow.

---

## 9) Definition of Done Checklist

- [ ] Form contains username, email, city, alert_time.
- [ ] Placeholders implemented exactly per story.
- [ ] Required-field, email, and city validation enforced server-side.
- [ ] Success message shown on valid submit.
- [ ] Daily email includes city, AQI, and main pollutant.
- [ ] Emails are dispatched automatically at subscriber time.
- [ ] Duplicate send prevention verified.
- [ ] Logs available for sent/failed events.

---

## 10) Suggested File-Level Changes in Current Repo

- `database/schema.sql`
  - Add subscription and notification tables + indexes.
- `services/`
  - Add `subscription_service.py` (validation + CRUD).
  - Add `email_service.py` (provider integration + template rendering).
  - Add `scheduler_service.py` (timed dispatch).
- `app.py`
  - Register `POST /api/subscriptions`.
  - Initialize scheduler on app startup (guarded for single process).
- `templates/index.html` and `static/main.js`
  - Add and wire subscription form.
- `static/style.css`
  - Add elderly-friendly spacing, input/button sizing for the new form.

This plan keeps your implementation incremental while meeting all listed acceptance criteria.
