import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')

# Email Settings (Mock for demo)
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
EMAIL_SENDER = "accounts@example.com"

# Model Settings (Placeholder for real LLM integration)
MODEL_NAME = "gpt-4-turbo-preview"
