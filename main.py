import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/tasks.readonly'
]
CREDENTIALS_FILE = 'credentials.json'  # Download from Google Cloud Console
TOKEN_FILE = 'token.json'
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

def get_credentials():
    """Load or refresh Google API credentials."""
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the refreshed credentials
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                logger.error(f"Error refreshing credentials: {e}")
                return None
        else:
            return None
    
    return creds

def create_auth_flow():
    """Create OAuth2 flow for authentication."""
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"Please download your OAuth2 credentials file and save it as '{CREDENTIALS_FILE}'"
        )
    
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow

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
    """Fetch tasks from Google Tasks API."""
    try:
        creds = get_credentials()
        if not creds:
            logger.warning("No valid credentials available for tasks sync")
            return []
        
        service = build('tasks', 'v1', credentials=creds)
        
        # Get all task lists
        task_lists = service.tasklists().list().execute()
        all_tasks = []
        
        for task_list in task_lists.get('items', []):
            tasks = service.tasks().list(
                tasklist=task_list['id'],
                showCompleted=False,  # Only get incomplete tasks
                maxResults=100
            ).execute()
            
            for task in tasks.get('items', []):
                task['taskListId'] = task_list['id']
                task['taskListTitle'] = task_list['title']
                all_tasks.append(task)
        
        logger.info(f"Fetched {len(all_tasks)} tasks")
        return all_tasks
        
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
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
            "status": "/status - Check sync status"
        }
    }

@app.get("/auth")
async def auth():
    """Start the OAuth2 authentication flow."""
    try:
        flow = create_auth_flow()
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return {"auth_url": authorization_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth setup failed: {str(e)}")

@app.get("/auth/callback")
async def auth_callback(code: str):
    """Handle OAuth2 callback and save credentials."""
    try:
        flow = create_auth_flow()
        flow.fetch_token(code=code)
        
        creds = flow.credentials
        
        # Save credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        
        # Trigger initial sync
        await sync_data()
        
        return {"message": "Authentication successful! Data sync initiated."}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

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
    creds = get_credentials()

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents= "Help me plan my events for today: this is my calendar and tasks data" + str(tasks_data) + str(calendar_data),
    )

    return response.text

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)