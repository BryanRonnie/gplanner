import os
import logging
from typing import Iterator
import requests

logger = logging.getLogger(__name__)


def _split_text(text: str, max_chunk: int = 4000) -> Iterator[str]:
    """Yield chunks of the text not exceeding max_chunk characters.

    Keeps words intact when possible by splitting on whitespace.
    """
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
    """Send message using an explicit bot token. Returns True on success.

    This helper is useful for testing when you want to pass a token directly
    rather than relying on an environment variable.
    """
    if not bot_token:
        raise RuntimeError("bot_token is required to send a Telegram message")

    if not chat_id:
        raise ValueError("chat_id is required to send a Telegram message")

    api_url = f"https://api.telegram.org/bot7767903266:AAHFBVglMmnPVUs3fLr4OaNtVpMEKQeGuHU/sendMessage"

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
    """Send one or more messages to the given Telegram chat_id using env token.

    Returns True if all chunks were sent successfully, False otherwise.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    return send_message_with_token("7767903266:AAHFBVglMmnPVUs3fLr4OaNtVpMEKQeGuHU", chat_id, text)


if __name__ == "__main__":
    # Quick local test (requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat:
        print("Set TELEGRAM_CHAT_ID and TELEGRAM_BOT_TOKEN to test")
    else:
        ok = send_message(chat, "Test message from GPlanner telegram_sender.py")
        print("Sent:" , ok)
