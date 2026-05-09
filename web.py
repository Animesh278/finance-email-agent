import os
import pandas as pd
from flask import Flask, render_template, request, send_file
from agents.credit_followup import CreditFollowUpAgent
from config.settings import DATA_DIR, OUTPUT_DIR

app = Flask(__name__)

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

agent = CreditFollowUpAgent()

@app.route('/')
def index():
    return render_template('index.html', results=None, dry_run=True)

@app.route('/process', methods=['POST'])
def process_clients():
    use_sample = request.form.get('use_sample') == 'true'
    
    if use_sample:
        sample_path = os.path.join(DATA_DIR, 'sample_invoices.csv')
        df = pd.read_csv(sample_path)
    else:
        file = request.files.get('file')
        if not file or file.filename == '':
            return render_template('index.html', results={"error": "No file uploaded"}, dry_run=True)
        
        file_path = os.path.join(OUTPUT_DIR, 'uploaded_clients.csv')
        file.save(file_path)
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

    # Core logic processing
    clients = df.to_dict('records')
    results = agent.process_batch(clients)
    
    # Save results for download
    output_path = os.path.join(OUTPUT_DIR, 'followup_report.xlsx')
    
    # Create a nice Excel report with tabs
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        if results['emails']:
            pd.DataFrame(results['emails']).to_excel(writer, sheet_name='Drafts', index=False)
        if results['escalated']:
            pd.DataFrame(results['escalated']).to_excel(writer, sheet_name='Escalated', index=False)
        if results['invalid']:
            pd.DataFrame(results['invalid']).to_excel(writer, sheet_name='Invalid Data', index=False)

    return render_template('index.html', results=results, dry_run=True)

@app.route('/download')
def download_results():
    path = os.path.join(OUTPUT_DIR, 'followup_report.xlsx')
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "No report found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
