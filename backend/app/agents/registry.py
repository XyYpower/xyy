"""Tool Registry：将现有服务函数注册为可审计的 Agent 工具。"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

import uuid
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import ToolCall

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """工具统一输出格式。"""

    ok: bool = True
    data: Any = None
    summary: str = ""
    artifacts: list[dict] = []
    warnings: list[str] = []
    needs_approval: bool = False


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
        run_id: uuid.UUID | None = None,
        step_id: uuid.UUID | None = None,
        approval_granted: bool = False,
    ) -> ToolResult:
        """执行工具并返回统一结果。

        写工具（requires_approval=True）需要 approval_granted=True 才会执行。
        所有执行都会记录到 tool_calls 表。
        """
        tool = self._tools.get(name)
        if not tool:
            result = ToolResult(ok=False, summary=f"工具 {name} 未注册")
            await self._record_call(db, run_id, step_id, name, arguments, result, 0)
            return result

        # 写工具需要审批
        if tool.requires_approval and not approval_granted:
            result = ToolResult(
                ok=False,
                needs_approval=True,
                summary=f"工具 {name} 需要审批后才能执行",
            )
            await self._record_call(db, run_id, step_id, name, arguments, result, 0, status="denied")
            return result

        started = time.perf_counter()
        try:
            data = await tool.fn(db=db, user_id=user_id, **arguments)
            latency_ms = round((time.perf_counter() - started) * 1000)
            result = ToolResult(ok=True, data=data, summary=f"{name} 执行成功")
            await self._record_call(db, run_id, step_id, name, arguments, result, latency_ms)
            return result
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000)
            logger.warning("Tool %s failed after %dms: %s", name, latency_ms, exc)
            result = ToolResult(ok=False, summary=f"{name} 执行失败: {exc}")
            await self._record_call(db, run_id, step_id, name, arguments, result, latency_ms, status="error", error=str(exc))
            return result

    async def _record_call(
        self,
        db: AsyncSession,
        run_id: uuid.UUID | None,
        step_id: uuid.UUID | None,
        tool_name: str,
        arguments: dict,
        result: ToolResult,
        latency_ms: int,
        status: str = "success",
        error: str | None = None,
    ) -> None:
        """记录工具调用到 tool_calls 表。"""
        if not run_id:
            return
        call = ToolCall(
            run_id=run_id,
            step_id=step_id,
            tool_name=tool_name,
            arguments=arguments,
            result={"ok": result.ok, "summary": result.summary},
            status=status,
            latency_ms=latency_ms,
            error_message=error,
        )
        db.add(call)
        try:
            await db.flush()
        except Exception:
            logger.warning("Failed to record tool_call for %s", tool_name)


# 全局单例
registry = ToolRegistry()
