import json
from functools import lru_cache
from typing import Any

from fastapi import HTTPException, status
from groq import Groq

from src.app.core.config import Settings, get_settings
from src.app.schemas.voice import InstructionPayload

SYSTEM_PROMPT = """You are a backend instruction router for a voice-controlled task management API.
Given a natural language transcription of a user's command, you must determine the appropriate HTTP endpoint, HTTP method, and parameters.

Available Task API endpoints:
- GET /tasks -> Retrieve all tasks. params: {}
- POST /tasks -> Create a new task. params: {"title": "<task title>"} (or optional "done": false)
- PUT /tasks/<task_id> -> Replace the full task object. params: {"title": "<new title>", "done": <bool>}
- PATCH /tasks/<task_id> -> Partially update a task (e.g., mark as done/undone, change title). params: {"title": "<new title>"} and/or {"done": <bool>}
- DELETE /tasks/<task_id> -> Delete a task with the given ID. params: {}

Rules:
1. Output MUST be a valid JSON object with exactly three fields:
   - "endpoint": string (e.g., "/tasks" or "/tasks/1")
   - "method": string (one of "GET", "POST", "PUT", "PATCH", "DELETE")
   - "params": object with the appropriate fields
2. When the user references a specific task ID (e.g. "task 2", "item 1", "number 3"), include the integer ID in the endpoint path (e.g. "/tasks/2").
3. Do not include any explanations, markdown formatting, or text outside the JSON object.
"""


def get_groq_client() -> Groq:
    settings: Settings = get_settings()
    return Groq(
        api_key=settings.groq_api_key,
        timeout=settings.request_timeout_seconds,
    )


def route_instruction_llm(transcription: str) -> InstructionPayload:
    """Use Groq LLM to convert transcription to structured routing instructions."""
    settings: Settings = get_settings()
    client = get_groq_client()

    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcription},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        data = json.loads(content)
        return InstructionPayload(
            endpoint=data.get("endpoint", "/tasks"),
            method=str(data.get("method", "GET")).upper(),
            params=data.get("params", {}) if isinstance(data.get("params"), dict) else {},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to route instruction with LLM: {str(exc)}",
        ) from exc


def transcribe_audio(
    file_bytes: bytes,
    filename: str = "audio.webm",
    language: str | None = None,
) -> str:
    """Transcribe audio bytes using Groq Whisper."""
    settings: Settings = get_settings()
    client = get_groq_client()

    try:
        kwargs: dict[str, Any] = {
            "file": (filename, file_bytes),
            "model": settings.groq_transcription_model,
        }
        if language:
            kwargs["language"] = language

        transcription_res = client.audio.transcriptions.create(**kwargs)
        transcription_text = transcription_res.text.strip()
        if not transcription_text:
            raise ValueError("Whisper returned an empty transcription.")
        return transcription_text
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Audio transcription failed: {str(exc)}",
        ) from exc
