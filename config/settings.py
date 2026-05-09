"""
Configuration settings for the Finance Email Agent.
"""

import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# File Paths
AUDIT_LOG_PATH = os.path.join(OUTPUT_DIR, "audit_trail.csv")
EMAIL_LOG_PATH = os.path.join(OUTPUT_DIR, "email_log.json")

# LLM Settings
# To use real Claude, set ANTHROPIC_API_KEY in your environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
