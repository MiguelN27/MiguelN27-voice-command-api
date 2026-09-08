from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate
from src.app.services import task_store

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def get_tasks() -> list[dict[str, object]]:
    return task_store.list_tasks()


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> dict[str, object]:
    return task_store.create_task(title=payload.title, done=payload.done)


@router.put("/{task_id}", response_model=Task)
def replace_task(
    task_id: int,
    payload: TaskReplace,
) -> dict[str, object]:
    task = task_store.replace_task(task_id, title=payload.title, done=payload.done)
    if task is None:
        raise task_not_found(task_id)
    return task


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    payload: TaskUpdate,
) -> dict[str, object]:
    task = task_store.update_task(task_id, title=payload.title, done=payload.done)
    if task is None:
        raise task_not_found(task_id)
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    if not task_store.delete_task(task_id):
        raise task_not_found(task_id)
    return {"detail": f"Task {task_id} deleted"}


def task_not_found(task_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found",
    )
