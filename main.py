"""
Finance Credit Follow-Up Email Agent — Main Orchestrator (CLI Entry Point)

Executes the 6-step pipeline:
  1. Data Ingestion  — load CSV, calculate days_overdue, validate
  2. Triage          — classify stages (no LLM)
  3. Email Generation — call mock/real LLM for non-escalated rows
  4. Send / Dry-Run  — write output or send via SMTP
  5. Audit Logging   — append to audit_trail.csv
  6. Summary Report  — print run stats to console
"""

import argparse
import csv
import json
import logging
import os
import re
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from typing import Any

# Ensure project root is in sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.triage_agent import load_and_triage, mask_pii
from agents.email_generator import EmailOutput, get_email_generator
from config.settings import (
    MODE, SENDER_EMAIL, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS,
    is_smtp_configured,
)

logger = logging.getLogger("finance_agent")


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def validate_email_format(email: str) -> bool:
    """Basic email format validation."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def ensure_output_dir() -> str:
    """Create the output/ directory if it doesn't exist. Returns the path."""
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


# ══════════════════════════════════════════════════════════════
# STEP 4 — SEND OR DRY-RUN
# ══════════════════════════════════════════════════════════════

def send_email_smtp(to_email: str, subject: str, body: str) -> bool:
    """
    Send an email via SMTP. Returns True on success, False on failure.
    """
    if not is_smtp_configured():
        logger.error("SMTP credentials not configured — cannot send email")
        return False

    if not validate_email_format(to_email):
        logger.error(f"Invalid email format: {mask_pii(to_email)}")
        return False

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())

        logger.info(f"Email sent successfully to {mask_pii(to_email)}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {mask_pii(to_email)}: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# STEP 5 — AUDIT LOGGING
# ══════════════════════════════════════════════════════════════

AUDIT_COLUMNS = [
    "timestamp", "invoice_number", "client_name", "amount_due",
    "days_overdue", "stage", "tone_used", "action_taken",
    "send_status", "error_message",
]


def append_audit_row(output_dir: str, row: dict[str, Any]) -> None:
    """Append one row to the audit trail CSV."""
    audit_path = os.path.join(output_dir, "audit_trail.csv")
    file_exists = os.path.exists(audit_path)

    with open(audit_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIT_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ══════════════════════════════════════════════════════════════
# STEP 6 — SUMMARY REPORT
# ══════════════════════════════════════════════════════════════

def print_summary(
    total_loaded: int,
    invalid_count: int,
    emails_generated: int,
    emails_sent_or_dry: int,
    escalated_count: int,
    error_count: int,
) -> None:
    """Print the formatted run summary to console (ASCII-safe for Windows)."""
    print("\n")
    print("  +======================================+")
    print("  |   FINANCE AGENT -- RUN SUMMARY       |")
    print("  +======================================+")
    print(f"  | Total invoices loaded    : {total_loaded:<10}|")
    print(f"  | Invalid / skipped rows   : {invalid_count:<10}|")
    print(f"  | Emails generated         : {emails_generated:<10}|")
    print(f"  | Emails sent (or dry-run) : {emails_sent_or_dry:<10}|")
    print(f"  | Escalated to legal       : {escalated_count:<10}|")
    print(f"  | Errors                   : {error_count:<10}|")
    print("  +======================================+")
    print()


# ══════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════

def run_pipeline(csv_path: str, mode: str, verbose: bool) -> None:
    """
    Execute the full 6-step pipeline:
    1. Data Ingestion → 2. Triage → 3. Email Generation →
    4. Send/Dry-Run → 5. Audit Logging → 6. Summary Report
    """

    # ── Setup logging ─────────────────────────────────────────
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("=" * 60)
    logger.info("FINANCE CREDIT FOLLOW-UP EMAIL AGENT — Starting Run")
    logger.info(f"CSV file : {csv_path}")
    logger.info(f"Mode     : {mode}")
    logger.info(f"Verbose  : {verbose}")
    logger.info("=" * 60)

    # ── STEP 1 & 2: Data Ingestion + Triage ───────────────────
    email_rows, escalated_rows, invalid_rows = load_and_triage(csv_path)

    total_loaded = len(email_rows) + len(escalated_rows) + len(invalid_rows)

    # ── STEP 3: Email Generation ──────────────────────────────
    generator = get_email_generator()
    output_dir = ensure_output_dir()

    email_log: list[dict[str, Any]] = []
    emails_generated = 0
    emails_sent_or_dry = 0
    error_count = 0

    # Track invoice numbers to enforce one-email-per-invoice rule
    processed_invoices: set[str] = set()

    for record in email_rows:
        invoice_number = str(record["invoice_number"])
        client_name = str(record["client_name"])
        contact_email = str(record["contact_email"])

        # Enforce: never send more than one email per invoice per run
        if invoice_number in processed_invoices:
            logger.warning(f"Duplicate invoice {invoice_number} — skipping")
            continue
        processed_invoices.add(invoice_number)

        try:
            result: EmailOutput = generator.generate(record)
            emails_generated += 1

            logger.info(
                f"Generated Stage {result.stage} email for invoice {invoice_number} "
                f"({mask_pii(client_name)})"
            )

            # Build email log entry
            log_entry = {
                "invoice_number": invoice_number,
                "client_name": client_name,
                "contact_email": contact_email,
                "stage": result.stage,
                "tone_used": result.tone_used,
                "subject": result.subject,
                "body": result.body,
                "justification": result.justification,
            }
            email_log.append(log_entry)

            # ── STEP 4: Send or Dry-Run ──────────────────────
            send_status = "skipped"

            if mode == "dry_run":
                print(f"  [DRY RUN] Would send to: {contact_email}")
                send_status = "success"
                emails_sent_or_dry += 1

            elif mode == "send":
                if validate_email_format(contact_email):
                    if send_email_smtp(contact_email, result.subject or "", result.body or ""):
                        send_status = "success"
                        emails_sent_or_dry += 1
                    else:
                        send_status = "failed"
                        error_count += 1
                else:
                    logger.error(f"Invalid email format for {invoice_number}: {mask_pii(contact_email)}")
                    send_status = "failed"
                    error_count += 1

            # ── STEP 5: Audit Logging ─────────────────────────
            append_audit_row(output_dir, {
                "timestamp": datetime.now().isoformat(),
                "invoice_number": invoice_number,
                "client_name": client_name,
                "amount_due": record["amount_due"],
                "days_overdue": record["days_overdue"],
                "stage": result.stage,
                "tone_used": result.tone_used,
                "action_taken": "email_sent" if mode == "send" and send_status == "success" else "dry_run",
                "send_status": send_status,
                "error_message": "",
            })

        except Exception as e:
            logger.error(f"Error processing invoice {invoice_number}: {e}")
            error_count += 1

            append_audit_row(output_dir, {
                "timestamp": datetime.now().isoformat(),
                "invoice_number": invoice_number,
                "client_name": client_name,
                "amount_due": record.get("amount_due", ""),
                "days_overdue": record.get("days_overdue", ""),
                "stage": record.get("stage", ""),
                "tone_used": record.get("tone", ""),
                "action_taken": "error",
                "send_status": "parse_error",
                "error_message": str(e),
            })

    # ── Process escalated rows (no email, just audit) ─────────
    for record in escalated_rows:
        invoice_number = str(record["invoice_number"])
        client_name = str(record["client_name"])

        logger.info(
            f"ESCALATED: Invoice {invoice_number} ({mask_pii(client_name)}) "
            f"— {record['days_overdue']} days overdue → flagged for legal"
        )

        append_audit_row(output_dir, {
            "timestamp": datetime.now().isoformat(),
            "invoice_number": invoice_number,
            "client_name": client_name,
            "amount_due": record["amount_due"],
            "days_overdue": record["days_overdue"],
            "stage": "ESCALATE",
            "tone_used": "legal_escalation",
            "action_taken": "flag_legal",
            "send_status": "skipped",
            "error_message": "",
        })

    # ── Write email log to JSON ───────────────────────────────
    email_log_path = os.path.join(output_dir, "email_log.json")
    with open(email_log_path, "w", encoding="utf-8") as f:
        json.dump(email_log, f, indent=2, ensure_ascii=False)
    logger.info(f"Email log written to: {email_log_path}")

    # ── STEP 6: Summary Report ────────────────────────────────
    print_summary(
        total_loaded=total_loaded,
        invalid_count=len(invalid_rows),
        emails_generated=emails_generated,
        emails_sent_or_dry=emails_sent_or_dry,
        escalated_count=len(escalated_rows),
        error_count=error_count,
    )

    logger.info("Run complete.")


# ══════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finance Credit Follow-Up Email Agent — generates payment reminder emails for overdue invoices.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --file data/sample_invoices.csv
  python main.py --file data/sample_invoices.csv --mode dry_run --verbose
  python main.py --file data/sample_invoices.csv --mode send
        """,
    )
    parser.add_argument(
        "--file", "-f",
        required=True,
        help="Path to the CSV file containing invoice data",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["dry_run", "send"],
        default="dry_run",
        help="Execution mode: 'dry_run' (default) writes to log file, 'send' sends via SMTP",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG level) logging",
    )

    args = parser.parse_args()

    # Resolve CSV path relative to script directory if not absolute
    csv_path = args.file
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), csv_path)

    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)

    run_pipeline(csv_path=csv_path, mode=args.mode, verbose=args.verbose)


if __name__ == "__main__":
    main()
