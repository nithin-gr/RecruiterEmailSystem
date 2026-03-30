import os
from dataclasses import dataclass


@dataclass
class Config:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gmail_address: str = os.getenv("GMAIL_ADDRESS", "")
    # Use an App Password (not your real Gmail password).
    # Generate at: https://myaccount.google.com/apppasswords
    gmail_app_password: str = os.getenv("GMAIL_APP_PASSWORD", "")

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993

    # How many seconds to wait between individual sends to avoid rate limits
    send_delay_seconds: float = 2.0

    excel_file: str = "recruiter_outreach.xlsx"


config = Config()
