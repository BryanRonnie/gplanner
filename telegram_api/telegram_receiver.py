import os
import logging
from typing import Iterator, Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


def _split_text(text: str, max_chunk: int = 4000) -> Iterator[str]:
    if not text:
        return
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chunk, length)
        if end < length and text[end] != " ":
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space
        yield text[start:end]
        start = end


def send_message_with_token(bot_token: str, chat_id: str, text: str) -> bool:
    if not bot_token:
        raise RuntimeError("bot_token is required to send a Telegram message")

    if not chat_id:
        raise ValueError("chat_id is required to send a Telegram message")

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    success = True
    for chunk in _split_text(text, max_chunk=4000):
        payload = {"chat_id": chat_id, "text": chunk}
        try:
            resp = requests.post(api_url, data=payload, timeout=15)
            if not resp.ok:
                logger.error(f"Failed to send Telegram message chunk: {resp.status_code} {resp.text}")
                success = False
            else:
                logger.debug("Telegram chunk sent successfully")
        except Exception as e:
            logger.exception(f"Exception while sending Telegram message: {e}")
            success = False

    return success


def send_message(chat_id: str, text: str) -> bool:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")
    
    return send_message_with_token(bot_token, chat_id, text)


def get_updates(bot_token: Optional[str] = None, offset: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")
    
    api_url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"limit": limit}
    if offset is not None:
        params["offset"] = offset
    
    try:
        resp = requests.get(api_url, params=params, timeout=15)
        if not resp.ok:
            logger.error(f"Failed to get Telegram updates: {resp.status_code} {resp.text}")
            return {"ok": False, "result": []}
        return resp.json()
    except Exception as e:
        logger.exception(f"Exception while getting Telegram updates: {e}")
        return {"ok": False, "result": []}


def get_messages_from_user(user_id: str, bot_token: Optional[str] = None, limit: int = 10) -> list:
    updates = get_updates(bot_token=bot_token, limit=100)
    
    if not updates.get("ok"):
        return []
    
    messages = []
    for update in updates.get("result", []):
        if "message" in update:
            message = update["message"]
            # Check if message is from the requested user/chat
            if str(message.get("chat", {}).get("id")) == str(user_id):
                messages.append({
                    "update_id": update["update_id"],
                    "message_id": message.get("message_id"),
                    "from_user": message.get("from", {}).get("username"),
                    "from_id": message.get("from", {}).get("id"),
                    "chat_id": message.get("chat", {}).get("id"),
                    "text": message.get("text", ""),
                    "date": message.get("date"),
                })
                if len(messages) >= limit:
                    break
    
    return messages


def mark_updates_as_read(last_update_id: int, bot_token: Optional[str] = None) -> bool:
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")
    
    # Setting offset to last_update_id + 1 will mark all previous updates as confirmed
    api_url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"offset": last_update_id + 1, "limit": 1}
    
    try:
        resp = requests.get(api_url, params=params, timeout=15)
        return resp.ok
    except Exception as e:
        logger.exception(f"Exception while marking updates as read: {e}")
        return False


if __name__ == "__main__":
    # Quick local test (requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat:
        print("Set TELEGRAM_CHAT_ID and TELEGRAM_BOT_TOKEN to test")
    else:
        ok = send_message(chat, "Test message from GPlanner telegram_sender.py")
        print("Sent:", ok)
        
        # Test receiving messages
        print("\nFetching messages from user...")
        messages = get_messages_from_user(chat)
        print(f"Found {len(messages)} messages:")
        for msg in messages[:5]:  # Show last 5
            print(f"  - {msg['from_user']}: {msg['text']}")
