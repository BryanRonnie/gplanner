import logging
import os
from fastapi import APIRouter, HTTPException
from google import genai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gemini", tags=["gemini"])

# @router.get("/recommendations")
async def get_recommendations(prompt: str):
    """Return recommendations text from GenAI (requires GEMINI_API_KEY in env)."""
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY not set in environment")

    client = genai.Client(api_key=api_key)    

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    text = getattr(response, "text", None) or getattr(response, "content", None) or str(response)
    return {"recommendations": text}
