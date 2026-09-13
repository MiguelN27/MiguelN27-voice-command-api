from fastapi import APIRouter, HTTPException, Request, status
from starlette.datastructures import UploadFile

from src.app.schemas.voice import TranscribeFlowResponse
from src.app.services.groq_service import route_instruction_llm, transcribe_audio
from src.app.services.task_executor import execute_instruction
from src.app.utils.language import normalize_transcription_language

router = APIRouter(tags=["transcribe"])


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    content_type = request.headers.get("content-type", "").lower()
    transcription: str = ""

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from exc

        if not isinstance(body, dict) or not body.get("transcription"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Field 'transcription' is required in JSON body.",
            )
        transcription = str(body["transcription"]).strip()

    elif "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = form.get("file")
        if not file_obj or not isinstance(file_obj, UploadFile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Form field 'file' is required for audio transcription.",
            )

        raw_language = form.get("language")
        language = normalize_transcription_language(raw_language)
        file_bytes = await file_obj.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio file is empty.",
            )

        filename = file_obj.filename or "audio.webm"
        transcription = transcribe_audio(
            file_bytes=file_bytes,
            filename=filename,
            language=language,
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Content-Type must be 'multipart/form-data' or 'application/json'.",
        )

    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty transcription received.",
        )

    instruction = route_instruction_llm(transcription)
    result = execute_instruction(instruction)

    return TranscribeFlowResponse(
        transcription=transcription,
        instruction=instruction,
        result=result,
    )

