import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio
from dotenv import load_dotenv, set_key

from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google import genai
from telegram_api.telegram_sender import send_message, send_message_with_token
from telegram_api.telegram_receiver import get_messages_from_user, get_updates, mark_updates_as_read
from routes.env_methods import router as env_router, set_env_var

import uvicorn
from datetime import time as dtime, datetime
from apscheduler.triggers.cron import CronTrigger

# Load environment variables from .env file
load_dotenv('.env')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/tasks.readonly'
]
REDIRECT_URI = 'http://localhost:8000/auth/callback'

app = FastAPI(title="Google Calendar & Tasks API", version="1.0.0")

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:3000",  # If you're using React
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
    "https://localhost",
    "https://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(env_router)


scheduler = AsyncIOScheduler()

# Global storage for fetched data (in production, use a proper database)
calendar_data = {"events": [], "last_updated": None}
tasks_data = {"tasks": [], "last_updated": None}

# Pydantic models
class CalendarEvent(BaseModel):
    id: str
    summary: str
    start: Optional[Dict]
    end: Optional[Dict]
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[Dict]] = None

class Task(BaseModel):
    id: str
    title: str
    notes: Optional[str] = None
    status: str
    due: Optional[str] = None
    updated: str

class DataResponse(BaseModel):
    events: List[CalendarEvent]
    tasks: List[Task]
    calendar_last_updated: Optional[str]
    tasks_last_updated: Optional[str]

def _build_credentials_payload_from_env() -> Optional[dict]:
    """Construct the serialized credential payload using only environment variables."""
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json:
        try:
            return json.loads(token_json)
        except json.JSONDecodeError:
            logger.error("GOOGLE_TOKEN_JSON is not valid JSON; falling back to individual env vars")

    token = os.getenv("GOOGLE_APPLICATION_TOKEN")
    client_id = os.getenv("GOOGLE_APPLICATION_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_APPLICATION_CLIENT_SECRET")

    if not token or not client_id or not client_secret:
        return None

    payload = {
        "token": token,
        "refresh_token": os.getenv("GOOGLE_APPLICATION_REFRESH_TOKEN"),
        "token_uri": os.getenv("GOOGLE_APPLICATION_TOKEN_URI", "https://oauth2.googleapis.com/token"),
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES,
        "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN", "googleapis.com"),
        "account": os.getenv("GOOGLE_APPLICATION_ACCOUNT", ""),
    }

    expiry = os.getenv("GOOGLE_APPLICATION_TOKEN_EXPIRY")
    if expiry:
        payload["expiry"] = expiry

    return payload


def _persist_credentials_to_env(creds: Credentials, *, persist: bool = True) -> None:
    """Persist the credential details back into environment variables and optional .env."""
    token_json = creds.to_json()
    set_env_var("GOOGLE_TOKEN_JSON", token_json, persist=persist)
    set_env_var("GOOGLE_APPLICATION_TOKEN", getattr(creds, "token", None), persist=persist)
    set_env_var("GOOGLE_APPLICATION_REFRESH_TOKEN", getattr(creds, "refresh_token", None), persist=persist)
    set_env_var("GOOGLE_APPLICATION_CLIENT_ID", getattr(creds, "client_id", None), persist=persist)
    set_env_var("GOOGLE_APPLICATION_CLIENT_SECRET", getattr(creds, "client_secret", None), persist=persist)
    if getattr(creds, "expiry", None):
        expiry_val = creds.expiry.isoformat() if hasattr(creds.expiry, "isoformat") else str(creds.expiry)
        set_env_var("GOOGLE_APPLICATION_TOKEN_EXPIRY", expiry_val, persist=persist)


def get_credentials() -> Optional[Credentials]:
    """Load or refresh Google API credentials using environment variables only."""
    payload = _build_credentials_payload_from_env()
    if not payload:
        logger.warning("Google credentials not found in environment. Please authenticate via /auth.")
        return None

    try:
        creds = Credentials.from_authorized_user_info(payload, SCOPES)
    except Exception as exc:
        logger.error(f"Failed to load credentials from environment: {exc}")
        return None

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing Google credentials from environment...")
                creds.refresh(Request())
                _persist_credentials_to_env(creds)
                logger.info("Google credentials refreshed and persisted to environment")
            except Exception as exc:
                logger.error(f"Failed to refresh Google credentials: {exc}")
                return None
        else:
            logger.warning("Google credentials invalid and cannot be refreshed. Please re-authenticate.")
            return None

    return creds

def _build_client_config_from_env() -> Optional[dict]:
    raw_config = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if raw_config:
        try:
            parsed = json.loads(raw_config)
            if "web" not in parsed:
                logger.warning("GOOGLE_APPLICATION_CREDENTIALS_JSON missing 'web' key; wrapping automatically")
                parsed = {"web": parsed}
            return parsed
        except json.JSONDecodeError as exc:
            logger.error(f"GOOGLE_APPLICATION_CREDENTIALS_JSON invalid JSON: {exc}")

    client_id = os.getenv("GOOGLE_APPLICATION_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_APPLICATION_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "project_id": os.getenv("GOOGLE_APPLICATION_PROJECT_ID"),
            "auth_uri": os.getenv("GOOGLE_APPLICATION_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": os.getenv("GOOGLE_APPLICATION_TOKEN_URI", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": os.getenv(
                "GOOGLE_APPLICATION_AUTH_PROVIDER_X509_CERT_URL",
                "https://www.googleapis.com/oauth2/v1/certs",
            ),
        }
    }


def create_auth_flow() -> Flow:
    """Create OAuth2 flow for authentication using environment variables only."""
    client_config = _build_client_config_from_env()
    if not client_config:
        raise ValueError(
            "Google OAuth client configuration not found. "
            "Set GOOGLE_APPLICATION_CREDENTIALS_JSON or individual client env vars."
        )

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", REDIRECT_URI)
    try:
        return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
    except Exception as exc:
        logger.exception("Failed to build OAuth flow from environment")
        raise ValueError(f"Invalid Google client configuration: {exc}")

async def fetch_calendar_events():
    """Fetch calendar events from Google Calendar API."""
    try:
        creds = get_credentials()
        if not creds:
            logger.warning("No valid credentials available for calendar sync")
            return []
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Get events from the next 7 days
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=7)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        logger.info(f"Fetched {len(events)} calendar events")
        
        return events
        
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        return []

async def fetch_tasks():
    """Fetch tasks from Google Tasks API.
    
    This function:
    1. Gets all task lists
    2. For each task list, fetches all tasks (both completed and incomplete)
    3. Returns a comprehensive list of all tasks with their metadata
    """
    try:
        creds = get_credentials()
        if not creds:
            logger.warning("No valid credentials available for tasks sync")
            return []
        
        service = build('tasks', 'v1', credentials=creds)
        
        # Get all task lists
        try:
            task_lists_result = service.tasklists().list(maxResults=100).execute()
            task_lists = task_lists_result.get('items', [])
            
            if not task_lists:
                logger.info("No task lists found")
                return []
            
            logger.info(f"Found {len(task_lists)} task list(s)")
            
        except Exception as e:
            logger.error(f"Error fetching task lists: {e}")
            return []
        
        all_tasks = []
        
        # For each task list, get all tasks
        for task_list in task_lists:
            task_list_id = task_list['id']
            task_list_title = task_list['title']
            
            try:
                # Fetch tasks from this list
                # showCompleted=True to get all tasks, you can change to False for incomplete only
                # showHidden=False to exclude hidden/deleted tasks
                tasks_result = service.tasks().list(
                    tasklist=task_list_id,
                    showCompleted=True,  # Change to False if you only want incomplete tasks
                    showHidden=False,
                    maxResults=100
                ).execute()
                
                tasks = tasks_result.get('items', [])
                
                logger.info(f"  Task list '{task_list_title}': {len(tasks)} task(s)")
                
                # Add task list metadata to each task
                for task in tasks:
                    task['taskListId'] = task_list_id
                    task['taskListTitle'] = task_list_title
                    all_tasks.append(task)
                    
            except Exception as e:
                logger.error(f"Error fetching tasks from list '{task_list_title}': {e}")
                continue
        
        logger.info(f"Fetched {len(all_tasks)} total task(s) across all lists")
        return all_tasks
        
    except Exception as e:
        logger.error(f"Error in fetch_tasks: {e}")
        return []

async def sync_data():
    """Background task to sync calendar and tasks data."""
    global calendar_data, tasks_data
    
    logger.info("Starting data sync...")
    
    # Fetch calendar events
    events = await fetch_calendar_events()
    calendar_data = {
        "events": events,
        "last_updated": datetime.now().isoformat()
    }
    
    # Fetch tasks
    tasks = await fetch_tasks()
    tasks_data = {
        "tasks": tasks,
        "last_updated": datetime.now().isoformat()
    }
    
    logger.info("Data sync completed")

@app.on_event("startup")
async def startup_event():
    """Start the scheduler when the app starts."""
    # Initial sync
    await sync_data()
    
    # Schedule hourly sync
    scheduler.add_job(
        sync_data,
        trigger=IntervalTrigger(hours=1),
        id='sync_google_data',
        name='Sync Google Calendar and Tasks',
        replace_existing=True
    )

    # Run every 30 minutes but only send recommendations between 07:30 and 00:30

    async def _telegram_recommendation_job():
        now = datetime.now().time()
        start = dtime(7, 30)
        end = dtime(0, 30)
        # Window wraps past midnight: true if now >= 07:30 OR now <= 00:30
        in_window = (now >= start) or (now <= end)
        if not in_window:
            return
        try:
            await telegram_recommendation()
        except Exception:
            logger.exception("Failed to run scheduled telegram_recommendation")

    scheduler.add_job(
        _telegram_recommendation_job,
        trigger=CronTrigger(minute="0,30"),
        id='telegram_recommendation',
        name='Telegram Recommendation (07:30-00:30)',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started - data will sync every hour")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler when the app shuts down."""
    scheduler.shutdown()

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Google Calendar & Tasks API",
        "endpoints": {
            "auth": "/auth - Start OAuth flow",
            "data": "/data - Get all calendar events and tasks",
            "events": "/events - Get calendar events only",
            "tasks": "/tasks - Get tasks only",
            "sync": "/sync - Manually trigger sync",
            "status": "/status - Check sync status",
            "telegram_messages": "/telegram/messages - Get messages from Telegram user",
            "telegram_updates": "/telegram/updates - Get all Telegram updates",
            "telegram_mark_read": "/telegram/mark_read - Mark messages as read",
            "telegram_webhook": "/telegram/webhook - Webhook for real-time Telegram messages"
        }
    }

@app.get("/auth")
async def auth():
    """Start the OAuth2 authentication flow.
    
    Returns:
        Dictionary with authorization URL to visit
    
    Raises:
        HTTPException: If credentials setup fails
    """
    try:
        flow = create_auth_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent screen to ensure refresh token
        )
        logger.info(f"Generated auth URL with state: {state}")
        return {
            "auth_url": authorization_url,
            "instructions": "Visit the auth_url in your browser and complete the OAuth flow"
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in auth setup")
        raise HTTPException(status_code=500, detail=f"Auth setup failed: {str(e)}")

@app.get("/auth/callback")
async def auth_callback(code: str, state: Optional[str] = None):
    """Handle OAuth2 callback and save credentials.
    
    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection (optional)
    
    Returns:
        Success message with instructions
    
    Raises:
        HTTPException: If authentication fails
    """
    try:
        logger.info("Processing OAuth callback...")
        
        flow = create_auth_flow()
        
        # Exchange authorization code for credentials
        try:
            flow.fetch_token(code=code)
        except Exception as e:
            logger.error(f"Failed to exchange authorization code: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to exchange authorization code. The code may be expired or invalid. Please try /auth again."
            )
        
        creds = flow.credentials
        
        if not creds:
            raise HTTPException(status_code=500, detail="Failed to obtain credentials")
        
        # Validate credentials
        if not creds.valid:
            raise HTTPException(status_code=500, detail="Obtained credentials are not valid")
        
        # Persist credentials entirely to environment variables (and .env for local dev)
        try:
            _persist_credentials_to_env(creds)
            logger.info("Credentials saved to environment variables (.env updated if present)")
        except Exception as e:
            logger.exception("Failed to persist credentials to environment")
            raise HTTPException(status_code=500, detail="Failed to save Google credentials")
        
        
        # Trigger initial data sync
        try:
            await sync_data()
            sync_status = "Data sync completed successfully"
        except Exception as e:
            logger.error(f"Initial sync failed: {e}")
            sync_status = f"Authentication successful but initial sync failed: {str(e)}"
        
        return {
            "message": "Authentication successful!",
            "sync_status": sync_status,
            "next_steps": [
                "Your credentials are now active",
                "Environment variables updated with latest Google tokens",
                "Access your data via /data, /events, or /tasks endpoints"
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in auth callback")
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}"
        )

@app.get("/data", response_model=DataResponse)
async def get_all_data():
    """Get all calendar events and tasks."""
    return DataResponse(
        events=[CalendarEvent(**event) for event in calendar_data["events"]],
        tasks=[Task(**task) for task in tasks_data["tasks"]],
        calendar_last_updated=calendar_data["last_updated"],
        tasks_last_updated=tasks_data["last_updated"]
    )

@app.get("/events")
async def get_events():
    """Get calendar events only."""
    return {
        "events": calendar_data["events"],
        "last_updated": calendar_data["last_updated"]
    }

@app.get("/tasks")
async def get_tasks():
    """Get tasks only."""
    return {
        "tasks": tasks_data["tasks"],
        "last_updated": tasks_data["last_updated"]
    }

@app.post("/sync")
async def manual_sync():
    """Manually trigger a data sync."""
    await sync_data()
    return {
        "message": "Data sync completed",
        "calendar_last_updated": calendar_data["last_updated"],
        "tasks_last_updated": tasks_data["last_updated"]
    }

@app.get("/recommendations")
async def get_recommendations():
    """Return recommendations text from GenAI (requires GEMINI_API_KEY in env)."""
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY not set in environment")

    client = genai.Client(api_key=api_key)    
    prompt = (
        "Help me plan my events for today alone - hourly tasks please based on my calendar and tasks. I'm a very bad procrastinator with ADHD. I need your help badly: this is my calendar and tasks data\n"
        + "Tasks:\n"
        + str(tasks_data)
        + "\nCalendar:\n"
        + str(calendar_data)
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    text = getattr(response, "text", None) or getattr(response, "content", None) or str(response)
    return {"recommendations": text}

def create_credentials_json_from_env():
    """Create Credentials object from GOOGLE_TOKEN_JSON environment variable."""
    payload = _build_credentials_payload_from_env()
    if not payload:
        raise HTTPException(status_code=400, detail="Google credentials not available in environment")

    try:
        return Credentials.from_authorized_user_info(payload, SCOPES)
    except Exception as e:
        logger.exception("Failed to create credentials from env")
        raise HTTPException(status_code=500, detail=f"Failed to create credentials: {str(e)}")
    

@app.get("/status")
async def get_status():
    """Get sync status and statistics."""
    creds = get_credentials()
    
    return {
        "authenticated": creds is not None and creds.valid,
        "scheduler_running": scheduler.running,
        "calendar_events_count": len(calendar_data["events"]),
        "tasks_count": len(tasks_data["tasks"]),
        "calendar_last_updated": calendar_data["last_updated"],
        "tasks_last_updated": tasks_data["last_updated"],
        "next_sync": "Every hour" if scheduler.running else "Scheduler not running"
    }

@app.get("/telegram_recommendation")
async def telegram_recommendation(telegram_token: Optional[str] = None):
    """Singular endpoint: send demo recommendation. Accepts optional telegram_token to override env token."""
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not chat_id:
        raise HTTPException(status_code=400, detail="TELEGRAM_CHAT_ID not set in environment")

    recommendation_data = await get_recommendations()
    content = recommendation_data.get("recommendations")

    print(telegram_token, chat_id, content)

    if content is None:
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")
    try:
        if telegram_token:
            sent = await asyncio.to_thread(send_message_with_token, telegram_token, chat_id, content)
        else:
            sent = await asyncio.to_thread(send_message, chat_id, content)
        return {"sent": bool(sent)}
    except Exception as e:
        logger.exception("Failed to send telegram demo message (singular)")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/telegram/messages")
async def get_telegram_messages(
    user_id: Optional[str] = None,
    limit: int = 10
):
    """Get recent messages from Telegram.
    
    Args:
        user_id: Optional Telegram user ID to filter messages. If not provided, uses TELEGRAM_CHAT_ID from env
        limit: Maximum number of messages to retrieve (default: 10)
    
    Returns:
        List of recent messages
    """
    target_user = user_id or os.getenv('TELEGRAM_CHAT_ID')
    if not target_user:
        raise HTTPException(
            status_code=400, 
            detail="user_id parameter or TELEGRAM_CHAT_ID environment variable must be set"
        )
    
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

@app.get("/telegram/updates")
async def get_telegram_updates(offset: Optional[int] = None, limit: int = 100):
    """Get all Telegram updates (messages, commands, etc.).
    
    Args:
        offset: Identifier of the first update to be returned
        limit: Maximum number of updates to retrieve (1-100, default: 100)
    
    Returns:
        Telegram updates response
    """
    try:
        updates = await asyncio.to_thread(get_updates, offset=offset, limit=limit)
        return updates
    except Exception as e:
        logger.exception("Failed to get Telegram updates")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/telegram/mark_read")
async def mark_telegram_read(update_id: int):
    """Mark Telegram messages as read up to the specified update_id.
    
    Args:
        update_id: The update_id of the last processed message
    
    Returns:
        Success status
    """
    try:
        success = await asyncio.to_thread(mark_updates_as_read, update_id)
        return {"success": success, "last_update_id": update_id}
    except Exception as e:
        logger.exception("Failed to mark Telegram updates as read")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/telegram/webhook")
async def telegram_webhook(update: Dict):
    """Webhook endpoint for receiving Telegram messages in real-time.
    
    To use this endpoint:
    1. Deploy your app with a public URL (e.g., using ngrok, Heroku, etc.)
    2. Set webhook: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_URL>/telegram/webhook
    
    This endpoint will automatically process incoming messages.
    """
    try:
        logger.info(f"Received Telegram webhook update: {update}")
        
        # Extract message information
        if "message" in update:
            message = update["message"]
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")
            from_user = message.get("from", {}).get("username", "unknown")
            
            logger.info(f"Message from {from_user} (chat_id: {chat_id}): {text}")
            
            # Here you can add custom logic to process incoming messages
            # For example, respond to specific commands:
            if text.startswith("/"):
                # Handle commands
                if text == "/start":
                    await asyncio.to_thread(
                        send_message, 
                        str(chat_id), 
                        "Welcome to GPlanner! I can help you manage your calendar and tasks."
                    )
                elif text == "/help":
                    help_text = (
                        "Available commands:\n"
                        "/start - Start the bot\n"
                        "/help - Show this help message\n"
                        "/events - Get your upcoming events\n"
                        "/tasks - Get your tasks\n"
                        "/recommendations - Get AI recommendations"
                    )
                    await asyncio.to_thread(send_message, str(chat_id), help_text)
                elif text == "/events":
                    events = calendar_data["events"][:5]  # Get first 5 events
                    if events:
                        events_text = "📅 Upcoming Events:\n\n"
                        for event in events:
                            summary = event.get("summary", "No title")
                            start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
                            events_text += f"• {summary}\n  {start}\n\n"
                    else:
                        events_text = "No upcoming events found."
                    await asyncio.to_thread(send_message, str(chat_id), events_text)
                elif text == "/tasks":
                    tasks = tasks_data["tasks"][:5]  # Get first 5 tasks
                    if tasks:
                        tasks_text = "✅ Your Tasks:\n\n"
                        for task in tasks:
                            title = task.get("title", "No title")
                            tasks_text += f"• {title}\n"
                    else:
                        tasks_text = "No tasks found."
                    await asyncio.to_thread(send_message, str(chat_id), tasks_text)
                elif text == "/recommendations":
                    # Generate recommendations
                    api_key = os.getenv('GEMINI_API_KEY')
                    if api_key:
                        client = genai.Client(api_key=api_key)
                        prompt = (
                            "Help me plan my events for today: this is my calendar and tasks data\n"
                            + "Tasks:\n"
                            + str(tasks_data)
                            + "\nCalendar:\n"
                            + str(calendar_data)
                        )
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt,
                        )
                        rec_text = getattr(response, "text", None) or str(response)
                        await asyncio.to_thread(send_message, str(chat_id), f"🤖 AI Recommendations:\n\n{rec_text}")
                    else:
                        await asyncio.to_thread(send_message, str(chat_id), "GEMINI_API_KEY not configured.")
            else:
                # Echo back non-command messages or implement custom logic
                await asyncio.to_thread(
                    send_message,
                    str(chat_id),
                    f"You said: {text}\n\nUse /help to see available commands."
                )
        
        return {"ok": True}
    except Exception as e:
        logger.exception("Error processing Telegram webhook")
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)