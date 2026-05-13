"""
Email Generator Agent - Gemini-powered generation.
"""

import os
import json
from google import genai
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

MOCK_EMAILS = {
    1: {"subject": "Friendly Reminder: Invoice {id}", "body": "Hi {name},\n\nReminder for invoice {id}.\n\nRegards,\nFinance", "justification": "Stage 1"},
    2: {"subject": "Overdue Notice: Invoice {id}", "body": "Dear {name},\n\nInvoice {id} is overdue.\n\nRegards,\nFinance", "justification": "Stage 2"},
    3: {"subject": "Urgent: Invoice {id}", "body": "Dear {name},\n\nInvoice {id} is urgent.\n\nRegards,\nFinance", "justification": "Stage 3"},
    4: {"subject": "FINAL NOTICE: Invoice {id}", "body": "Dear {name},\n\nFinal notice for invoice {id}.\n\nRegards,\nFinance", "justification": "Stage 4"}
}

class GeneratedEmail(BaseModel):
    subject: str = Field(..., description="Subject")
    body: str = Field(..., description="Body")
    tone_used: str = Field(..., description="Tone")
    justification: str = Field(..., description="Justification")

class EmailGenerator:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.use_mock = not api_key
        if not self.use_mock:
            self.client = genai.Client(api_key=api_key)
            self.model_id = "gemini-2.0-flash"

    def generate(self, data, stage):
        if self.use_mock: return self._generate_mock(data, stage)
        return self._generate_real(data, stage)

    def _generate_mock(self, data, stage):
        t = MOCK_EMAILS.get(stage, MOCK_EMAILS[1])
        return {
            "subject": t["subject"].format(id=data.get("invoice_number")),
            "body": t["body"].format(name=data.get("client_name"), id=data.get("invoice_number")),
            "tone_used": ["warm", "firm", "serious", "urgent"][stage-1],
            "justification": t["justification"]
        }

    def _generate_real(self, data, stage):
        prompt = f"Generate a credit follow-up email for invoice {data.get('invoice_number')} stage {stage}."
        try:
            res = self.client.models.generate_content(
                model=self.model_id, contents=prompt,
                config={'response_mime_type': 'application/json', 'response_schema': GeneratedEmail}
            )
            return json.loads(res.text)
        except:
            return self._generate_mock(data, stage)
