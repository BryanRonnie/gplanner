#!/usr/bin/env python3
"""
Quick test to verify environment variables are loaded correctly
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv('.env')

print("=" * 70)
print("Environment Variables Check")
print("=" * 70)
print()

# Check each required variable
variables = {
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
    'GOOGLE_APPLICATION_CREDENTIALS_JSON': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON'),
    'GOOGLE_TOKEN_JSON': os.getenv('GOOGLE_TOKEN_JSON'),
    'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
    'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID'),
}

all_set = True

for var_name, var_value in variables.items():
    if var_value:
        # Show first 20 chars for security
        display_value = var_value[:20] + '...' if len(var_value) > 20 else var_value
        print(f"✅ {var_name}: {display_value}")
    else:
        print(f"❌ {var_name}: NOT SET")
        all_set = False

print()
print("=" * 70)

if all_set:
    print("✅ All environment variables are set!")
    print()
    print("Your app should work correctly now.")
else:
    print("⚠️  Some environment variables are missing!")
    print()
    print("Please check your .env file and ensure all variables are set.")

print("=" * 70)
