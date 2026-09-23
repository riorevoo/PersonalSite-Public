from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.errors import ErrorResponse
from app.services.answerer import Answerer, get_answerer
from app.services.errors import EngineUnavailableError

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    responses={
        413: {"model": ErrorResponse, "description": "Request body is too large."},
        429: {"model": ErrorResponse, "description": "Too many questions from this address."},
        503: {"model": ErrorResponse, "description": "The answering engine is unavailable."},
    },
)
async def chat(
    payload: ChatRequest,
    request: Request,
    answerer: Annotated[Answerer, Depends(get_answerer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Message is empty.")
    if len(message) > settings.max_message_chars:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Message is longer than {settings.max_message_chars} characters.",
        )
    # Sizes only, never the text: visitors' questions are not logged.
    request.state.log_fields = {
        "engine": settings.answerer,
        "message_chars": len(message),
        "history_turns": len(payload.history),
    }
    try:
        answer = await answerer.answer(message, payload.history)
    except EngineUnavailableError as error:
        # The cause (provider, spend counters) is already logged; visitors only get a retry.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "The answering service is unavailable right now."
        ) from error
    return ChatResponse(answer=answer)
