"""
Recruiter Email Outreach System
================================
Usage:
  python main.py send    - interactive wizard to send outreach
  python main.py bounces - check inbox for bounces and update Excel
  python main.py summary - print confirmed emails from Excel
"""

import sys
import textwrap
from datetime import datetime, timezone

from config import config
from email_generator import generate_email_combinations
from email_composer import compose_email
from gmail_client import send_to_all, check_bounces
from excel_tracker import save_outreach_attempt, apply_bounce_results, print_confirmed_emails


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _input_multiline(prompt: str) -> str:
    """Reads multi-line input until the user enters END on a blank line."""
    print(prompt)
    print("(Paste text, then type END on a new line and press Enter)")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def _confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() == "y"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_send():
    print("\n=== Recruiter Outreach Wizard ===\n")

    # --- Validate credentials ---
    if not config.openai_api_key:
        sys.exit("ERROR: Set OPENAI_API_KEY environment variable first.")
    if not config.gmail_address or not config.gmail_app_password:
        sys.exit(
            "ERROR: Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables.\n"
            "       Generate an App Password at: https://myaccount.google.com/apppasswords"
        )

    # --- Recruiter info ---
    recruiter_name = input("Recruiter / Hiring Manager full name: ").strip()
    recruiter_title = input("Their title (e.g. Senior Recruiter): ").strip()
    company = input("Company name: ").strip()
    company_domain = input("Company email domain (leave blank to auto-detect, e.g. acme.com): ").strip() or None

    # --- Job info ---
    role_title = input("Role you are applying for: ").strip()
    job_description = _input_multiline("\nPaste the job description:")
    resume_text = _input_multiline("\nPaste your resume (plain text):")
    sender_name = input("\nYour full name (for the email sign-off): ").strip()

    # --- Step 1: Generate email combinations ---
    print("\n[1/4] Generating email combinations via GPT-4o …")
    gen = generate_email_combinations(recruiter_name, company, company_domain)
    domain = gen["domain"]
    candidates = gen["emails"]
    print(f"      Domain inferred: {domain}")
    print(f"      {len(candidates)} candidate addresses generated:")
    for e in candidates:
        print(f"        {e}")

    if not _confirm("\nProceed with these addresses?"):
        print("Aborted.")
        return

    # --- Step 2: Compose email ---
    print("\n[2/4] Composing outreach email via GPT-4o …")
    composed = compose_email(
        recruiter_name=recruiter_name,
        recruiter_title=recruiter_title,
        company=company,
        role_title=role_title,
        job_description=job_description,
        resume_text=resume_text,
        sender_name=sender_name,
    )
    subject = composed["subject"]
    body = composed["body"]

    print(f"\n--- Subject ---\n{subject}")
    print(f"\n--- Body ---\n{textwrap.indent(body, '  ')}\n")

    if not _confirm("Send this email to all candidates?"):
        print("Aborted.")
        return

    # --- Step 3: Send ---
    print(f"\n[3/4] Sending to {len(candidates)} addresses …")
    results = send_to_all(candidates, subject, body, delay=config.send_delay_seconds)

    # --- Step 4: Save to Excel ---
    print("\n[4/4] Saving to Excel …")
    for res in results:
        save_outreach_attempt(
            recruiter_name=recruiter_name,
            recruiter_title=recruiter_title,
            company=company,
            role_applied=role_title,
            email_address=res["to"],
            sent=res["success"],
            sent_at=res.get("sent_at"),
            subject=subject,
            notes=res.get("error") or "",
        )

    sent_count = sum(1 for r in results if r["success"])
    print(f"\nDone. {sent_count}/{len(candidates)} emails sent.")
    print(f"Records saved to: {config.excel_file}")
    print("\nRun  `python main.py bounces`  in a few hours to check for bounces.")


def cmd_bounces():
    print("\n=== Checking Gmail for Bounce Notifications ===\n")
    if not config.gmail_address or not config.gmail_app_password:
        sys.exit("ERROR: Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables.")

    # Check last 48 hours by default
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=48)
    print(f"Scanning inbox for bounces since {since.strftime('%Y-%m-%d %H:%M UTC')} …")

    bounced = check_bounces(since_datetime=since)

    if not bounced:
        print("No bounce notifications found.")
    else:
        print(f"\nFound {len(bounced)} bounced address(es):")
        for addr in bounced:
            print(f"  {addr}")
        apply_bounce_results(bounced)
        print(f"\nExcel updated: {config.excel_file}")

    print_confirmed_emails()


def cmd_summary():
    print_confirmed_emails()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

COMMANDS = {
    "send": cmd_send,
    "bounces": cmd_bounces,
    "summary": cmd_summary,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "send"
    if cmd not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[cmd]()
