
import asyncio
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException

from routes.gemini_api import get_recommendations
from routes.tasks_and_calendar_api import sync_data
from telegram_api.telegram_receiver import get_messages_from_user, get_updates, mark_updates_as_read
from telegram_api.telegram_sender import send_message, send_message_with_token

from routes.gemini_api import get_recommendations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


def _get_env_chat_id() -> int:
    """Return TELEGRAM_CHAT_ID from env as an integer."""
    chat_id_raw = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id_raw:
        raise HTTPException(status_code=400, detail="TELEGRAM_CHAT_ID not set in environment")

    try:
        return int(chat_id_raw)
    except ValueError as exc:
        logger.error("TELEGRAM_CHAT_ID must be an integer, got %s", chat_id_raw)
        raise HTTPException(status_code=400, detail="TELEGRAM_CHAT_ID must be an integer") from exc

@router.get("/telegram_recommendation")
async def telegram_recommendation(telegram_token: Optional[str] = None):
    """Singular endpoint: send demo recommendation. Accepts optional telegram_token to override env token."""

    response = await sync_data()
    calendar_data = response.get("calendar_data", {})
    tasks_data = response.get("tasks_data", {})
    current_time = asyncio.get_event_loop().time()

    gemini_prompt = f"""Help me plan my events for today alone. 
                        This scheduled job runs every 30 mins within this range. 
                        If the time is not divisible by 30 mins, it's a manual api call. 
                        The current time is {current_time} - hourly tasks please based on my calendar and tasks. 
                        I'm a very bad procrastinator with ADHD. I need your help badly: This is my calendar and tasks data. 


                        Keep the message concise. No styled characters needed. 
                        eg. Cooking(Priority Lvl) -> 12pm - 1pm - Short Advice
                        
                        The day starts at 7.30am and ends at 12.30am. 
                        For the first scheduled api call at 7.30am, please plan the whole day for me. Give the tasks with approximate time slots Make sure to leave buffer time for each task. 
                        If the time is greater than 7.30am, only plan the next few hours ahead based on current time.
                        Give me progress report with score two times: at 2pm and at 12am.
                        \n""" + "Tasks:\n" + str(tasks_data) + "\nCalendar:\n" + str(calendar_data)

    gemini_output = await get_recommendations(gemini_prompt)

    chat_id = _get_env_chat_id()
    chat_id_str = str(chat_id)

    content = gemini_output.get("recommendations")

    if content is None:
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")
    try:
        if telegram_token:
            sent = await asyncio.to_thread(send_message_with_token, telegram_token, chat_id_str, content)
        else:
            sent = await asyncio.to_thread(send_message, chat_id_str, content)
        return {"sent": bool(sent)}
    except Exception as e:
        logger.exception("Failed to send telegram demo message (singular)")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/messages")
async def get_telegram_messages(
    user_id: Optional[str] = None,
    limit: int = 10
):
    if user_id:
        target_user = user_id
    else:
        target_user = str(_get_env_chat_id())
    
    try:
        messages = await asyncio.to_thread(get_messages_from_user, target_user, limit=limit)
        return {
            "user_id": target_user,
            "message_count": len(messages),
            "messages": messages
        }
    except Exception as e:
        logger.exception("Failed to get Telegram messages")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/updates")
async def get_telegram_updates(offset: Optional[int] = None, limit: int = 100):
    try:
        updates = await asyncio.to_thread(get_updates, offset=offset, limit=limit)
        return updates
    except Exception as e:
        logger.exception("Failed to get Telegram updates")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mark_read")
async def mark_telegram_read():
    chat_id = _get_env_chat_id()

    try:
        success = await asyncio.to_thread(mark_updates_as_read, chat_id)
        return {"success": success, "last_update_id": chat_id}
    except Exception as e:
        logger.exception("Failed to mark Telegram updates as read")
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/webhook")
# async def telegram_webhook(update: Dict):
#     """Webhook endpoint for receiving Telegram messages in real-time.
    
#     To use this endpoint:
#     1. Deploy your app with a public URL (e.g., using ngrok, Heroku, etc.)
#     2. Set webhook: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_URL>/telegram/webhook
    
#     This endpoint will automatically process incoming messages.
#     """
#     try:
#         logger.info(f"Received Telegram webhook update: {update}")
        
#         # Extract message information
#         if "message" in update:
#             message = update["message"]
#             chat_id = message.get("chat", {}).get("id")
#             text = message.get("text", "")
#             from_user = message.get("from", {}).get("username", "unknown")
            
#             logger.info(f"Message from {from_user} (chat_id: {chat_id}): {text}")
            
#             # Here you can add custom logic to process incoming messages
#             # For example, respond to specific commands:
#             if text.startswith("/"):
#                 # Handle commands
#                 if text == "/start":
#                     await asyncio.to_thread(
#                         send_message, 
#                         str(chat_id), 
#                         "Welcome to GPlanner! I can help you manage your calendar and tasks."
#                     )
#                 elif text == "/help":
#                     help_text = (
#                         "Available commands:\n"
#                         "/start - Start the bot\n"
#                         "/help - Show this help message\n"
#                         "/events - Get your upcoming events\n"
#                         "/tasks - Get your tasks\n"
#                         "/recommendations - Get AI recommendations"
#                     )
#                     await asyncio.to_thread(send_message, str(chat_id), help_text)
#                 elif text == "/events":
#                     events = calendar_data["events"][:5]  # Get first 5 events
#                     if events:
#                         events_text = "📅 Upcoming Events:\n\n"
#                         for event in events:
#                             summary = event.get("summary", "No title")
#                             start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
#                             events_text += f"• {summary}\n  {start}\n\n"
#                     else:
#                         events_text = "No upcoming events found."
#                     await asyncio.to_thread(send_message, str(chat_id), events_text)
#                 elif text == "/tasks":
#                     tasks = tasks_data["tasks"][:5]  # Get first 5 tasks
#                     if tasks:
#                         tasks_text = "✅ Your Tasks:\n\n"
#                         for task in tasks:
#                             title = task.get("title", "No title")
#                             tasks_text += f"• {title}\n"
#                     else:
#                         tasks_text = "No tasks found."
#                     await asyncio.to_thread(send_message, str(chat_id), tasks_text)
#                 elif text == "/recommendations":
#                     # Generate recommendations
#                     api_key = os.getenv('GEMINI_API_KEY')
#                     if api_key:
#                         client = genai.Client(api_key=api_key)
#                         prompt = (
#                             "Help me plan my events for today: this is my calendar and tasks data\n"
#                             + "Tasks:\n"
#                             + str(tasks_data)
#                             + "\nCalendar:\n"
#                             + str(calendar_data)
#                         )
#                         response = client.models.generate_content(
#                             model="gemini-2.5-flash",
#                             contents=prompt,
#                         )
#                         rec_text = getattr(response, "text", None) or str(response)
#                         await asyncio.to_thread(send_message, str(chat_id), f"🤖 AI Recommendations:\n\n{rec_text}")
#                     else:
#                         await asyncio.to_thread(send_message, str(chat_id), "GEMINI_API_KEY not configured.")
#             else:
#                 # Echo back non-command messages or implement custom logic
#                 await asyncio.to_thread(
#                     send_message,
#                     str(chat_id),
#                     f"You said: {text}\n\nUse /help to see available commands."
#                 )
        
#         return {"ok": True}
#     except Exception as e:
#         logger.exception("Error processing Telegram webhook")
#         return {"ok": False, "error": str(e)}
