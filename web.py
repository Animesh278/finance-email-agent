import os
import pandas as pd
from flask import Flask, render_template, request, send_file
from agents.credit_followup import CreditFollowUpAgent
from config.settings import DATA_DIR, OUTPUT_DIR


app = Flask(__name__)


# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


agent = CreditFollowUpAgent(api_key=os.environ.get("GEMINI_API_KEY"))


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
