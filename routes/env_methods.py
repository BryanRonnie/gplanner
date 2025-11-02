
import logging
import os
from typing import Optional

from dotenv import set_key
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/env", tags=["environment"])


def _mask_value(value: Optional[str]) -> str:
    if value is None:
        return "<missing>"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:2]}***{value[-4:]}"


class EnvUpdate(BaseModel):
    key: str
    value: str
    persist: Optional[bool] = False


# @router.get("/{key}")
async def get_env(
    key: str,
    reveal: bool = False,
    x_admin_token: Optional[str] = Header(default=None, alias="X-ADMIN-TOKEN"),
):
    """Return a masked or full environment variable depending on reveal flag."""

    value = os.getenv(key)
    admin_token = os.getenv("ADMIN_TOKEN")

    if reveal:
        if admin_token and x_admin_token != admin_token:
            raise HTTPException(status_code=403, detail="Invalid admin token")
        return {"key": key, "present": value is not None, "value": value}

    return {"key": key, "present": value is not None, "value": _mask_value(value)}


# @router.post("/set-env")
async def set_env(
    payload: EnvUpdate,
    x_admin_token: Optional[str] = Header(default=None, alias="X-ADMIN-TOKEN"),
):
    """Set or update an environment variable and optionally persist it to .env."""

    admin_token = os.getenv("ADMIN_TOKEN")
    if admin_token and x_admin_token != admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    os.environ[payload.key] = payload.value

    persisted = False
    if payload.persist:
        try:
            set_key(".env", payload.key, payload.value)
            persisted = True
        except Exception:  # pragma: no cover - logging only
            logger.exception("Failed to persist env to .env")

    return {"key": payload.key, "present": True, "persisted": persisted}


def set_env_var(key: str, value, persist: bool = False):
    """
    Helper to set an environment variable and optionally persist it to .env.
    """
    os.environ[key] = "" if value is None else str(value)
    if persist:
        try:
            set_key(".env", key, os.environ[key])
        except Exception:
            logger.exception("Failed to persist env to .env")

