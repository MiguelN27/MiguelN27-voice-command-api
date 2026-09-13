import re
from typing import Any

from fastapi import HTTPException, status

from src.app.schemas.voice import InstructionPayload
from src.app.services import task_store


def extract_task_id(endpoint: str, params: dict[str, Any]) -> int | None:
    """Extract integer task_id from endpoint path or params."""
    match = re.search(r"/tasks/(\d+)", endpoint)
    if match:
        return int(match.group(1))

    if "id" in params and isinstance(params["id"], (int, str)) and str(params["id"]).isdigit():
        return int(params["id"])

    if "task_id" in params and isinstance(params["task_id"], (int, str)) and str(params["task_id"]).isdigit():
        return int(params["task_id"])

    return None


def execute_instruction(instruction: InstructionPayload) -> Any:
    """Execute the routed task instruction against the in-memory task store."""
    method = instruction.method.upper()
    endpoint = instruction.endpoint.rstrip("/")
    params = instruction.params or {}

    if method == "GET" and (endpoint == "/tasks" or endpoint == ""):
        return task_store.list_tasks()

    if method == "POST" and (endpoint == "/tasks" or endpoint == ""):
        title = str(params.get("title", "")).strip()
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title is required to create a task",
            )
        done = bool(params.get("done", False))
        return task_store.create_task(title=title, done=done)

    task_id = extract_task_id(instruction.endpoint, params)
    if task_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not determine task ID for {method} {instruction.endpoint}",
        )

    if method == "PUT":
        title = str(params.get("title", "")).strip()
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title is required to replace a task",
            )
        done = bool(params.get("done", False))
        task = task_store.replace_task(task_id, title=title, done=done)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        return task

    if method == "PATCH":
        title = params.get("title")
        if title is not None:
            title = str(title).strip()
            if not title:
                title = None
        done = params.get("done")
        if done is not None:
            done = bool(done)
        task = task_store.update_task(task_id, title=title, done=done)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        return task

    if method == "DELETE":
        if not task_store.delete_task(task_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        return {"detail": f"Task {task_id} deleted"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported route or method: {method} {instruction.endpoint}",
    )
