"""
Handles:
  - Sending emails via Gmail SMTP (TLS)
  - Checking Gmail inbox via IMAP for bounce / delivery failure notifications
"""

import imaplib
import smtplib
import time
import email as emaillib
import re
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from config import config


# ---------------------------------------------------------------------------
# SMTP sender
# ---------------------------------------------------------------------------

def send_email(
    to_address: str,
    subject: str,
    body: str,
    reply_to: Optional[str] = None,
) -> dict:
    """
    Sends a plain-text email from the configured Gmail account.

    Returns:
        {"success": True/False, "error": str or None, "sent_at": iso-timestamp}
    """
    sent_at = datetime.now(timezone.utc).isoformat()
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = config.gmail_address
        msg["To"] = to_address
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(config.gmail_address, config.gmail_app_password)
            server.sendmail(config.gmail_address, [to_address], msg.as_string())

        return {"success": True, "error": None, "sent_at": sent_at}

    except Exception as exc:
        return {"success": False, "error": str(exc), "sent_at": sent_at}


def send_to_all(
    email_list: list[str],
    subject: str,
    body: str,
    delay: float = None,
) -> list[dict]:
    """
    Sends the same email to every address in email_list.

    Returns a list of result dicts (one per address), each containing:
        {"to": str, "success": bool, "error": str|None, "sent_at": str}
    """
    delay = delay if delay is not None else config.send_delay_seconds
    results = []
    for addr in email_list:
        result = send_email(addr, subject, body)
        result["to"] = addr
        results.append(result)
        print(f"  {'✓' if result['success'] else '✗'} {addr}  {result.get('error') or ''}")
        if delay > 0:
            time.sleep(delay)
    return results


# ---------------------------------------------------------------------------
# IMAP bounce checker
# ---------------------------------------------------------------------------

# Subjects/senders that indicate a permanent delivery failure
_BOUNCE_SUBJECT_PATTERNS = [
    r"delivery status notification",
    r"undeliverable",
    r"mail delivery (failed|failure|subsystem)",
    r"returned mail",
    r"failure notice",
    r"delivery failure",
    r"non-?delivery",
]
_BOUNCE_SENDER_PATTERNS = [
    r"mailer-daemon",
    r"postmaster",
    r"mail delivery subsystem",
]
_BOUNCE_RE = re.compile(
    "|".join(_BOUNCE_SUBJECT_PATTERNS + _BOUNCE_SENDER_PATTERNS),
    re.IGNORECASE,
)


def _extract_bounced_address(raw_message: bytes) -> Optional[str]:
    """Try to pull the original recipient out of a bounce email."""
    msg = emaillib.message_from_bytes(raw_message)

    # Walk MIME parts looking for the original headers or DSN status
    for part in msg.walk():
        content_type = part.get_content_type()

        if content_type in ("message/delivery-status", "text/plain"):
            payload = part.get_payload(decode=True)
            if payload is None:
                payload_str = str(part.get_payload())
            else:
                payload_str = payload.decode("utf-8", errors="replace")

            # Look for "Final-Recipient" or "To:" inside the bounce body
            for line in payload_str.splitlines():
                m = re.search(
                    r"(?:final.recipient|original.recipient|to)[:\s]+[^<]*<?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?",
                    line,
                    re.IGNORECASE,
                )
                if m:
                    return m.group(1).lower()
    return None


def check_bounces(since_datetime: Optional[datetime] = None) -> list[str]:
    """
    Connects to Gmail via IMAP and returns a list of email addresses
    that generated a bounce / delivery failure notification received
    after `since_datetime` (defaults to last 24 h).

    Returns: list of bounced email addresses (lowercase).
    """
    if since_datetime is None:
        from datetime import timedelta
        since_datetime = datetime.now(timezone.utc) - timedelta(hours=24)

    # IMAP date format: DD-Mon-YYYY
    since_str = since_datetime.strftime("%d-%b-%Y")

    bounced: list[str] = []

    try:
        mail = imaplib.IMAP4_SSL(config.imap_host, config.imap_port)
        mail.login(config.gmail_address, config.gmail_app_password)
        mail.select("INBOX")

        _, msg_ids = mail.search(None, f'(SINCE "{since_str}")')
        ids = msg_ids[0].split() if msg_ids[0] else []

        for uid in ids:
            _, data = mail.fetch(uid, "(RFC822)")
            if not data or not data[0]:
                continue
            raw = data[0][1]

            msg = emaillib.message_from_bytes(raw)
            subject = msg.get("Subject", "")
            sender = msg.get("From", "")

            combined = subject + " " + sender
            if _BOUNCE_RE.search(combined):
                addr = _extract_bounced_address(raw)
                if addr:
                    bounced.append(addr)
                    print(f"  ↩ Bounce detected for: {addr}")

        mail.logout()

    except Exception as exc:
        print(f"  [IMAP error] {exc}")

    return list(set(bounced))
