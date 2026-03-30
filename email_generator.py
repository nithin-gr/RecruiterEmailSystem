"""
Uses GPT-4o to generate all plausible email address combinations for a person
at a given company, then augments with deterministic pattern expansion.
"""

import re
import unicodedata
from typing import Optional
from openai import OpenAI
from config import config

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.openai_api_key)
    return _client


# ---------------------------------------------------------------------------
# Deterministic pattern expansion
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip accents, keep only ascii letters."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z]", "", ascii_only.lower())


def _build_patterns(first: str, last: str, domain: str) -> list[str]:
    f = _normalize(first)
    l = _normalize(last)
    fi = f[0] if f else ""
    li = l[0] if l else ""

    raw_patterns = [
        f"{f}.{l}",
        f"{f}{l}",
        f"{fi}{l}",
        f"{fi}.{l}",
        f"{f}_{l}",
        f"{f}-{l}",
        f"{f}",
        f"{l}",
        f"{l}.{f}",
        f"{l}{f}",
        f"{l}_{f}",
        f"{l}-{f}",
        f"{f}.{li}",
        f"{fi}{li}",
        f"{l}{fi}",
        f"{f}{l[0:3]}",       # firstname + first 3 of last
    ]

    seen = set()
    emails = []
    for p in raw_patterns:
        if p and p not in seen:
            seen.add(p)
            emails.append(f"{p}@{domain}")
    return emails


# ---------------------------------------------------------------------------
# GPT-4o augmentation: discovers the likely domain and extra patterns
# ---------------------------------------------------------------------------

def generate_email_combinations(
    full_name: str,
    company: str,
    company_domain: Optional[str] = None,
) -> dict:
    """
    Returns:
        {
          "domain": "acme.com",
          "emails": ["john.doe@acme.com", ...],
          "gpt_reasoning": "...",
        }
    """
    client = _get_client()

    domain_hint = f"The company's email domain is {company_domain}." if company_domain else ""

    prompt = f"""You are an expert at corporate email address formats.

Given:
- Person: {full_name}
- Company: {company}
{domain_hint}

Tasks:
1. If the domain is not provided, infer the most likely corporate email domain (e.g. acme.com, not gmail.com).
2. List every plausible email address format this company might use for this person.
   Consider: firstname.lastname, flastname, firstnamelastname, firstname, f.lastname,
   lastname.firstname, firstname-lastname, firstname_lastname, and any other common patterns.

Respond in this exact JSON format (no markdown, no extra keys):
{{
  "domain": "example.com",
  "emails": ["alice.smith@example.com", "asmith@example.com"],
  "reasoning": "one sentence explanation"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    import json
    data = json.loads(response.choices[0].message.content)
    domain = data.get("domain", "").strip().lower()

    # Parse name parts for deterministic expansion
    parts = full_name.strip().split()
    first = parts[0] if parts else full_name
    last = parts[-1] if len(parts) > 1 else ""

    deterministic = _build_patterns(first, last, domain) if domain else []

    # Merge GPT emails + deterministic, deduplicate, preserve order
    gpt_emails = [e.strip().lower() for e in data.get("emails", []) if "@" in e]
    all_emails = list(dict.fromkeys(gpt_emails + deterministic))

    return {
        "domain": domain,
        "emails": all_emails,
        "gpt_reasoning": data.get("reasoning", ""),
    }
