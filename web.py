"""
Finance Credit Follow-Up Email Agent - Web Frontend (Flask)
Uses the same backend pipeline but provides a sleek glassmorphism dashboard.
"""

import os
import json
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from main import process_invoices, load_sample_data
from config.settings import OUTPUT_DIR, AUDIT_LOG_PATH, EMAIL_LOG_PATH

app = Flask(__name__)

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/')
def index():
      return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def run_pipeline():
      if 'file' in request.files:
                file = request.files['file']
                if file.filename == '':
                              return jsonify({"error": "No file selected"}), 400
                          file_path = os.path.join(OUTPUT_DIR, "uploaded_invoices.csv")
                file.save(file_path)
else:
        file_path = os.path.join("data", "sample_invoices.csv")
      results = process_invoices(file_path, mode="dry_run", verbose=True)
    return jsonify(results)

@app.route('/api/sample', methods=['GET'])
def get_sample():
      df = load_sample_data(os.path.join("data", "sample_invoices.csv"))
      return jsonify(df.to_dict(orient='records'))

@app.route('/api/results', methods=['GET'])
def get_results():
      emails = []
      audit = []
      if os.path.exists(EMAIL_LOG_PATH):
                with open(EMAIL_LOG_PATH, 'r') as f:
                              emails = json.load(f)
                      if os.path.exists(AUDIT_LOG_PATH):
                                audit_df = pd.read_csv(AUDIT_LOG_PATH)
                                audit = audit_df.to_dict(orient='records')
                            return jsonify({"emails": emails, "audit": audit})

  @app.route('/download/<filename>')
def download_file(filename):
      if filename == "emails":
                path = EMAIL_LOG_PATH
                name = "email_log.json"
elif filename == "audit":
        path = AUDIT_LOG_PATH
        name = "audit_trail.csv"
else:
        return "File not found", 404
      if os.path.exists(path):
                return send_file(path, as_attachment=True, download_name=name)
            return "File not yet generated", 404

if __name__ == '__main__':
      print("Finance Email Agent Frontend starting at http://localhost:5000")
      app.run(debug=True, port=5000)
  
