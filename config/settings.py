"""
Configuration settings for Finance Credit Follow-Up Email Agent.
Loads all environment variables from .env file using python-dotenv.
"""

import os
from dotenv import load_dotenv

# Load .env from the project root (one level up from config/)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


# -- Gemini API ---------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# -- SMTP Configuration ------------------------------------------------
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASS: str = os.getenv("SMTP_PASS", "")
SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "finance@yourcompany.com")

# -- Agent Mode ---------------------------------------------------------
MODE: str = os.getenv("MODE", "dry_run")

# -- LLM Model ---------------------------------------------------------
LLM_MODEL: str = "gemini-2.0-flash"


def is_api_available() -> bool:
    """Check if a real Gemini API key is configured."""
    return bool(GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here")


def is_smtp_configured() -> bool:
    """Check if SMTP credentials are configured for real email sending."""
    return bool(SMTP_USER and SMTP_PASS and SMTP_USER != "your_email@gmail.com")
