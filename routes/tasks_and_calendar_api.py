
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from routes.gemini_api import get_recommendations
from routes.google_auth import get_credentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_calendar_service():
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Google credentials not configured")
    return build("calendar", "v3", credentials=creds)


def _raise_from_http_error(exc: HttpError):
    status = getattr(exc, "status_code", None)
    resp = getattr(exc, "resp", None)
    if not status and resp is not None:
        status = getattr(resp, "status", None)
    detail = exc._get_reason() if hasattr(exc, "_get_reason") else str(exc)
    raise HTTPException(status_code=status or 500, detail=detail)


def _get_tasks_service():
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Google credentials not configured")
    return build("tasks", "v1", credentials=creds)

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


class EventCreateRequest(BaseModel):
    summary: str
    start: Dict[str, str]
    end: Dict[str, str]
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[Dict[str, str]]] = None


class EventUpdateRequest(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[Dict[str, str]]] = None
    start: Optional[Dict[str, str]] = None
    end: Optional[Dict[str, str]] = None


class EventRescheduleRequest(BaseModel):
    start: Dict[str, str]
    end: Dict[str, str]


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


@router.post("/events")
async def create_event(payload: EventCreateRequest):
    """Create a new Google Calendar event on the primary calendar."""

    service = _get_calendar_service()
    body = payload.dict(exclude_none=True)

    try:
        created = service.events().insert(calendarId="primary", body=body).execute()
        return {"event": created}
    except HttpError as exc:
        logger.exception("Google Calendar event creation failed")
        _raise_from_http_error(exc)
    except Exception as exc:
        logger.exception("Unexpected error creating Google Calendar event")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/events/{event_id}")
async def update_event(event_id: str, payload: EventUpdateRequest):
    """Patch fields on an existing event."""

    service = _get_calendar_service()
    body = payload.dict(exclude_unset=True, exclude_none=True)
    if not body:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    try:
        updated = service.events().patch(calendarId="primary", eventId=event_id, body=body).execute()
        return {"event": updated}
    except HttpError as exc:
        logger.exception("Google Calendar event update failed for %s", event_id)
        _raise_from_http_error(exc)
    except Exception as exc:
        logger.exception("Unexpected error updating event %s", event_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/events/{event_id}/reschedule")
async def reschedule_event(event_id: str, payload: EventRescheduleRequest):
    """Change the start/end of an event."""

    service = _get_calendar_service()
    body = payload.dict()

    try:
        updated = service.events().patch(calendarId="primary", eventId=event_id, body=body).execute()
        return {"event": updated}
    except HttpError as exc:
        logger.exception("Google Calendar event reschedule failed for %s", event_id)
        _raise_from_http_error(exc)
    except Exception as exc:
        logger.exception("Unexpected error rescheduling event %s", event_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/events/{event_id}")
async def delete_event(event_id: str):
    """Delete an event from the primary calendar."""

    service = _get_calendar_service()

    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return {"deleted": True, "event_id": event_id}
    except HttpError as exc:
        logger.exception("Google Calendar event delete failed for %s", event_id)
        _raise_from_http_error(exc)
    except Exception as exc:
        logger.exception("Unexpected error deleting event %s", event_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/daily_plan")
async def create_daily_plan(force: bool = False):
    """Generate a Gemini-crafted day plan and materialize it as a Google Tasks list."""

    tasks_service = _get_tasks_service()
    today = datetime.now()
    title = f"Daily Plan - {today.strftime('%Y-%m-%d')}"

    sync_response = await sync_data()
    calendar_data = sync_response.get("calendar_data", {})
    tasks_data = sync_response.get("tasks_data", {})
    existing_lists = {}
    
    tasklist = {}

    prompt = (
        "You are a productivity assistant. Build a concise schedule for today.\n"
        f"Today is {today.strftime('%A, %d %B %Y')}.")
    prompt += (
        "\nFocus on 5-7 entries. Each line must start with a realistic time like '08:30 AM'"
        " followed by a short description and one fun/filler detail."
        "\nExisting calendar events:\n" + str(calendar_data.get("events", []))
        + "\nExisting tasks:\n" + str(tasks_data.get("tasks", []))
    )

    gemini_output = await get_recommendations(prompt)
    plan_text = (gemini_output or {}).get("recommendations", "").strip()

    if not plan_text:
        plan_text = (
            "08:00 AM - Morning focus block with coffee check-in\n"
            "10:30 AM - Deep work sprint while listening to lo-fi beats\n"
            "12:30 PM - Lunch break with a quick walk outside\n"
            "15:00 PM - Catch up on emails and project notes\n"
            "19:00 PM - Wind down with planning for tomorrow"
        )

    lines = [line.strip("-• ") for line in plan_text.splitlines() if line.strip()]
    if not lines:
        lines = [plan_text]

    if not force:
        try:
            existing_lists = tasks_service.tasklists().list(maxResults=100).execute()
        except HttpError as exc:
            logger.exception("Failed to inspect Google Tasks lists before creation")
            _raise_from_http_error(exc)

        for existing in existing_lists.get("items", []):
            if existing.get("title") == title:
                existing_tasks = []
                try:
                    page = tasks_service.tasks().list(tasklist=existing["id"], maxResults=100).execute()
                    existing_tasks = [
                        {"id": item.get("id"), "title": item.get("title")}
                        for item in page.get("items", [])
                    ]
                except HttpError as exc:
                    logger.exception("Failed to fetch tasks for existing list %s", existing.get("id"))
                    _raise_from_http_error(exc)

                return {
                    "tasklist": {"id": existing.get("id"), "title": existing.get("title")},
                    "generated_plan": lines,
                    "task_count": len(existing_tasks),
                    "tasks": existing_tasks,
                    "source_text": plan_text,
                    "force_used": force,
                    "existing": True,
                }

    try:
        tasklist = tasks_service.tasklists().insert(body={"title": title}).execute()
    except HttpError as exc:
        logger.exception("Failed to create Google Tasks list %s", title)
        _raise_from_http_error(exc)

    due_time = datetime.utcnow().replace(hour=23, minute=59, second=0, microsecond=0).isoformat() + "Z"
    created_tasks = []

    for line in lines[:10]:  # cap to avoid runaway plans
        body = {
            "title": line,
            "notes": f"Auto-generated on {today.isoformat()}",
            "due": due_time,
        }
        try:
            task = tasks_service.tasks().insert(tasklist=tasklist["id"], body=body).execute()
            created_tasks.append({"id": task.get("id"), "title": task.get("title")})
        except HttpError as exc:
            logger.exception("Failed to add generated task to list %s", tasklist["id"])
            _raise_from_http_error(exc)

    return {
        "tasklist": {"id": tasklist.get("id"), "title": tasklist.get("title")},
        "generated_plan": lines,
        "task_count": len(created_tasks),
        "tasks": created_tasks,
        "source_text": plan_text,
        "force_used": force,
    }


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