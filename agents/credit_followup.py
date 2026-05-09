import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CreditFollowUpAgent:
    """
    Agent responsible for analyzing client payment status and generating follow-up actions.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stages = {
            1: "Friendly Reminder",
            2: "Second Notice",
            3: "Urgent Demand",
            4: "Final Notice / Legal Escalation"
        }

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
            stage = 1
        elif days_overdue <= 21:
            stage = 2
        elif days_overdue <= 45:
            stage = 3
        else:
            stage = 4
            
        return {
            "stage": stage,
            "stage_name": self.stages.get(stage),
            "action": "Generate Email"
        }

    def generate_email_content(self, client_data: Dict[str, Any], triage_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates personalized email content based on the triage stage.
        In a real scenario, this would call an LLM.
        """
        stage = triage_result.get('stage')
        client_name = client_data.get('client_name')
        balance = client_data.get('balance')
        invoice_ref = client_data.get('invoice_ref', 'N/A')
        
        if stage == "ESCALATE":
            return None

        subjects = {
            1: f"Friendly Reminder: Invoice {invoice_ref} - {client_name}",
            2: f"Second Notice: Overdue Payment for Invoice {invoice_ref}",
            3: f"URGENT: Outstanding Balance for {client_name} - Action Required",
            4: f"FINAL NOTICE: Legal Action Warning regarding Invoice {invoice_ref}"
        }
        
        # Mocking LLM-style personalization
        bodies = {
            1: f"Hi {client_name},\n\nThis is a friendly reminder that invoice {invoice_ref} for £{balance} is now slightly overdue. We would appreciate it if you could look into this at your earliest convenience.\n\nBest regards,\nAccounts Team",
            2: f"Dear {client_name},\n\nWe are following up on our previous reminder regarding invoice {invoice_ref} (£{balance}). Our records show that payment has not yet been received. Please let us know if there are any issues.\n\nRegards,\nAccounts Team",
            3: f"Urgent Notice,\n\nYour account with {client_name} is now significantly overdue. The outstanding balance is £{balance}. We require immediate payment or a confirmed payment plan by end of week.\n\nSincerely,\nCredit Control",
            4: f"FINAL NOTICE,\n\nDespite multiple reminders, the balance of £{balance} remains unpaid. If payment is not received within 48 hours, we will be forced to escalate this to our legal department for collection.\n\nFinal Warning,\nLegal Dept"
        }
        
        return {
            "subject": subjects.get(stage, "Payment Follow-up"),
            "body": bodies.get(stage, "Please contact us regarding your balance."),
            "justification": f"Selected Stage {stage} based on {client_data.get('days_overdue')} days overdue."
        }

    def process_batch(self, clients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes a list of clients and returns a summary of results.
        """
        results = {
            "emails": [],
            "escalated": [],
            "invalid": [],
            "summary": {
                "total": len(clients),
                "generated": 0,
                "escalated": 0,
                "skipped": 0,
                "errors": 0
            }
        }
        
        for idx, client in enumerate(clients):
            try:
                # Basic validation
                if not client.get('client_name') or not client.get('email'):
                    results["invalid"].append({"row_index": idx+1, "reason": "Missing name or email", "client_name": client.get('client_name')})
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
                    
                email = self.generate_email_content(client, triage)
                if email:
                    results["emails"].append({
                        "client_name": client["client_name"],
                        "email": client["email"],
                        "balance": client["balance"],
                        "stage": triage["stage"],
                        "subject": email["subject"],
                        "body": email["body"],
                        "justification": email["justification"]
                    })
                    results["summary"]["generated"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing client {client.get('client_name')}: {str(e)}")
                results["summary"]["errors"] += 1
                
        return results
