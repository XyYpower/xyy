from fastapi import APIRouter

from app.api.notes import router as notes_router
from app.api.tags import router as tags_router
from app.api.categories import router as categories_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(notes_router)
api_router.include_router(tags_router)
api_router.include_router(categories_router)
