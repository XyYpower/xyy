"""LangGraph Adapter：将 Agent 工作流接入 LangGraph 的 StateGraph。

支持长任务持久化、暂停/恢复和 human-in-the-loop。
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from app.database import async_session
from app.agents import runtime, diagnosis, planner
from app.services import note_service

logger = logging.getLogger(__name__)


# ── State 定义 ──────────────────────


class AgentState(TypedDict):
    """Agent 工作流状态。"""
    user_id: str
    run_id: str | None
    goal: str
    diagnosis: dict | None
    plan: dict | None
    current_step: str
    messages: Annotated[list[dict], add_messages]
    error: str | None
    needs_approval: bool
    approval_result: str | None


# ── Node 函数 ──────────────────────


async def diagnose_node(state: AgentState) -> dict:
    """诊断节点：分析用户学习状态。"""
    user_id = uuid.UUID(state["user_id"])
    async with async_session() as db:
        try:
            result = await diagnosis.diagnose(db, user_id)
            return {
                "diagnosis": result,
                "current_step": "diagnosis_complete",
                "messages": [{"role": "assistant", "content": f"诊断完成：{result.get('summary', '')}"}],
            }
        except Exception as exc:
            logger.warning("Diagnosis failed: %s", exc)
            return {"error": str(exc), "current_step": "diagnosis_failed"}


async def plan_node(state: AgentState) -> dict:
    """规划节点：生成学习路径。"""
    user_id = uuid.UUID(state["user_id"])
    goal = state["goal"]
    diag = state.get("diagnosis")

    async with async_session() as db:
        try:
            result = await planner.plan(db, user_id, goal, diag)
            return {
                "plan": result,
                "current_step": "plan_complete",
                "needs_approval": True,
                "messages": [{"role": "assistant", "content": f"已生成学习计划：{result.get('name', '')}，共 {result.get('tasks_count', 0)} 个任务。请确认是否采纳。"}],
            }
        except Exception as exc:
            logger.warning("Planning failed: %s", exc)
            return {"error": str(exc), "current_step": "plan_failed"}


async def approval_node(state: AgentState) -> dict:
    """人工确认节点：等待用户确认。"""
    approval = state.get("approval_result")
    if approval == "approved":
        return {
            "current_step": "approved",
            "needs_approval": False,
            "messages": [{"role": "assistant", "content": "计划已确认，学习任务已创建。"}],
        }
    return {
        "current_step": "rejected",
        "needs_approval": False,
        "messages": [{"role": "assistant", "content": "计划已拒绝。请调整目标后重新规划。"}],
    }


async def finalize_node(state: AgentState) -> dict:
    """完成节点：更新 AgentRun 状态。"""
    run_id = state.get("run_id")
    if run_id:
        async with async_session() as db:
            await runtime.update_run_status(db, uuid.UUID(run_id), "completed", output={
                "diagnosis": state.get("diagnosis"),
                "plan": state.get("plan"),
            })
            await db.commit()
    return {"current_step": "completed"}


# ── 条件边 ──────────────────────


def should_continue(state: AgentState) -> str:
    """决定下一步走向。"""
    if state.get("error"):
        return "finalize"
    if state.get("needs_approval"):
        return "wait_approval"
    return "finalize"


def after_approval(state: AgentState) -> str:
    """确认后走向。"""
    return "finalize"


# ── Graph 构建 ──────────────────────


def build_learning_workflow() -> StateGraph:
    """构建学习规划工作流图。"""
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("plan", plan_node)
    graph.add_node("wait_approval", approval_node)
    graph.add_node("finalize", finalize_node)

    # 设置入口
    graph.set_entry_point("diagnose")

    # 添加边
    graph.add_edge("diagnose", "plan")
    graph.add_conditional_edges("plan", should_continue, {
        "wait_approval": "wait_approval",
        "finalize": "finalize",
    })
    graph.add_conditional_edges("wait_approval", after_approval, {
        "finalize": "finalize",
    })
    graph.add_edge("finalize", END)

    return graph


# ── 执行入口 ──────────────────────


# 全局 checkpointer（内存版，生产可换 PostgreSQL）
_checkpointer = MemorySaver()


async def run_learning_workflow(
    user_id: uuid.UUID,
    goal: str,
    thread_id: str | None = None,
) -> dict:
    """运行学习规划工作流。

    Args:
        user_id: 用户 ID
        goal: 学习目标
        thread_id: 线程 ID（用于暂停/恢复）

    Returns:
        工作流执行结果
    """
    graph = build_learning_workflow()
    app = graph.compile(checkpointer=_checkpointer)

    # 创建 AgentRun 记录
    async with async_session() as db:
        run = await runtime.start_run(db, user_id, "plan", goal=goal)
        await db.commit()
        run_id = str(run.id)

    thread = {"configurable": {"thread_id": thread_id or run_id}}

    initial_state: AgentState = {
        "user_id": str(user_id),
        "run_id": run_id,
        "goal": goal,
        "diagnosis": None,
        "plan": None,
        "current_step": "starting",
        "messages": [],
        "error": None,
        "needs_approval": False,
        "approval_result": None,
    }

    try:
        result = await app.ainvoke(initial_state, thread)
        return {
            "run_id": run_id,
            "thread_id": thread_id or run_id,
            "status": "completed",
            "current_step": result.get("current_step"),
            "diagnosis": result.get("diagnosis"),
            "plan": result.get("plan"),
            "messages": result.get("messages", []),
        }
    except Exception as exc:
        logger.warning("Workflow failed: %s", exc)
        async with async_session() as db:
            await runtime.update_run_status(db, uuid.UUID(run_id), "failed", error_message=str(exc))
            await db.commit()
        return {"run_id": run_id, "status": "failed", "error": str(exc)}


async def resume_learning_workflow(
    thread_id: str,
    approval_result: str,
) -> dict:
    """恢复暂停的工作流（人工确认后）。

    Args:
        thread_id: 线程 ID
        approval_result: "approved" 或 "rejected"
    """
    graph = build_learning_workflow()
    app = graph.compile(checkpointer=_checkpointer)

    thread = {"configurable": {"thread_id": thread_id}}

    try:
        result = await app.ainvoke({"approval_result": approval_result}, thread)
        return {
            "thread_id": thread_id,
            "status": "completed",
            "current_step": result.get("current_step"),
            "messages": result.get("messages", []),
        }
    except Exception as exc:
        logger.warning("Workflow resume failed: %s", exc)
        return {"thread_id": thread_id, "status": "failed", "error": str(exc)}
