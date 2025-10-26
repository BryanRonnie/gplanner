#!/usr/bin/env python3
"""
Quick test script for Telegram receiver functionality.
"""

import os
import sys
from dotenv import load_dotenv
from telegram_receiver import get_messages_from_user, get_updates, mark_updates_as_read
from telegram_sender import send_message

# Load environment variables
load_dotenv('env')

def test_send_message():
    """Test sending a message."""
    print("=" * 60)
    print("Testing: Send Message")
    print("=" * 60)
    
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID not set in environment")
        return False
    
    try:
        success = send_message(chat_id, "🧪 Test message from GPlanner test script")
        if success:
            print("✅ Message sent successfully!")
            return True
        else:
            print("❌ Failed to send message")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_updates():
    """Test getting Telegram updates."""
    print("\n" + "=" * 60)
    print("Testing: Get Updates")
    print("=" * 60)
    
    try:
        updates = get_updates(limit=10)
        if updates.get('ok'):
            result = updates.get('result', [])
            print(f"✅ Retrieved {len(result)} updates")
            
            if result:
                print("\nRecent updates:")
                for update in result[:3]:  # Show first 3
                    update_id = update.get('update_id')
                    if 'message' in update:
                        msg = update['message']
                        text = msg.get('text', '<no text>')
                        from_user = msg.get('from', {}).get('username', 'unknown')
                        print(f"  - Update {update_id}: {from_user} said: {text}")
            return True
        else:
            print("❌ Failed to get updates")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_messages():
    """Test getting messages from specific user."""
    print("\n" + "=" * 60)
    print("Testing: Get Messages from User")
    print("=" * 60)
    
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID not set in environment")
        return False
    
    try:
        messages = get_messages_from_user(chat_id, limit=5)
        print(f"✅ Retrieved {len(messages)} messages from user {chat_id}")
        
        if messages:
            print("\nRecent messages:")
            for msg in messages:
                text = msg.get('text', '<no text>')
                from_user = msg.get('from_user', 'unknown')
                print(f"  - {from_user}: {text}")
        else:
            print("  No messages found (or no recent messages)")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_mark_read():
    """Test marking messages as read."""
    print("\n" + "=" * 60)
    print("Testing: Mark Messages as Read")
    print("=" * 60)
    
    try:
        # Get latest update
        updates = get_updates(limit=1)
        if updates.get('ok') and updates.get('result'):
            last_update_id = updates['result'][0]['update_id']
            print(f"Latest update ID: {last_update_id}")
            
            # Mark as read
            success = mark_updates_as_read(last_update_id)
            if success:
                print("✅ Successfully marked messages as read")
                return True
            else:
                print("❌ Failed to mark messages as read")
                return False
        else:
            print("ℹ️  No updates to mark as read")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🧪 GPlanner Telegram Receiver Test Suite")
    print("=" * 60)
    
    # Check environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token:
        print("\n❌ TELEGRAM_BOT_TOKEN not set in environment!")
        print("Please add it to your 'env' file")
        sys.exit(1)
    
    if not chat_id:
        print("\n⚠️  TELEGRAM_CHAT_ID not set in environment!")
        print("Some tests may fail. Please add it to your 'env' file")
    
    print(f"\n✅ Bot Token: {'*' * 10}{bot_token[-10:]}")
    print(f"✅ Chat ID: {chat_id or 'Not set'}")
    
    # Run tests
    results = []
    results.append(("Send Message", test_send_message()))
    results.append(("Get Updates", test_get_updates()))
    results.append(("Get Messages", test_get_messages()))
    results.append(("Mark Read", test_mark_read()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
