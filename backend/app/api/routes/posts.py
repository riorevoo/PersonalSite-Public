from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.schemas.errors import ErrorResponse
from app.schemas.posts import PostDetail, PostSummary
from app.services.knowledge import KnowledgeBase, get_knowledge

router = APIRouter(tags=["posts"])


@router.get("/posts")
async def list_posts(
    knowledge: Annotated[KnowledgeBase, Depends(get_knowledge)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[PostSummary]:
    """Published posts, newest first."""
    posts = knowledge.posts(include_drafts=settings.show_drafts)
    return [PostSummary.model_validate(post, from_attributes=True) for post in posts]


@router.get(
    "/posts/{slug}",
    responses={404: {"model": ErrorResponse, "description": "There is no post with this slug."}},
)
async def get_post(
    slug: str,
    knowledge: Annotated[KnowledgeBase, Depends(get_knowledge)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PostDetail:
    post = knowledge.post(slug, include_drafts=settings.show_drafts)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found.")
    return PostDetail.model_validate(post, from_attributes=True)
