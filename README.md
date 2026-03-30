# Recruiter Email Outreach System

A Streamlit app that helps job seekers cold-email recruiters and hiring managers at scale. It uses GPT-4o to generate every plausible email address for a person at a company, composes a personalised short email from your resume and the job description, sends it via your Gmail account, and tracks bounces in an Excel file to infer the recruiter's real address.

---

## Features

- **Email combination generation** — GPT-4o infers the company domain and generates every common address pattern (`first.last`, `flast`, `firstnamelast`, etc.), augmented by 15 deterministic variants
- **AI-composed outreach email** — GPT-4o writes a ≤150-word personalised cold email from your resume + job description, fully editable before sending
- **Gmail sending** — sends via your personal Gmail using SMTP with a per-address delay to avoid rate limits
- **Bounce detection** — scans your Gmail inbox via IMAP for delivery failure notifications and marks bounced addresses in Excel
- **Confirmed-email inference** — automatically identifies the recruiter's real address once all others have bounced
- **Excel tracker** — records every attempt with sent/bounced/confirmed status; filterable in-app and downloadable

---

## Prerequisites

| Requirement | Details |
|---|---|
| Python 3.11+ | [python.org/downloads](https://www.python.org/downloads/) |
| OpenAI API key | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) — needs GPT-4o access |
| Gmail account | Must have **2-Step Verification** enabled |
| Gmail App Password | Generated at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) |

> **Why an App Password?** Google no longer allows third-party apps to use your real Gmail password for SMTP. An App Password is a 16-character code that grants access only to Gmail — it is not your account password.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/nithin-gr/RecruiterEmailSystem.git
cd RecruiterEmailSystem
```

### 2. Create and activate a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-...
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

> The app also accepts these credentials directly in the sidebar, so the `.env` file is optional — useful if you want them pre-filled on launch.

To load the `.env` automatically, install `python-dotenv` and add this to the top of `app.py` (one-time setup):

```bash
pip install python-dotenv
```

```python
# Add at the very top of app.py
from dotenv import load_dotenv
load_dotenv()
```

---

## Generating a Gmail App Password

1. Go to your Google Account → **Security**
2. Under *How you sign in to Google*, ensure **2-Step Verification** is **On**
3. Visit [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Click **Create**, give it a name (e.g. *RecruiterOutreach*), click **Create**
5. Copy the 16-character password (shown once — save it now)
6. Paste it as `GMAIL_APP_PASSWORD` — spaces are fine, they are ignored

---

## Launching the app

```bash
streamlit run app.py
```

The app opens at **http://localhost:8501** in your browser.

---

## Using the app

### Sidebar — Credentials

Fill in before doing anything else:

| Field | What to enter |
|---|---|
| Your full name | Used in the email sign-off |
| Your Gmail address | The account emails will be sent from |
| Gmail App Password | The 16-character code from the step above |
| OpenAI API key | Your `sk-...` key from platform.openai.com |

A warning is shown until all four fields are filled.

---

### Tab 1 — Send Outreach

The workflow unfolds in three steps.

#### Step 1 — Recruiter details

| Field | Notes |
|---|---|
| Recruiter / Hiring Manager name | Full name, e.g. *Sarah Johnson* |
| Their title | e.g. *Senior Technical Recruiter* |
| Company | e.g. *Stripe* |
| Company email domain | Optional — leave blank to let GPT-4o infer it (e.g. `stripe.com`) |
| Role you're applying for | e.g. *Senior Software Engineer* |

Click **Generate Email Combinations**. A live status box shows:
- GPT-4o inferring the domain and common address formats
- Deterministic pattern expansion (15 variants)
- Final count of unique candidate addresses

#### Step 2 — Review addresses & compose email

An editable table lists every candidate address with a **Send?** checkbox. Uncheck any addresses you want to skip (e.g. obvious guesses you are confident are wrong).

Then paste:
- **Job description** — the full posting text
- **Your resume** — plain text (copy-paste from your resume document)

Click **Compose Email with GPT-4o**. The model reads your resume against the job description and writes a short, targeted cold email.

#### Step 3 — Review, edit & send

The generated **subject** and **body** are fully editable text fields. Tweak tone, add a specific detail, or rewrite entirely.

An expandable section shows the exact list of addresses that will receive the email.

Click **Send to X address(es)**. A progress bar updates as each email is sent. Results (sent / failed) are shown in a table and saved to `recruiter_outreach.xlsx`.

---

### Tab 2 — Check Bounces

Run this **a few hours after sending** to let delivery failure notifications arrive in your inbox.

1. Adjust the **hours slider** (default: last 24 hours)
2. Click **Scan Gmail inbox for bounces**

The app connects to Gmail via IMAP, finds messages from `mailer-daemon` / `Mail Delivery Subsystem`, extracts the failed recipient addresses, and marks them as bounced in the Excel file.

**Confirmed email inference:** once all addresses for a recruiter except one have bounced, that surviving address is automatically marked as the confirmed real email.

Click **Refresh confirmed emails** to see a summary table.

---

### Tab 3 — Records

A full view of every outreach attempt.

- **Metrics row** — total attempts, sent, bounced, confirmed
- **Filters** — by company and by status (Sent / Not sent / Bounced / Confirmed)
- **Download button** — exports the current Excel file

Click **Load / refresh records** to pull the latest data.

---

## Excel file structure

The file `recruiter_outreach.xlsx` is created automatically in the project folder.

| Column | Description |
|---|---|
| Recruiter Name | Full name entered |
| Recruiter Title | Their job title |
| Company | Company name |
| Role Applied | Role you applied for |
| Email Address | The specific address this row tracks |
| Sent | Yes / No |
| Sent At | UTC timestamp of send |
| Bounced | Yes / No (filled after bounce check) |
| Confirmed Email | The inferred real address once all others bounce |
| Subject | Email subject sent |
| Notes | Any send error messages |

Rows are colour-coded: **red** = bounced, **green** = confirmed.

> `recruiter_outreach.xlsx` is in `.gitignore` — it will never be committed to version control.

---

## CLI usage (optional)

A command-line interface is also available if you prefer not to use the Streamlit app:

```bash
# Interactive send wizard
python main.py send

# Check inbox for bounces
python main.py bounces

# Print confirmed emails
python main.py summary
```

Set credentials as environment variables before running:

```bash
export OPENAI_API_KEY=sk-...
export GMAIL_ADDRESS=you@gmail.com
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
```

---

## Security notes

- **Never commit `.env` or `pat.txt`** — both are in `.gitignore`
- The Gmail App Password grants access only to Gmail send/receive, not your full Google account
- Revoke the App Password any time at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
- The OpenAI API key is only used for GPT-4o calls and is never stored to disk by this app

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SMTPAuthenticationError` | Make sure you are using an App Password, not your real Gmail password. 2-Step Verification must be enabled. |
| `IMAP login failed` | Same as above — App Password required for IMAP too. |
| `openai.AuthenticationError` | Check your `OPENAI_API_KEY` is correct and has GPT-4o access. |
| No bounces detected | Wait longer (up to 24 h) and increase the hours slider. Some servers delay bounce notifications. |
| Streamlit not found | Run `pip install -r requirements.txt` inside your virtual environment. |
