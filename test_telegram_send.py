#!/usr/bin/env python3
"""
Simple test to verify Telegram sending is working.
"""

import os
from dotenv import load_dotenv
from telegram_sender import send_message

# Load environment
load_dotenv('.env')

print("=" * 70)
print("Testing Telegram Message Sending")
print("=" * 70)
print()

chat_id = os.getenv('TELEGRAM_CHAT_ID')
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

if not bot_token:
    print("❌ TELEGRAM_BOT_TOKEN not set")
    exit(1)

if not chat_id:
    print("❌ TELEGRAM_CHAT_ID not set")
    exit(1)

print(f"Bot Token: {bot_token[:20]}...")
print(f"Chat ID: {chat_id}")
print()

print("Sending test message...")
test_message = "🎉 Test from GPlanner - Telegram is now working!"

try:
    result = send_message(chat_id, test_message)
    
    if result:
        print("✅ Message sent successfully!")
        print()
        print("Check your Telegram to see if you received the message.")
    else:
        print("❌ Failed to send message")
        print("Check the error messages above.")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print()
print("=" * 70)
