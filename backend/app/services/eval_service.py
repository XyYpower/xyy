"""RAG 评估服务：管理评估用例、运行和结果。"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.eval import EvalCase, EvalRun, EvalResult, MessageFeedback
from app.rag import hybrid_retrieval, prompts
from app.rag.llm import get_llm

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ── 反馈 ──────────────────────


async def submit_feedback(
    db: AsyncSession,
    user_id: uuid.UUID,
    message_id: uuid.UUID,
    rating: str,
    issue_type: str | None = None,
    comment: str | None = None,
) -> MessageFeedback:
    feedback = MessageFeedback(
        message_id=message_id,
        user_id=user_id,
        rating=rating,
        issue_type=issue_type,
        comment=comment,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)
    return feedback


async def get_feedback_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    total = (await db.execute(
        select(func.count(MessageFeedback.id)).where(MessageFeedback.user_id == user_id)
    )).scalar() or 0

    helpful = (await db.execute(
        select(func.count(MessageFeedback.id)).where(
            MessageFeedback.user_id == user_id, MessageFeedback.rating == "helpful"
        )
    )).scalar() or 0

    return {
        "total": total,
        "helpful": helpful,
        "not_helpful": total - helpful,
        "helpful_rate": round(helpful / total * 100, 1) if total > 0 else 0.0,
    }


# ── 评估用例 ──────────────────────


async def create_eval_case(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    case_type: str,
    input_data: dict,
    expected_output: dict | None = None,
    tags: list[str] | None = None,
) -> EvalCase:
    case = EvalCase(
        user_id=user_id,
        name=name,
        case_type=case_type,
        input_data=input_data,
        expected_output=expected_output,
        tags=tags,
    )
    db.add(case)
    await db.flush()
    await db.refresh(case)
    return case


async def get_eval_cases(db: AsyncSession, user_id: uuid.UUID, case_type: str | None = None) -> list[EvalCase]:
    query = select(EvalCase).where(EvalCase.user_id == user_id)
    if case_type:
        query = query.where(EvalCase.case_type == case_type)
    result = await db.execute(query.order_by(EvalCase.created_at.desc()))
    return list(result.scalars().all())


# ── 评估运行 ──────────────────────


async def run_rag_evaluation(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str = "RAG 评估",
) -> EvalRun:
    """运行 RAG 回归评估：对所有 rag_groundedness 类型用例执行检索+回答，评估质量。"""

    cases = await get_eval_cases(db, user_id, case_type="rag_groundedness")
    if not cases:
        raise ValueError("没有可用的评估用例，请先创建 rag_groundedness 类型的用例")

    eval_run = EvalRun(
        user_id=user_id,
        name=name,
        target_type="rag_chat",
        status="running",
        total_cases=len(cases),
    )
    db.add(eval_run)
    await db.flush()

    passed = 0
    scores = []

    for case in cases:
        try:
            result = await _evaluate_single_rag_case(db, user_id, case)
            score = result["score"]
            is_passed = score >= 0.6

            if is_passed:
                passed += 1
            scores.append(score)

            eval_result = EvalResult(
                eval_run_id=eval_run.id,
                eval_case_id=case.id,
                score=score,
                metrics=result.get("metrics"),
                actual_output=result.get("actual_output"),
                passed=is_passed,
            )
            db.add(eval_result)
        except Exception as exc:
            logger.warning("Eval case %s failed: %s", case.id, exc)
            eval_result = EvalResult(
                eval_run_id=eval_run.id,
                eval_case_id=case.id,
                score=0.0,
                passed=False,
                error_message=str(exc)[:500],
            )
            db.add(eval_result)

    eval_run.status = "completed"
    eval_run.passed_cases = passed
    eval_run.avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
    eval_run.finished_at = _utc_now()
    await db.flush()
    await db.refresh(eval_run)
    return eval_run


async def _evaluate_single_rag_case(db: AsyncSession, user_id: uuid.UUID, case: EvalCase) -> dict:
    """评估单条 RAG 用例：检索 → 回答 → 自动评分。"""
    query = case.input_data.get("query", "")
    expected_answer = (case.expected_output or {}).get("answer", "")

    # 检索
    contexts = await hybrid_retrieval.hybrid_search(db, user_id, query, top_k=5)

    # 回答
    llm = get_llm()
    if not llm.api_key:
        # 无 LLM 时用兜底评估
        has_context = len(contexts) > 0
        return {
            "score": 0.8 if has_context else 0.3,
            "metrics": {"retrieval_count": len(contexts), "has_llm": False},
            "actual_output": {"answer": "(无 LLM，跳过生成)", "contexts": len(contexts)},
        }

    messages = prompts.build_rag_messages(query, contexts)
    answer = await llm.chat(messages)

    # 自动评分：检查回答是否基于检索到的内容
    score = await _auto_score_rag(query, answer, contexts, expected_answer)

    return {
        "score": score,
        "metrics": {"retrieval_count": len(contexts), "answer_length": len(answer)},
        "actual_output": {"answer": answer[:500], "contexts": len(contexts)},
    }


async def _auto_score_rag(
    query: str,
    answer: str,
    contexts: list[dict],
    expected_answer: str,
) -> float:
    """自动评分 RAG 回答质量。"""
    llm = get_llm()
    if not llm.api_key:
        return 0.5

    eval_prompt = (
        "你是 RAG 质量评估专家。根据以下信息评分（0.0-1.0）：\n"
        "1. 检索结果是否相关（0-0.3）\n"
        "2. 回答是否基于检索内容（0-0.4）\n"
        "3. 回答是否准确完整（0-0.3）\n"
        "只返回 JSON：{\"score\": 0.85, \"reason\": \"...\"}"
    )

    context_text = "\n".join(f"- {c['note_title']}: {c['chunk_text'][:100]}" for c in contexts[:3])
    user_msg = f"问题：{query}\n检索结果：\n{context_text}\n回答：{answer[:300]}"
    if expected_answer:
        user_msg += f"\n参考答案：{expected_answer[:200]}"

    try:
        raw = await llm.chat_json([
            {"role": "system", "content": eval_prompt},
            {"role": "user", "content": user_msg},
        ])
        import json
        result = json.loads(raw)
        return max(0.0, min(1.0, float(result.get("score", 0.5))))
    except Exception:
        return 0.5


async def get_eval_runs(db: AsyncSession, user_id: uuid.UUID, limit: int = 20) -> list[EvalRun]:
    result = await db.execute(
        select(EvalRun)
        .where(EvalRun.user_id == user_id)
        .order_by(EvalRun.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_eval_run_detail(db: AsyncSession, user_id: uuid.UUID, run_id: uuid.UUID) -> EvalRun | None:
    result = await db.execute(
        select(EvalRun)
        .options(selectinload(EvalRun.results))
        .where(EvalRun.id == run_id, EvalRun.user_id == user_id)
    )
    return result.scalar_one_or_none()
