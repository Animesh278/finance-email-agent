import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from .email_generator import EmailGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CreditFollowUpAgent:
    """
    Agent responsible for analyzing client payment status and generating follow-up actions.
    """
    
    def __init__(self, api_key=None, config: Dict[str, Any] = None):
        self.config = config or {}
        self.email_generator = EmailGenerator(api_key=api_key)
        self.stages = {
            1: "Friendly Reminder",
            2: "Second Notice",
            3: "Urgent Demand",
            4: "Final Notice / Legal Escalation"
        }

    def generate_email_content(self, data: Dict[str, Any], stage: int) -> Dict[str, Any]:
        """
        Generates email content using the Gemini-powered EmailGenerator.
        """
        return self.email_generator.generate(data, stage)

    def triage_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifies a client into a follow-up stage based on days overdue and balance.
        """
        days_overdue = client_data.get('days_overdue', 0)
        balance = client_data.get('balance', 0)
        
        # High value escalation
        if balance > 50000 and days_overdue > 30:
            return {"stage": "ESCALATE", "reason": "High balance overdue (>50k)"}
            
        if days_overdue <= 7:
            return {"stage": 1, "reason": "Recently overdue"}
        elif days_overdue <= 14:
            return {"stage": 2, "reason": "Over 1 week overdue"}
        elif days_overdue <= 30:
            return {"stage": 3, "reason": "Over 2 weeks overdue"}
        else:
            return {"stage": 4, "reason": "Over 30 days overdue"}

    def run_bulk_followup(self, clients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes a list of clients and generates follow-up emails for each.
        """
        results = {
            "emails": [],
            "escalated": [],
            "invalid": [],
            "summary": {
                "total": len(clients),
                "generated": 0,
                "escalated": 0,
                "errors": 0
            }
        }
        
        for idx, client in enumerate(clients):
            try:
                # Basic validation
                if not client.get('client_name') or not client.get('email'):
                    results["invalid"].append({
                        "row_index": idx + 1,
                        "reason": "Missing name or email",
                        "client_name": client.get('client_name')
                    })
                    results["summary"]["errors"] += 1
                    continue
                
                triage = self.triage_client(client)
                
                if triage["stage"] == "ESCALATE":
                    results["escalated"].append({
                        "client_name": client["client_name"],
                        "balance": client["balance"],
                        "reason": triage["reason"]
                    })
                    results["summary"]["escalated"] += 1
                    continue
                
                email = self.generate_email_content(client, triage["stage"])
                if email:
                    results["emails"].append({
                        "client_name": client["client_name"],
                        "email": client["email"],
                        "balance": client["balance"],
                        "stage": triage["stage"],
                        "subject": email.get("subject", ""),
                        "body": email.get("body", ""),
                        "justification": email.get("justification", "")
                    })
                    results["summary"]["generated"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing client {client.get('client_name')}: {str(e)}")
                results["summary"]["errors"] += 1
                
        return results
