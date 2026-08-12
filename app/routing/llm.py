"""Optional LLM router (OpenAI-compatible chat-completions API).

Enabled only when LLM_API_KEY is set in .env. Always returns a fallback dict
when the call fails so routing never breaks during a live demo.
"""
from __future__ import annotations

import json
import re

from ..config import settings
from ..database import fetch_all

_SYSTEM_PROMPT = """You are a routing engine for a citizen grievance system in India.
Given the list of government departments and a citizen's complaint, choose the
single most appropriate department and a confidence score 0..1.

Respond ONLY with valid JSON:
{"department_code": "<code>", "confidence": 0.0-1.0, "reason": "<short reason>"}"""

_DEPARTMENTS_TEMPLATE = """Departments:
{depts}

Citizen complaint:
{complaint}"""


class LLMRouter:
    def __init__(self):
        self.enabled = bool(settings.LLM_API_KEY)

    def route(self, title: str, description: str) -> dict:
        if not self.enabled:
            return {"used": False}
        try:
            return self._call_llm(title, description)
        except Exception as exc:  # never break the demo
            return {"used": True, "error": str(exc), "department_code": None,
                    "confidence": 0.0, "reason": "LLM call failed"}

    def _call_llm(self, title: str, description: str) -> dict:
        depts = fetch_all("SELECT code, name FROM departments ORDER BY name")
        dept_lines = "\n".join(f"- {d['code']}: {d['name']}" for d in depts)

        import requests

        url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _DEPARTMENTS_TEMPLATE.format(
                    depts=dept_lines, complaint=f"{title}\n\n{description}")},
            ],
            "temperature": 0,
            "max_tokens": 200,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        match = re.search(r"\{.*\}", content, re.DOTALL)
        data = json.loads(match.group(0) if match else content)
        code = (data.get("department_code") or "").strip().upper()
        return {
            "used": True,
            "department_code": code or None,
            "confidence": float(data.get("confidence", 0.0)),
            "reason": str(data.get("reason", "")),
        }
