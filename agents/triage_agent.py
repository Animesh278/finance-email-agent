"""
Triage Agent - classifies invoices into urgency stages.
"""

from datetime import datetime
from typing import Dict, Any

class TriageAgent:
    def triage(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifies an invoice based on days overdue.
        0 days: Normal (Skip)
        1-7 days: Stage 1 (Friendly)
        8-14 days: Stage 2 (Formal)
        15-30 days: Stage 3 (Urgent)
        31+ days: Stage 4 (Final Warning/Legal)
        """
        days = invoice_data.get('days_overdue', 0)

        if days <= 0:
            status = "skipped"
            stage = 0
            reason = "Not overdue"
        elif 1 <= days <= 7:
            status = "generate"
            stage = 1
            reason = "Slightly overdue"
        elif 8 <= days <= 14:
            status = "generate"
            stage = 2
            reason = "Moderately overdue"
        elif 15 <= days <= 30:
            status = "generate"
            stage = 3
            reason = "Severely overdue"
        else:
            status = "escalate"
            stage = 4
            reason = "Final notice required / Legal escalation"

        invoice_data['status'] = status
        invoice_data['stage'] = stage
        invoice_data['triage_reason'] = reason

        return invoice_data
triage_agent.py
