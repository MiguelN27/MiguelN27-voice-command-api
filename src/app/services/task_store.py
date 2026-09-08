"""In-memory storage for tasks. Resets whenever the server restarts."""

from itertools import count

tasks: list[dict[str, object]] = []

_id_counter = count(1)


def list_tasks() -> list[dict[str, object]]:
    return tasks


def create_task(title: str, done: bool = False) -> dict[str, object]:
    task = {"id": next(_id_counter), "title": title, "done": done}
    tasks.append(task)
    return task


def get_task(task_id: int) -> dict[str, object] | None:
    return next((task for task in tasks if task["id"] == task_id), None)


def replace_task(task_id: int, title: str, done: bool) -> dict[str, object] | None:
    task = get_task(task_id)
    if task is None:
        return None
    task["title"] = title
    task["done"] = done
    return task


def update_task(
    task_id: int, title: str | None = None, done: bool | None = None
) -> dict[str, object] | None:
    task = get_task(task_id)
    if task is None:
        return None
    if title is not None:
        task["title"] = title
    if done is not None:
        task["done"] = done
    return task


def delete_task(task_id: int) -> bool:
    task = get_task(task_id)
    if task is None:
        return False
    tasks.remove(task)
    return True
