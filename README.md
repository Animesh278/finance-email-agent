# Finance Credit Follow-Up Email Agent

**AI Enablement Internship · Task 2**

An intelligent agent that automatically generates professional, tone-escalating payment reminder emails for overdue B2B invoices. The agent reads invoice data from CSV, classifies each invoice by urgency, generates personalised follow-up emails, and logs everything for audit compliance.

---

## Table of Contents
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Logic Flow](#-logic-flow)
- [Security & Compliance](#-security--compliance)
- [Installation & Usage](#-installation--usage)
- [Monitoring & Logs](#-monitoring--logs)

---

## Features
- **Tone Escalation**: Automatically adjusts email tone from "Gentle Reminder" (Stage 1) to "Final Notice" (Stage 4) and "Legal Escalation" based on days past due.
- **Mock LLM Support**: Fully functional demo mode without requiring API keys (uses deterministic mock generation).
- **Audit Compliance**: Generates a tamper-evident CSV audit log and a JSON email log.
- **PII Protection**: Automatically masks sensitive data (Internal IDs, full names) in logs.
- **Modern Web Dashboard**: Sleek Flask-based UI for CSV uploads and results visualization.

---

## Tech Stack
- **Backend**: Python 3.10+, Flask
- **LLM**: Claude 3.5 Sonnet (via Anthropic SDK)
- **Data**: Pandas (CSV processing)
- **Validation**: Pydantic (Schema enforcement)
- **Frontend**: Tailwind CSS, Lucide Icons, Glassmorphism UI

---

## Project Structure
```text
finance-email-agent/
├── data/               # Input data (CSV)
├── logs/               # Application logs
├── output/             # Generated emails & audit trails
├── src/
│   ├── config.py       # Constants & Business Logic settings
│   ├── models.py       # Pydantic schemas
│   ├── processor.py    # Invoice triage & logic
│   └── generator.py    # LLM & Mock email generation
├── templates/          # Flask HTML templates
├── main.py             # CLI Orchestrator
├── web.py              # Flask Web Server
└── requirements.txt    # Dependencies
```

---

## Logic Flow
1. **Ingestion**: Load invoices from CSV.
2. **Triage**: 
   - `0-7 days`: Stage 1 (Gentle)
   - `8-14 days`: Stage 2 (Firm)
   - `15-30 days`: Stage 3 (Urgent)
   - `>30 days`: Stage 4 (Final)
   - `>35 days`: Escalated to Legal
3. **Generation**: Mock or Real LLM generates the email body based on the Stage.
4. **Output**: Write to `email_log.json` and `audit_trail.csv`.

---

## Security & Compliance
- **Dry-Run Mode**: No emails are actually sent; they are saved for review.
- **Audit Trail**: Every action is logged with a timestamp and status.
- **PII Masking**: Customer names are masked in the audit CSV (e.g., `An*** Sh***`) to comply with privacy standards.

---

## Installation & Usage

### 1. Clone & Install
```bash
git clone https://github.com/Animesh278/finance-email-agent.git
cd finance-email-agent
pip install -r requirements.txt
```

### 2. Run CLI
```bash
python main.py --file data/sample_invoices.csv --mode dry_run --verbose
```

### 3. Run Web UI
```bash
python web.py
# Visit http://localhost:5000
```

---

## Monitoring & Logs
- **Audit Trail**: `output/audit_trail.csv`
- **Email Archive**: `output/email_log.json`

---
*Created as part of the AI Enablement Internship.*
