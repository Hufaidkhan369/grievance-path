"""Application configuration, read from .env with sane defaults."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "grievances.db"


def _bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    APP_NAME = "GrievancePath"
    APP_TAGLINE = "Smart grievance routing for Smart India"

    DB_PATH = DB_PATH

    # ---- Routing engine ----
    ROUTER_DEFAULT = os.getenv("ROUTER_DEFAULT", "classifier")  # classifier | llm | hybrid
    # When ROUTER_DEFAULT=hybrid, the LLM is asked first and the classifier result is
    # used as a fallback / cross-check.
    CONFIDENCE_ACCEPT = float(os.getenv("CONFIDENCE_ACCEPT", "0.55"))
    MIN_ROUTE_CONFIDENCE = float(os.getenv("MIN_ROUTE_CONFIDENCE", "0.35"))
    USE_ML = _bool("USE_ML", True)  # train a small scikit-learn model at startup if possible

    # ---- Optional LLM router (OpenAI-compatible) ----
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # ---- Alerts ----
    ALERT_ENABLED = _bool("ALERT_ENABLED", True)
    EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "")
    EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@grievancepath.in")

    # ---- Demo auth (change for production) ----
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    DEPT_PASSWORD = os.getenv("DEPT_PASSWORD", "dept123")


settings = Settings()
