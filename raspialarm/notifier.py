"""Notifier module – handles event logging and optional email alerts.

Notifications are always written to the Python logging infrastructure.
Email delivery is attempted only when SMTP credentials are supplied via the
application configuration.
"""

import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Notifier:
    """Sends alarm notifications through multiple channels.

    Parameters
    ----------
    log_file:
        Optional path to a plain-text log file that records every alarm event.
    smtp_host:
        SMTP server hostname for email alerts (e.g. ``"smtp.gmail.com"``).
    smtp_port:
        SMTP server port.  Defaults to 465 (SSL).
    smtp_user:
        Sender email address / SMTP username.
    smtp_password:
        SMTP authentication password.
    recipient_email:
        Destination address for alarm email messages.
    """

    def __init__(
        self,
        log_file: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: int = 465,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        recipient_email: Optional[str] = None,
    ) -> None:
        self.log_file = Path(log_file) if log_file else None
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.recipient_email = recipient_email

        self._email_enabled = all(
            [smtp_host, smtp_user, smtp_password, recipient_email]
        )
        if self._email_enabled:
            logger.info("Email notifications enabled → %s", recipient_email)
        else:
            logger.info("Email notifications disabled (incomplete SMTP config)")

    def notify(self, message: str) -> None:
        """Dispatch *message* through all configured channels."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}"

        logger.warning(entry)
        self._write_log(entry)

        if self._email_enabled:
            self._send_email(subject="RaspiAlarm – Motion Detected", body=entry)

    def _write_log(self, entry: str) -> None:
        if self.log_file is None:
            return
        try:
            with self.log_file.open("a", encoding="utf-8") as fh:
                fh.write(entry + "\n")
        except OSError as exc:
            logger.error("Failed to write alarm log: %s", exc)

    def _send_email(self, subject: str, body: str) -> None:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = self.recipient_email

        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(
                self.smtp_host, self.smtp_port, context=context
            ) as server:
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, self.recipient_email, msg.as_string())
            logger.info("Email alert sent to %s", self.recipient_email)
        except smtplib.SMTPException as exc:
            logger.error("Failed to send email alert: %s", exc)
