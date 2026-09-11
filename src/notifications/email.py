from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send_email(subject: str, body: str) -> bool:
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    to_email = os.getenv("EMAIL_TO")

    if not all([smtp_username, smtp_password, to_email]):
        print("Email notification skipped: SMTP credentials not configured.")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_username
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(message)
        return True
    except Exception as exc:  # pragma: no cover - best effort integration
        print(f"Email send failed: {exc}")
        return False
