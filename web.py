import os
import json
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from agents.credit_followup import CreditFollowUpAgent
from config.settings import DATA_DIR, OUTPUT_DIR

app = Flask(__name__)

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

agent = CreditFollowUpAgent(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/run', methods=['POST'])
def run_pipeline():
    use_sample = request.form.get('use_sample') == 'true'
    
    if use_sample:
        csv_path = os.path.join(DATA_DIR, 'sample_invoices.csv')
        # Ensure sample exists
        if not os.path.exists(csv_path):
             data = [
                 {"invoice_number": "INV-001", "client_name": "Acme Corp", "amount_due": "$1,200", "days_overdue": 5, "contact_email": "billing@acme.com"},
                 {"invoice_number": "INV-002", "client_name": "Globex", "amount_due": "$500", "days_overdue": 15, "contact_email": "finance@globex.com"},
                 {"invoice_number": "INV-003", "client_name": "Soylent", "amount_due": "$3,000", "days_overdue": 45, "contact_email": "pay@soylent.com"},
                 {"invoice_number": "INV-004", "client_name": "Initech", "amount_due": "$150", "days_overdue": 95, "contact_email": "accounts@initech.com"},
                 {"invoice_number": "INV-005", "client_name": "Umbrella", "amount_due": "$10,000", "days_overdue": 120, "contact_email": "legal@umbrella.com"},
                 {"invoice_number": "INV-006", "client_name": "Hooli", "amount_due": "$2,500", "days_overdue": 3, "contact_email": "ops@hooli.com"}
             ]
             pd.DataFrame(data).to_csv(csv_path, index=False)
    else:
        file = request.files.get('csv_file')
        if not file:
            return jsonify({"success": False, "error": "No CSV file uploaded"}), 400
        csv_path = os.path.join(DATA_DIR, file.filename)
        file.save(csv_path)

    try:
        # Run agent logic
        results = agent.process_ledger(csv_path)
        
        # Save results for download
        with open(os.path.join(OUTPUT_DIR, 'email_log.json'), 'w') as f:
            json.dump(results.get('emails', []), f, indent=2)
            
        # Build response summary
        summary = results.get('summary', {})
        emails = results.get('emails', [])
        escalated = results.get('escalated', [])
        invalid = results.get('invalid', [])
        
        return jsonify({
            "success": True,
            "summary": {
                "total_loaded": summary.get('total', 0),
                "invalid_count": summary.get('invalid', 0),
                "emails_generated": len(emails),
                "emails_dry_run": len(emails),
                "escalated_count": len(escalated),
                "error_count": summary.get('errors', 0),
                "is_mock": getattr(agent, 'is_mock', False)
            },
            "emails": emails,
            "escalated": escalated,
            "invalid": invalid
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
