import os
import sys
import logging
from main import load_config, fetch_grok_report

logging.basicConfig(level=logging.INFO)

config = load_config()
config["search_prompt"] = config["search_prompt"] + " Only extract exactly 2 posts for this preview."

print("Fetching 2 samples for preview...")
try:
    report = fetch_grok_report(config)
    print("\n--- PREVIEW START ---")
    print(report)
    print("--- PREVIEW END ---\n")
except Exception as e:
    print(f"Error: {e}")
