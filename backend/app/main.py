from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.agents.tools import register_all_tools
from app.mcp.server import get_mcp_app

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_all_tools()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# 挂载 MCP SSE 端点
mcp_app = get_mcp_app()
app.mount("/mcp", mcp_app)


@app.get("/health")
async def health():
    return {"status": "ok", "mcp_endpoint": "/mcp/sse"}
