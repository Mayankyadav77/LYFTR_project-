import os
import sys
from typing import Optional, List
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from app.db import init_db, save_message, get_session_messages, session_exists
from app.llm import LLMService, AllKeysFailedException

app = FastAPI(title="Lyftr AI Backend", version="1.0.0")

# Setup CORS
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip().rstrip("/") for o in allowed_origins_raw.split(",") if o.strip()]
if not origins or "*" in origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_service = LLMService()

@app.on_event("startup")
def on_startup():
    init_db()

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str
    system_prompt: Optional[str] = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        trimmed = v.strip()
        if not (1 <= len(trimmed) <= 4000):
            raise ValueError("message must be between 1 and 4000 chars after trimming whitespace")
        return trimmed

class MetadataResponse(BaseModel):
    resolution_source: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: Optional[str] = None
    fallback_attempts: int

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: MetadataResponse

@app.get("/health")
def health():
    return {
        "status": "ok",
        "keys_configured": llm_service.get_configured_keys_count(),
        "cache_enabled": llm_service.is_cache_enabled()
    }

@app.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    x_simulate_failure: Optional[str] = Header(None, alias="X-Simulate-Failure")
):
    session_id = payload.session_id
    user_message = payload.message
    system_prompt = payload.system_prompt or "You are Lyftr AI, a helpful, intelligent and reliable assistant."

    # Fetch existing session history from SQLite
    history = get_session_messages(session_id)

    # Build prompt messages for the LLM
    llm_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        llm_messages.append({"role": msg["role"], "content": msg["content"]})
    llm_messages.append({"role": "user", "content": user_message})

    try:
        completion_result = llm_service.chat_completion(
            messages=llm_messages,
            sim_header=x_simulate_failure
        )
    except AllKeysFailedException:
        # A request that fails (422 or 503) is not added to the session history
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="all providers unavailable"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="all providers unavailable"
        )

    # If successful, commit user message and assistant reply to DB
    save_message(session_id=session_id, role="user", content=user_message, metadata=None)
    save_message(
        session_id=session_id,
        role="assistant",
        content=completion_result["reply"],
        metadata=completion_result["metadata"]
    )

    return {
        "session_id": session_id,
        "reply": completion_result["reply"],
        "metadata": completion_result["metadata"]
    }

@app.get("/sessions/{session_id}/messages")
def get_session_history(session_id: str):
    if not session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="session not found"
        )

    messages = get_session_messages(session_id)
    formatted_messages = []
    for msg in messages:
        item = {"role": msg["role"], "content": msg["content"]}
        if msg["role"] == "assistant" and msg.get("metadata"):
            item["metadata"] = {
                "resolution_source": msg["metadata"].get("resolution_source"),
                "input_tokens": msg["metadata"].get("input_tokens"),
                "output_tokens": msg["metadata"].get("output_tokens")
            }
        formatted_messages.append(item)

    return {
        "session_id": session_id,
        "messages": formatted_messages
    }
