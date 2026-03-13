"""Service for formatting and sending AQI notification emails."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def get_level_icon(level):
    """Map AQI level to simple icon cue."""
    if level == "Good":
        return "🟢"
    if level == "Moderate":
        return "🟠"
    return "🔴"


def build_email_content(subscription, aqi_result):
    """Build subject, text, and html message content."""
    city = aqi_result.get("city", subscription["city"])
    aqi_value = aqi_result.get("aqi", "N/A")
    pollutant = aqi_result.get("dominentpol", "Unknown")
    level = aqi_result.get("level", "Unknown")
    advice = aqi_result.get("advice", "Please follow local health advice.")
    icon = get_level_icon(level)

    subject = f"AirGuard Daily Alert — {city} AQI {aqi_value} ({icon} {level})"

    text = (
        f"Hello {subscription['username']},\n\n"
        f"Your daily AirGuard alert:\n"
        f"City: {city}\n"
        f"AQI: {aqi_value}\n"
        f"Main pollutant: {pollutant}\n"
        f"Level: {icon} {level}\n\n"
        f"Health tip: {advice}\n"
    )

    html = f"""
    <html>
      <body style=\"font-family: Arial, sans-serif; font-size: 18px; line-height: 1.6;\">
        <p>Hello {subscription['username']},</p>
        <p><strong>Your daily AirGuard alert:</strong></p>
        <ul>
          <li><strong>City:</strong> {city}</li>
          <li><strong>AQI:</strong> {aqi_value}</li>
          <li><strong>Main pollutant:</strong> {pollutant}</li>
          <li><strong>Level:</strong> {icon} {level}</li>
        </ul>
        <p><strong>Health tip:</strong> {advice}</p>
      </body>
    </html>
    """

    return subject, text, html


def send_email(to_email, subject, text_body, html_body):
    """Send email over SMTP. Returns (ok, error_message)."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("EMAIL_FROM", smtp_user or "no-reply@airguard.local")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not smtp_host or not smtp_user or not smtp_password:
        return False, "SMTP credentials are not configured"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = email_from
    message["To"] = to_email
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, [to_email], message.as_string())
        return True, None
    except Exception as exc:
        return False, str(exc)
