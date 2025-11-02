import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from routes.env_methods import set_env_var

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

active_env = os.getenv("ACTIVE_ENV", "development")

REDIRECT_URI = 'http://localhost:8000/auth/callback' if active_env == "development" else 'https://gplanner.vercel.app/auth/callback'
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/tasks.readonly'
]

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


@router.get("/")
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


@router.get("/callback")
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
        # try:
        #     await sync_data()
        #     sync_status = "Data sync completed successfully"
        # except Exception as e:
        #     logger.error(f"Initial sync failed: {e}")
        #     sync_status = f"Authentication successful but initial sync failed: {str(e)}"
        
        return {
            "message": "Authentication successful!",
            # "sync_status": sync_status,
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
