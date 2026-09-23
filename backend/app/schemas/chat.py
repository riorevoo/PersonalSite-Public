from typing import Literal

from pydantic import BaseModel, Field

# Request limits. The frontend's history cap (MAX_HISTORY_TURNS in useChat.ts) must stay <= this.
MAX_HISTORY_TURNS = 20
MAX_TURN_CHARS = 4000


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_TURN_CHARS)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="The visitor's question.")
    history: list[ChatTurn] = Field(
        default_factory=list,
        max_length=MAX_HISTORY_TURNS,
        description="Earlier turns in this conversation, oldest first.",
    )


class ChatResponse(BaseModel):
    answer: str
