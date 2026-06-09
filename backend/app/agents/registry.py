"""Tool Registry：将现有服务函数注册为可审计的 Agent 工具。"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

import uuid
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """工具统一输出格式。"""

    ok: bool = True
    data: Any = None
    summary: str = ""
    artifacts: list[dict] = []
    warnings: list[str] = []


@dataclass
class ToolDef:
    """工具定义。"""

    name: str
    description: str
    requires_approval: bool = False
    fn: Callable[..., Awaitable[Any]] = field(default=lambda: _noop)


async def _noop(**kwargs: Any) -> None:
    raise NotImplementedError("Tool function not registered")


class ToolRegistry:
    """全局工具注册表，单例模式。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool
        logger.info("Registered tool: %s", tool.name)

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDef]:
        return list(self._tools.values())

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> ToolResult:
        """执行工具并返回统一结果。"""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(ok=False, summary=f"工具 {name} 未注册")

        started = time.perf_counter()
        try:
            result = await tool.fn(db=db, user_id=user_id, **arguments)
            latency_ms = round((time.perf_counter() - started) * 1000)
            return ToolResult(
                ok=True,
                data=result,
                summary=f"{name} 执行成功",
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000)
            logger.warning("Tool %s failed after %dms: %s", name, latency_ms, exc)
            return ToolResult(ok=False, summary=f"{name} 执行失败: {exc}")


# 全局单例
registry = ToolRegistry()
