#!/usr/bin/env python3
"""
Test your Telegram bot token to see if it's valid.
Usage: python test_telegram_token.py
"""

import os
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv('.env')

def test_token(token):
    """Test if a Telegram bot token is valid."""
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_bot_info(token):
    """Get bot information."""
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def main():
    print("=" * 70)
    print("Telegram Bot Token Tester")
    print("=" * 70)
    print()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        print()
        print("Please add your token to .env:")
        print("TELEGRAM_BOT_TOKEN=your_token_here")
        return 1
    
    print(f"Testing token: {token[:20]}...")
    print()
    
    result = test_token(token)
    
    if result.get('ok'):
        bot = result.get('result', {})
        print("✅ Token is VALID!")
        print()
        print("Bot Information:")
        print(f"  Name: {bot.get('first_name')}")
        print(f"  Username: @{bot.get('username')}")
        print(f"  ID: {bot.get('id')}")
        print(f"  Can join groups: {bot.get('can_join_groups')}")
        print(f"  Can read messages: {bot.get('can_read_all_group_messages')}")
        print()
        print("=" * 70)
        print("✅ Your bot is ready to use!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Start a chat with your bot: https://t.me/" + bot.get('username', ''))
        print("2. Send /start to your bot")
        print("3. Test your app: python main.py")
        return 0
    else:
        error_code = result.get('error_code')
        description = result.get('description', result.get('error', 'Unknown error'))
        
        print("❌ Token is INVALID!")
        print()
        print(f"Error: [{error_code}] {description}")
        print()
        print("=" * 70)
        print("How to fix:")
        print("=" * 70)
        print()
        
        if error_code == 401:
            print("Your token is unauthorized or revoked.")
            print()
            print("To get a new token:")
            print("1. Open Telegram and find @BotFather")
            print("2. Send: /newbot (for new bot) or /mybots (for existing)")
            print("3. Follow the prompts to get a new token")
            print("4. Update your .env file with the new token")
            print("5. Run this script again to verify")
        else:
            print(f"Unexpected error: {description}")
            print("Please check your token and try again.")
        
        return 1

if __name__ == '__main__':
    exit(main())
