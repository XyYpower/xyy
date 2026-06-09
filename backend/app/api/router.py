from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.notes import router as notes_router
from app.api.imports import router as import_router
from app.api.paths import router as paths_router
from app.api.review import router as review_router
from app.api.chat import router as chat_router
from app.api.interview import router as interview_router
from app.api.export import router as export_router
from app.api.tags import router as tags_router
from app.api.categories import router as categories_router
from app.api.traces import router as traces_router
from app.api.workspace import router as workspace_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(notes_router)
api_router.include_router(import_router)
api_router.include_router(paths_router)
api_router.include_router(review_router)
api_router.include_router(chat_router)
api_router.include_router(interview_router)
api_router.include_router(export_router)
api_router.include_router(tags_router)
api_router.include_router(categories_router)
api_router.include_router(traces_router)
api_router.include_router(workspace_router)
