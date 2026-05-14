"""
Finance Credit Follow-Up Email Agent - Streamlit Frontend
"""

import os
import sys
import json
import csv
from datetime import datetime
import pandas as pd
import streamlit as st

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.triage_agent import load_and_triage
from agents.email_generator import get_email_generator, format_inr, format_date_display
from config.settings import is_api_available

# Configuration
st.set_page_config(
    page_title="LEDGER//OPS Mission Control",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark terminal vibe
st.markdown("""
<style>
    :root {
        --green: #00ff66;
    }
    .stApp {
        background-color: #0a0e14;
        color: #e6edf3;
        font-family: 'JetBrains Mono', monospace;
    }
    h1, h2, h3 {
        color: #00ff66 !important;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -1px;
    }
    .stButton>button {
        background-color: transparent !important;
        color: #00ff66 !important;
        border: 1px solid #00ff66 !important;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
        font-weight: 700;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #00ff66 !important;
        color: #0a0e14 !important;
        box-shadow: 0 0 10px #00ff6633;
    }
    .metric-container {
        background-color: #111820;
        border: 1px solid #1e2a3a;
        padding: 1rem;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SAMPLE_CSV = os.path.join(PROJECT_ROOT, "data", "sample_invoices.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.title("⚡ LEDGER//OPS")
st.sidebar.markdown("Autonomous Credit Operations")

api_status = "🟢 Active" if is_api_available() else "🟡 Mock Mode"
st.sidebar.markdown(f"**API Status:** {api_status}")

st.sidebar.markdown("---")
st.sidebar.header("Input Source")

use_sample = st.sidebar.button("Use Sample Data")
uploaded_file = st.sidebar.file_uploader("Or upload your CSV", type=["csv"])

# -----------------------------------------------------------------------------
# MAIN CONTENT
# -----------------------------------------------------------------------------
st.title("Mission Control Pipeline")
st.markdown("Upload a ledger or run the sample data to triage overdue invoices and generate tone-escalated follow-up emails.")

# Pipeline Logic
if use_sample or uploaded_file:
    with st.spinner("Initializing Pipeline..."):
        
        # 1. Prepare file path
        if use_sample:
            csv_path = SAMPLE_CSV
            st.info("Loaded sample dataset.")
        else:
            csv_path = os.path.join(OUTPUT_DIR, "uploaded_invoices.csv")
            with open(csv_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.info(f"Loaded {uploaded_file.name}.")

        # 2. Triage
        try:
            email_rows, escalated_rows, invalid_rows = load_and_triage(csv_path)
            total_loaded = len(email_rows) + len(escalated_rows) + len(invalid_rows)
            st.success(f"Triage Complete. {total_loaded} records processed.")
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")
            st.stop()

        # 3. Generate
        generator = get_email_generator()
        emails = []
        errors = []
        processed_invoices = set()
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, record in enumerate(email_rows):
            invoice_number = str(record["invoice_number"])
            if invoice_number in processed_invoices:
                continue
            processed_invoices.add(invoice_number)
            
            status_text.text(f"Generating email for {invoice_number}...")
            try:
                result = generator.generate(record)
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
                errors.append({"invoice_number": invoice_number, "error": str(e)})
            
            progress_bar.progress(min((i + 1) / max(len(email_rows), 1), 1.0))
            
        status_text.text("Generation Complete.")
        
        # Build Escalated
        escalated = []
        for record in escalated_rows:
            escalated.append({
                "invoice_number": str(record["invoice_number"]),
                "client_name": str(record["client_name"]),
                "contact_email": str(record["contact_email"]),
                "amount_due": format_inr(float(record["amount_due"])),
                "days_overdue": int(record["days_overdue"]),
            })

        # 4. Save Outputs
        email_log_path = os.path.join(OUTPUT_DIR, "email_log.json")
        with open(email_log_path, "w", encoding="utf-8") as f:
            json.dump(emails, f, indent=2, ensure_ascii=False)

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

        # -----------------------------------------------------------------------------
        # UI: RESULTS
        # -----------------------------------------------------------------------------
        st.markdown("---")
        st.header("Pipeline Results")
        
        # Stats
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Invoices", total_loaded)
        col2.metric("Emails Drafted", len(emails))
        col3.metric("Legal Escalations", len(escalated))
        col4.metric("Errors", len(errors))

        # Tabs
        tab1, tab2, tab3 = st.tabs(["Drafted Emails", "Escalated to Legal", "Audit Trail"])

        with tab1:
            if not emails:
                st.write("No emails drafted.")
            for em in emails:
                with st.expander(f"Invoice {em['invoice_number']} - {em['client_name']} (Stage {em['stage']})"):
                    st.caption(f"**Tone:** {em['tone_used']} | **Overdue:** {em['days_overdue']} days | **Amount:** {em['amount_due']}")
                    st.markdown(f"**Subject:** `{em['subject']}`")
                    st.text_area("Body", em['body'], height=200, label_visibility="collapsed")
                    st.info(f"**Agent Justification:** {em['justification']}")

        with tab2:
            if not escalated:
                st.write("No escalated invoices.")
            else:
                st.dataframe(pd.DataFrame(escalated))

        with tab3:
            with open(audit_path, "rb") as f:
                st.download_button("Download audit_trail.csv", f, file_name="audit_trail.csv", mime="text/csv")
            with open(email_log_path, "rb") as f:
                st.download_button("Download email_log.json", f, file_name="email_log.json", mime="application/json")
            
            df_audit = pd.read_csv(audit_path)
            st.dataframe(df_audit)

else:
    st.info("👈 Upload a CSV file or use the Sample Data from the sidebar to begin.")
