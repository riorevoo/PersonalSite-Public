import datetime

from pydantic import BaseModel, Field


class PostSummary(BaseModel):
    slug: str = Field(description="The URL part: /writing/<slug>.")
    title: str
    dek: str = Field(description="One-sentence summary shown under the title.")
    tag: str
    date: datetime.date
    read_minutes: int = Field(ge=1, description="Estimated reading time in minutes.")
    draft: bool = Field(description="True only for a draft shown because APP_SHOW_DRAFTS is on.")


class PostDetail(PostSummary):
    body: str = Field(description="The post as Markdown.")
