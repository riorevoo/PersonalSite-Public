from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """The shape of an error returned by the API (FastAPI's default `detail` key)."""

    detail: str
