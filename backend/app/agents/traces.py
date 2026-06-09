"""Trace 记录器：自动记录 Agent 运行步骤和工具调用到数据库。"""

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentRun, AgentStep, ToolCall, AICallLog

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TraceRecorder:
    """记录一次 Agent 运行的 trace 数据。"""

    def __init__(self, db: AsyncSession, run_id: uuid.UUID, step_id: uuid.UUID | None = None):
        self.db = db
        self.run_id = run_id
        self.step_id = step_id

    async def record_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any] | None,
        latency_ms: int,
        status: str = "success",
        error_message: str | None = None,
    ) -> ToolCall:
        """记录一次工具调用。"""
        call = ToolCall(
            run_id=self.run_id,
            step_id=self.step_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status=status,
            latency_ms=latency_ms,
            error_message=error_message,
        )
        self.db.add(call)
        await self.db.flush()
        return call

    async def record_llm_call(
        self,
        user_id: uuid.UUID | None,
        provider: str,
        model: str,
        purpose: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        estimated_cost: float = 0.0,
        latency_ms: int = 0,
        status: str = "success",
        error_message: str | None = None,
    ) -> AICallLog:
        """记录一次 AI 调用。"""
        log = AICallLog(
            user_id=user_id,
            agent_run_id=self.run_id,
            provider=provider,
            model=model,
            purpose=purpose,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=estimated_cost,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.flush()
        return log


async def record_llm_call_standalone(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    provider: str,
    model: str,
    purpose: str,
    latency_ms: int = 0,
    status: str = "success",
    error_message: str | None = None,
    agent_run_id: uuid.UUID | None = None,
) -> AICallLog:
    """独立记录 AI 调用（不关联特定 AgentRun）。"""
    log = AICallLog(
        user_id=user_id,
        agent_run_id=agent_run_id,
        provider=provider,
        model=model,
        purpose=purpose,
        latency_ms=latency_ms,
        status=status,
        error_message=error_message,
    )
    db.add(log)
    await db.flush()
    return log


async def logged_llm_call(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    purpose: str,
    llm_call,
    agent_run_id: uuid.UUID | None = None,
) -> Any:
    """包装 LLM 调用，自动记录耗时和状态到 ai_call_logs。

    llm_call: 一个无参异步函数，调用后返回 LLM 结果。
    """
    from app.rag.llm import get_llm
    llm = get_llm()
    started = time.perf_counter()
    status = "success"
    error_message = None
    result = None
    try:
        result = await llm_call()
    except Exception as exc:
        status = "error"
        error_message = str(exc)[:500]
        raise
    finally:
        latency_ms = round((time.perf_counter() - started) * 1000)
        log = AICallLog(
            user_id=user_id,
            agent_run_id=agent_run_id,
            provider=llm.provider,
            model=llm.model,
            purpose=purpose,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        db.add(log)
        try:
            await db.flush()
        except Exception:
            logger.warning("Failed to flush AI call log")
    return result


async def logged_llm_stream(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    purpose: str,
    llm_stream_call,
    agent_run_id: uuid.UUID | None = None,
) -> AsyncGenerator[str, None]:
    """包装 LLM 流式调用，自动记录耗时和状态。"""
    from app.rag.llm import get_llm
    llm = get_llm()
    started = time.perf_counter()
    status = "success"
    error_message = None
    try:
        async for chunk in llm_stream_call():
            yield chunk
    except Exception as exc:
        status = "error"
        error_message = str(exc)[:500]
        raise
    finally:
        latency_ms = round((time.perf_counter() - started) * 1000)
        log = AICallLog(
            user_id=user_id,
            agent_run_id=agent_run_id,
            provider=llm.provider,
            model=llm.model,
            purpose=purpose,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        db.add(log)
        try:
            await db.flush()
        except Exception:
            logger.warning("Failed to flush AI call log")
