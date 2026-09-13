from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.services import task_store


@pytest.fixture(autouse=True)
def reset_tasks():
    task_store.tasks.clear()
    task_store._id_counter = iter(range(1, 10000))
    yield
    task_store.tasks.clear()


client = TestClient(app)


# ===================== TASK CRUD TESTS =====================

def test_get_tasks_empty():
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_create_task():
    response = client.post("/tasks", json={"title": "Buy milk", "done": False})
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Buy milk"
    assert data["done"] is False

    get_res = client.get("/tasks")
    assert len(get_res.json()) == 1


def test_replace_task():
    create_res = client.post("/tasks", json={"title": "Original task", "done": False})
    task_id = create_res.json()["id"]

    replace_res = client.put(f"/tasks/{task_id}", json={"title": "Replaced task", "done": True})
    assert replace_res.status_code == 200
    assert replace_res.json() == {"id": task_id, "title": "Replaced task", "done": True}


def test_replace_task_not_found():
    response = client.put("/tasks/999", json={"title": "Non-existent", "done": True})
    assert response.status_code == 404


def test_update_task():
    create_res = client.post("/tasks", json={"title": "Initial", "done": False})
    task_id = create_res.json()["id"]

    patch_res = client.patch(f"/tasks/{task_id}", json={"done": True})
    assert patch_res.status_code == 200
    assert patch_res.json()["done"] is True
    assert patch_res.json()["title"] == "Initial"


def test_update_task_not_found():
    response = client.patch("/tasks/999", json={"done": True})
    assert response.status_code == 404


def test_delete_task():
    create_res = client.post("/tasks", json={"title": "To delete", "done": False})
    task_id = create_res.json()["id"]

    del_res = client.delete(f"/tasks/{task_id}")
    assert del_res.status_code == 200
    assert del_res.json() == {"detail": f"Task {task_id} deleted"}

    get_res = client.get("/tasks")
    assert len(get_res.json()) == 0


def test_delete_task_not_found():
    response = client.delete("/tasks/999")
    assert response.status_code == 404


# ===================== INSTRUCTION ROUTING TESTS =====================

@patch("src.app.services.groq_service.get_groq_client")
def test_instruction_endpoint_routing(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = '{"endpoint": "/tasks", "method": "POST", "params": {"title": "Call mom"}}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    response = client.post("/instruction", json={"transcription": "add call mom to my tasks"})
    assert response.status_code == 200
    data = response.json()
    assert data["endpoint"] == "/tasks"
    assert data["method"] == "POST"
    assert data["params"] == {"title": "Call mom"}


# ===================== TRANSCRIBE END-TO-END FLOW TESTS =====================

@patch("src.app.services.groq_service.get_groq_client")
def test_transcribe_json_create_flow(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = '{"endpoint": "/tasks", "method": "POST", "params": {"title": "Water plants"}}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    response = client.post("/transcribe", json={"transcription": "add water plants"})
    assert response.status_code == 200
    data = response.json()
    assert data["transcription"] == "add water plants"
    assert data["instruction"]["endpoint"] == "/tasks"
    assert data["instruction"]["method"] == "POST"
    assert data["result"]["title"] == "Water plants"
    assert data["result"]["id"] == 1


@patch("src.app.services.groq_service.get_groq_client")
def test_transcribe_json_list_flow(mock_get_client):
    task_store.create_task("Existing Task 1")
    task_store.create_task("Existing Task 2")

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = '{"endpoint": "/tasks", "method": "GET", "params": {}}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    response = client.post("/transcribe", json={"transcription": "show my tasks"})
    assert response.status_code == 200
    data = response.json()
    assert data["instruction"]["method"] == "GET"
    assert len(data["result"]) == 2


@patch("src.app.services.groq_service.get_groq_client")
def test_transcribe_json_update_flow(mock_get_client):
    task = task_store.create_task("Task to finish")
    task_id = task["id"]

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = f'{{"endpoint": "/tasks/{task_id}", "method": "PATCH", "params": {{"done": true}}}}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    response = client.post("/transcribe", json={"transcription": f"mark task {task_id} as done"})
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["done"] is True


@patch("src.app.services.groq_service.get_groq_client")
def test_transcribe_json_delete_flow(mock_get_client):
    task = task_store.create_task("Task to remove")
    task_id = task["id"]

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = f'{{"endpoint": "/tasks/{task_id}", "method": "DELETE", "params": {{}}}}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    response = client.post("/transcribe", json={"transcription": f"delete task {task_id}"})
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == {"detail": f"Task {task_id} deleted"}
    assert len(task_store.list_tasks()) == 0


@patch("src.app.services.groq_service.get_groq_client")
def test_transcribe_audio_flow(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Mock audio transcription
    mock_audio_res = MagicMock()
    mock_audio_res.text = "Add clean bedroom"
    mock_client.audio.transcriptions.create.return_value = mock_audio_res

    # Mock LLM chat completion
    mock_choice = MagicMock()
    mock_choice.message.content = '{"endpoint": "/tasks", "method": "POST", "params": {"title": "Clean bedroom"}}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    dummy_audio = b"dummy_audio_bytes"
    response = client.post(
        "/transcribe",
        files={"file": ("test.webm", dummy_audio, "audio/webm")},
        data={"language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["transcription"] == "Add clean bedroom"
    assert data["result"]["title"] == "Clean bedroom"


def test_transcribe_invalid_language():
    response = client.post(
        "/transcribe",
        files={"file": ("test.webm", b"dummy_audio", "audio/webm")},
        data={"language": "invalid-lang-code-1234"},
    )
    assert response.status_code == 400


def test_transcribe_unsupported_content_type():
    response = client.post("/transcribe", content="plain text", headers={"Content-Type": "text/plain"})
    assert response.status_code == 415


def test_healthcheck():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

