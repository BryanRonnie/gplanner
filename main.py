import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from googleapiclient.discovery import build

from routes.tasks_and_calendar_api import sync_data
from routes.telegram_api import router as telegram_router, telegram_recommendation
from routes.google_auth import get_credentials, router as google_auth_router
from routes.env_methods import router as env_router

import uvicorn
from datetime import time as dtime, datetime
from apscheduler.triggers.cron import CronTrigger

# Load environment variables from .env file
load_dotenv('.env')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
app.include_router(telegram_router)
app.include_router(google_auth_router)

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    """Start the scheduler when the app starts."""
    # Initial sync
    # await sync_data()
    
    # Schedule hourly sync
    # scheduler.add_job(
    #     sync_data,
    #     trigger=IntervalTrigger(hours=1),
    #     id='sync_google_data',
    #     name='Sync Google Calendar and Tasks',
    #     replace_existing=True
    # )

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

@app.get("/status")
async def get_status():
    """Get sync status and statistics."""
    creds = get_credentials()

    response = await sync_data()
    calendar_data = response.get("calendar_data", {})
    tasks_data = response.get("tasks_data", {})
    
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
    uvicorn.run(app, host="0.0.0.0", port=8000)