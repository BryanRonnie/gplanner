
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
from googleapiclient.discovery import build

from fastapi import APIRouter
from pydantic import BaseModel

from routes.google_auth import get_credentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

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


@router.get("/data", response_model=DataResponse)
async def get_all_data():
    """Get all calendar events and tasks."""

    response = await sync_data()
    calendar_data = response.get("calendar_data", {})
    tasks_data = response.get("tasks_data", {})

    return DataResponse(
        events=[CalendarEvent(**event) for event in calendar_data["events"]],
        tasks=[Task(**task) for task in tasks_data["tasks"]],
        calendar_last_updated=calendar_data["last_updated"],
        tasks_last_updated=tasks_data["last_updated"]
    )

@router.get("/events")
async def get_events():
    """Get calendar events only."""

    response = await sync_data()
    calendar_data = response.get("calendar_data", {})

    return {
        "events": calendar_data["events"],
        "last_updated": calendar_data["last_updated"]
    }

@router.get("/tasks")
async def get_tasks():
    """Get tasks only."""

    response = await sync_data()
    tasks_data = response.get("tasks_data", {})
    return {
        "tasks": tasks_data["tasks"],
        "last_updated": tasks_data["last_updated"]
    }

# @router.post("/sync")
# async def manual_sync():
#     """Manually trigger a data sync."""
#     await sync_data()
#     return {
#         "message": "Data sync completed",
#         "calendar_last_updated": calendar_data["last_updated"],
#         "tasks_last_updated": tasks_data["last_updated"]
#     }

async def sync_data():
    """Background task to sync calendar and tasks data."""
    
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

    return {"calendar_data": calendar_data, "tasks_data": tasks_data}

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
