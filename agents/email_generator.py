"""
Email Generator Agent - deterministic mock and real Claude-powered generation.
"""

import os
import json
import anthropic
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# Mock data for deterministic generation when no API key is present
MOCK_EMAILS = {
      1: {
                "subject": "Follow-up: Invoice {invoice_id} is slightly overdue",
                "body": "Dear {contact_name},\n\nWe noticed that invoice {invoice_id} for {amount} is now {days} days overdue. We understand things get busy, so we wanted to send a friendly reminder.\n\nPlease let us know if you have any questions.\n\nBest regards,\nFinance Team",
                "justification": "Stage 1: Friendly reminder for early delinquency."
      },
      2: {
                "subject": "Overdue Notice: Invoice {invoice_id}",
                "body": "Dear {contact_name},\n\nThis is a follow-up regarding invoice {invoice_id} which is now {days} days past due. Please ensure payment is made at your earliest convenience.\n\nRegards,\nFinance Team",
                "justification": "Stage 2: Formal reminder."
      },
      3: {
                "subject": "URGENT: Outstanding Payment for Invoice {invoice_id}",
                "body": "Dear {contact_name},\n\nWe have not received payment for invoice {invoice_id} despite multiple reminders. Your account is now {days} days overdue. Please settle this immediately to avoid further action.\n\nFinance Team",
                "justification": "Stage 3: Urgent warning."
      },
      4: {
                "subject": "FINAL NOTICE: Invoice {invoice_id} - Immediate Action Required",
                "body": "Dear {contact_name},\n\nThis is your FINAL NOTICE. Invoice {invoice_id} is {days} days overdue. If payment is not received within 48 hours, we will be forced to escalate this to our legal department.\n\nFinance Team",
                "justification": "Stage 4: Final warning before legal escalation."
      }
}

class GeneratedEmail(BaseModel):
      subject: str = Field(..., description="The email subject line")
      body: str = Field(..., description="The full email body")
      justification: str = Field(..., description="Brief rationale for the tone and content")

class EmailGenerator:
      def __init__(self, api_key: Optional[str] = None):
                self.api_key = api_key
                self.client = anthropic.Anthropic(api_key=api_key) if api_key else None

      def generate(self, invoice_data: Dict[str, Any], stage: int) -> GeneratedEmail:
                if not self.api_key:
                              return self._generate_mock(invoice_data, stage)
                          return self._generate_real(invoice_data, stage)

      def _generate_mock(self, data: Dict[str, Any], stage: int) -> GeneratedEmail:
                mock = MOCK_EMAILS.get(stage, MOCK_EMAILS[1])
                return GeneratedEmail(
                    subject=mock["subject"].format(**data),
                    body=mock["body"].format(**data),
                    justification=mock["justification"]
                )

      def _generate_real(self, data: Dict[str, Any], stage: int) -> GeneratedEmail:
                # Placeholder for real LLM call
                return self._generate_mock(data, stage)
        
