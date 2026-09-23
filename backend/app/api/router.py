from fastapi import APIRouter

from app.api.routes import chat, health, posts, resume

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(posts.router)
api_router.include_router(resume.router)
