# Progress Logbook

## Project

Voice Command API. This logbook tracks progress against `tech-lead-instruction.png` and the current repository contract in `README.md`.

## Completed

### Stage 1: In-memory task CRUD

Status: **Complete**

- Added module-level in-memory task storage with incremental IDs.
- Implemented task operations in `src/app/services/task_store.py`:
  - list tasks
  - create task
  - replace task
  - partially update task
  - delete task
- Exposed all required endpoints in `src/app/api/routes/tasks.py`:
  - `GET /tasks`
  - `POST /tasks`
  - `PUT /tasks/{task_id}`
  - `PATCH /tasks/{task_id}`
  - `DELETE /tasks/{task_id}`
- Added request and response validation through the Pydantic models in `src/app/schemas/voice.py`.
- Storage intentionally resets when the backend restarts. No database or file persistence is used.

### Project foundation

Status: **Complete / prepared**

- FastAPI application and CORS configuration are defined in `src/app/main.py`.
- Groq settings, model names, request timeout, and allowed origins are defined in `src/app/core/config.py`.
- Language validation helpers are prepared in `src/app/utils/language.py`.
- The frontend is already implemented and sends audio or manual transcription to `POST /transcribe`.

### Stage 2: Instruction routing

Status: **Complete**

- Built reusable Groq routing and transcription client service in `src/app/services/groq_service.py`.
- Configured controlled system prompt to convert natural language commands into strict JSON routing instructions (`endpoint`, `method`, `params`).
- Replaced the 501 placeholder in `src/app/api/routes/instruction.py`.
- `POST /instruction` returns routing JSON only without mutating task storage.

### Stage 3: Voice-to-action flow

Status: **Complete**

- Implemented `src/app/services/task_executor.py` to dispatch routed instructions to in-memory task store.
- Implemented `POST /transcribe` in `src/app/api/routes/transcribe.py`:
  - Handles multipart/form-data audio uploads (`file` and optional `language` fields) with Groq Whisper.
  - Handles manual JSON fallback (`{"transcription": "..."}`).
  - Routes instructions via Groq LLM and executes task actions against in-memory storage.
  - Returns `{ transcription, instruction, result }`.
- Added Web Speech API synthesis in `frontend/src/main.ts` so all action results and confirmations are spoken loud.

### Stage 4: Test and verify

Status: **Complete**

- Added automated test suite in `tests/test_api.py` covering:
  - Task CRUD endpoints (`GET /tasks`, `POST /tasks`, `PUT /tasks/{id}`, `PATCH /tasks/{id}`, `DELETE /tasks/{id}`).
  - Instruction routing endpoint (`POST /instruction`).
  - End-to-end flow with manual JSON and audio uploads (`POST /transcribe`).
  - Input validation, language normalization, and error responses.
- Verified test suite passes with `uv run pytest`.
- Verified frontend build passes with `npm run build`.

## Summary of All Stages

| Stage | Description | Status |
|---|---|---|
| Stage 1 | In-memory task CRUD | ✅ Complete |
| Stage 2 | Instruction routing via Groq LLM | ✅ Complete |
| Stage 3 | Voice-to-action flow (/transcribe) & TTS playback | ✅ Complete |
| Stage 4 | Automated test suite and verification | ✅ Complete |
