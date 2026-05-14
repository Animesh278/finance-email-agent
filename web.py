"""
Finance Credit Follow-Up Email Agent — Web Frontend (Flask)

Provides a browser-based UI to:
  - Upload CSV or use sample data
  - Run the agent pipeline in dry_run mode
  - View generated emails, audit trail, and summary
"""

import csv
import json
import io
import os
import sys
import logging
from datetime import datetime
from typing import Any

from flask import Flask, render_template, request, jsonify, send_from_directory

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.triage_agent import load_and_triage, mask_pii, calculate_days_overdue, classify_stage, REQUIRED_COLUMNS
from agents.email_generator import EmailOutput, get_email_generator, format_inr, format_date_display
from config.settings import is_api_available

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)

logger = logging.getLogger("finance_agent_web")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Path helpers ──────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SAMPLE_CSV = os.path.join(PROJECT_ROOT, "data", "sample_invoices.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve the main frontend page."""
    return render_template("index.html")


@app.route("/api/sample-data")
def get_sample_data():
    """Return the sample CSV data as JSON for preview."""
    try:
        import pandas as pd
        df = pd.read_csv(SAMPLE_CSV)
        records = df.to_dict(orient="records")
        return jsonify({"success": True, "data": records})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/run", methods=["POST"])
def run_pipeline():
    """
    Run the agent pipeline on uploaded CSV or sample data.
    Returns generated emails, audit trail, and summary stats.
    """
    ensure_output_dir()

    try:
        # Determine data source
        use_sample = request.form.get("use_sample", "false") == "true"

        if use_sample:
            csv_path = SAMPLE_CSV
        else:
            file = request.files.get("csv_file")
            if not file:
                return jsonify({"success": False, "error": "No CSV file uploaded"}), 400

            # Save uploaded file temporarily
            upload_path = os.path.join(OUTPUT_DIR, "uploaded_invoices.csv")
            file.save(upload_path)
            csv_path = upload_path

        # ── STEP 1 & 2: Data Ingestion + Triage ──────────────
        email_rows, escalated_rows, invalid_rows = load_and_triage(csv_path)
        total_loaded = len(email_rows) + len(escalated_rows) + len(invalid_rows)

        # ── STEP 3: Email Generation ──────────────────────────
        generator = get_email_generator()
        is_mock = not is_api_available()

        emails = []
        errors = []
        processed_invoices = set()

        for record in email_rows:
            invoice_number = str(record["invoice_number"])

            if invoice_number in processed_invoices:
                continue
            processed_invoices.add(invoice_number)

            try:
                result: EmailOutput = generator.generate(record)

                emails.append({
                    "invoice_number": invoice_number,
                    "client_name": str(record["client_name"]),
                    "contact_email": str(record["contact_email"]),
                    "amount_due": format_inr(float(record["amount_due"])),
                    "amount_raw": float(record["amount_due"]),
                    "due_date": format_date_display(str(record["due_date"])),
                    "days_overdue": int(record["days_overdue"]),
                    "stage": result.stage,
                    "tone_used": result.tone_used,
                    "subject": result.subject,
                    "body": result.body,
                    "justification": result.justification,
                    "action": result.action,
                })
            except Exception as e:
                errors.append({
                    "invoice_number": invoice_number,
                    "error": str(e),
                })

        # Build escalated list
        escalated = []
        for record in escalated_rows:
            escalated.append({
                "invoice_number": str(record["invoice_number"]),
                "client_name": str(record["client_name"]),
                "contact_email": str(record["contact_email"]),
                "amount_due": format_inr(float(record["amount_due"])),
                "days_overdue": int(record["days_overdue"]),
            })

        # Build invalid list
        invalid = []
        for record in invalid_rows:
            invalid.append({
                "invoice_number": str(record.get("invoice_number", "N/A")),
                "client_name": str(record.get("client_name", "N/A")),
                "reason": str(record.get("_error", "Unknown")),
            })

        # ── Write outputs ─────────────────────────────────────
        # Email log
        email_log_path = os.path.join(OUTPUT_DIR, "email_log.json")
        with open(email_log_path, "w", encoding="utf-8") as f:
            json.dump(emails, f, indent=2, ensure_ascii=False)

        # Audit trail
        audit_path = os.path.join(OUTPUT_DIR, "audit_trail.csv")
        with open(audit_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "invoice_number", "client_name", "amount_due",
                "days_overdue", "stage", "tone_used", "action_taken",
                "send_status", "error_message",
            ])
            writer.writeheader()
            for email in emails:
                writer.writerow({
                    "timestamp": datetime.now().isoformat(),
                    "invoice_number": email["invoice_number"],
                    "client_name": email["client_name"],
                    "amount_due": email["amount_raw"],
                    "days_overdue": email["days_overdue"],
                    "stage": email["stage"],
                    "tone_used": email["tone_used"],
                    "action_taken": "dry_run",
                    "send_status": "success",
                    "error_message": "",
                })
            for esc in escalated:
                writer.writerow({
                    "timestamp": datetime.now().isoformat(),
                    "invoice_number": esc["invoice_number"],
                    "client_name": esc["client_name"],
                    "amount_due": esc["amount_due"],
                    "days_overdue": esc["days_overdue"],
                    "stage": "ESCALATE",
                    "tone_used": "legal_escalation",
                    "action_taken": "flag_legal",
                    "send_status": "skipped",
                    "error_message": "",
                })

        # ── Summary ───────────────────────────────────────────
        summary = {
            "total_loaded": total_loaded,
            "invalid_count": len(invalid_rows),
            "emails_generated": len(emails),
            "emails_dry_run": len(emails),
            "escalated_count": len(escalated_rows),
            "error_count": len(errors),
            "is_mock": is_mock,
        }

        return jsonify({
            "success": True,
            "summary": summary,
            "emails": emails,
            "escalated": escalated,
            "invalid": invalid,
            "errors": errors,
        })

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/download/<filename>")
def download_output(filename):
    """Download output files (email_log.json or audit_trail.csv)."""
    safe_names = {"email_log.json", "audit_trail.csv"}
    if filename not in safe_names:
        return jsonify({"error": "File not allowed"}), 403
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    print("\n  Finance Email Agent — Web UI")
    print("  Open in browser: http://localhost:5000\n")
    app.run(debug=True, port=5000)
