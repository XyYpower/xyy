from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.notes import router as notes_router
from app.api.imports import router as import_router
from app.api.paths import router as paths_router
from app.api.review import router as review_router
from app.api.tags import router as tags_router
from app.api.categories import router as categories_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(notes_router)
api_router.include_router(import_router)
api_router.include_router(paths_router)
api_router.include_router(review_router)
api_router.include_router(tags_router)
api_router.include_router(categories_router)
