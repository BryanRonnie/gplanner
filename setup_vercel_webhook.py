#!/usr/bin/env python3
"""
Script to set up Telegram webhook for Vercel deployment.
Usage: python setup_vercel_webhook.py
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

def set_webhook(bot_token, webhook_url):
    """Set Telegram webhook."""
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    params = {"url": webhook_url}
    
    try:
        response = requests.post(url, params=params)
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_webhook_info(bot_token):
    """Get current webhook information."""
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def delete_webhook(bot_token):
    """Delete current webhook."""
    url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        response = requests.post(url)
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def main():
    print("=" * 70)
    print("Telegram Webhook Setup for Vercel")
    print("=" * 70)
    print()
    
    # Get configuration
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    vercel_url = "https://gplanner.vercel.app"
    webhook_endpoint = "/telegram/webhook"
    webhook_url = f"{vercel_url}{webhook_endpoint}"
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        print()
        print("Please add your bot token to .env:")
        print("TELEGRAM_BOT_TOKEN=your_token_here")
        print()
        print("Get a token from @BotFather on Telegram:")
        print("1. Send /newbot to @BotFather")
        print("2. Follow the prompts")
        print("3. Copy the token")
        return 1
    
    print(f"Bot Token: {bot_token[:20]}...")
    print(f"Webhook URL: {webhook_url}")
    print()
    
    # Check current webhook status
    print("Checking current webhook status...")
    info = get_webhook_info(bot_token)
    
    if info.get('ok'):
        result = info.get('result', {})
        current_url = result.get('url', '')
        
        if current_url:
            print(f"📌 Current webhook: {current_url}")
            if current_url == webhook_url:
                print("✅ Webhook is already set to the correct URL!")
                print()
                response = input("Do you want to refresh it anyway? (y/n): ")
                if response.lower() != 'y':
                    print("Skipping webhook setup.")
                    return 0
        else:
            print("ℹ️  No webhook currently set")
    else:
        error_code = info.get('error_code')
        description = info.get('description', info.get('error', 'Unknown error'))
        print(f"❌ Error checking webhook: [{error_code}] {description}")
        print()
        
        if error_code == 401:
            print("Your bot token appears to be invalid or revoked.")
            print()
            print("To fix this:")
            print("1. Go to @BotFather on Telegram")
            print("2. Send /mybots")
            print("3. Select your bot")
            print("4. Go to 'Bot Settings' → 'Revoke Bot Token'")
            print("5. Generate a new token")
            print("6. Update TELEGRAM_BOT_TOKEN in your .env file")
            return 1
    
    print()
    print("-" * 70)
    print("Setting webhook...")
    print("-" * 70)
    
    # Set the webhook
    result = set_webhook(bot_token, webhook_url)
    
    if result.get('ok'):
        print("✅ Webhook set successfully!")
        print()
        print("Next steps:")
        print("1. Make sure your Vercel deployment is live")
        print("2. Ensure environment variables are set in Vercel:")
        print("   - TELEGRAM_BOT_TOKEN")
        print("   - TELEGRAM_CHAT_ID")
        print("   - GEMINI_API_KEY")
        print("   - GOOGLE_APPLICATION_CREDENTIALS_JSON")
        print("   - GOOGLE_TOKEN_JSON")
        print("3. Send /start to your bot on Telegram")
        print("4. Check Vercel logs for webhook activity")
    else:
        error_code = result.get('error_code')
        description = result.get('description', result.get('error', 'Unknown error'))
        print(f"❌ Failed to set webhook: [{error_code}] {description}")
        return 1
    
    print()
    print("-" * 70)
    print("Verifying webhook...")
    print("-" * 70)
    
    # Verify
    info = get_webhook_info(bot_token)
    
    if info.get('ok'):
        result = info.get('result', {})
        print(f"✅ Webhook URL: {result.get('url')}")
        print(f"   Pending updates: {result.get('pending_update_count', 0)}")
        print(f"   Last error date: {result.get('last_error_date', 'None')}")
        if result.get('last_error_message'):
            print(f"   Last error: {result.get('last_error_message')}")
    
    print()
    print("=" * 70)
    print("Setup complete! 🎉")
    print("=" * 70)
    
    return 0

if __name__ == '__main__':
    exit(main())
