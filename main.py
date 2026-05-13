"""
Finance Credit Follow-Up Email Agent — Main Orchestrator (CLI Entry Point)
Executes the pipeline:
1. Data Ingestion
2. Triage & Analysis
3. Report Generation
"""
import argparse
import os
import sys
import pandas as pd
from agents.credit_followup import CreditFollowUpAgent
from config.settings import DATA_DIR, OUTPUT_DIR


def run_pipeline(input_file: str, dry_run: bool = True):
    """
    Runs the full end-to-end follow-up pipeline.
    """
    print(f"🚀 Starting Finance Email Agent (Dry Run: {dry_run})")
    
    # 1. Load Data
    if not os.path.exists(input_file):
        print(f"❌ Error: File {input_file} not found.")
        return


    df = pd.read_csv(input_file)
    clients = df.to_dict('records')
    
    # 2. Process with Agent
agent = CreditFollowUpAgent(api_key=os.environ.get("GEMINI_API_KEY"))
    results = agent.process_batch(clients)
    
    # 3. Output Results
    print(f"✅ Processed {results['summary']['total']} clients.")
    print(f"📧 Generated {results['summary']['generated']} emails.")
    print(f"⚠️  Escalated {results['summary']['escalated']} high-value cases.")
    
    # Save to Excel
    output_path = os.path.join(OUTPUT_DIR, 'cli_followup_report.xlsx')
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        if results['emails']:
            pd.DataFrame(results['emails']).to_excel(writer, sheet_name='Drafts', index=False)
        if results['escalated']:
            pd.DataFrame(results['escalated']).to_excel(writer, sheet_name='Escalated', index=False)
            
    print(f"📊 Detailed report saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finance Credit Follow-Up Agent")
    parser.add_argument("--input", default=os.path.join(DATA_DIR, "sample_invoices.csv"), help="Path to client CSV")
    parser.add_argument("--live", action="store_false", dest="dry_run", help="Run in live mode (send emails)")
    
    args = parser.parse_args()
    run_pipeline(args.input, args.dry_run)
