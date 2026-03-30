"""
Uses GPT-4o to compose a short, personalised cold-outreach email.
"""

from typing import Optional
from openai import OpenAI
from config import config

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.openai_api_key)
    return _client


def compose_email(
    recruiter_name: str,
    recruiter_title: str,
    company: str,
    role_title: str,
    job_description: str,
    resume_text: str,
    sender_name: str,
) -> dict:
    """
    Returns:
        {
          "subject": "...",
          "body": "...",
        }
    """
    client = _get_client()

    prompt = f"""You are a professional career coach helping a job seeker write a concise cold-outreach email.

Context:
- Recipient: {recruiter_name}, {recruiter_title} at {company}
- Role being applied for: {role_title}
- Sender's name: {sender_name}

Job Description (excerpt):
{job_description[:1500]}

Sender's Resume (excerpt):
{resume_text[:2000]}

Write a short (≤150 words), professional, and personalized email:
- Subject line that stands out
- A brief intro of who the sender is
- 1-2 sentences on why they are a strong fit, citing specific skills from their resume that match the JD
- A clear, low-friction call to action (e.g., brief call or coffee chat)
- Polite sign-off

Respond ONLY as JSON with keys "subject" and "body". No markdown fences."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    import json
    return json.loads(response.choices[0].message.content)
