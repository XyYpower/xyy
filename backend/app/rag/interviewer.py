import json
import logging

from app.rag.llm import get_llm

logger = logging.getLogger(__name__)


async def generate_interview_questions(topics: list[str], num_questions: int = 5) -> list[dict[str, str]]:
    """根据知识点生成面试题；未配置 LLM 时使用本地兜底题。"""

    llm = get_llm()
    if not llm.api_key:
        return _fallback_questions(topics, num_questions)

    prompt = (
        "你是技术面试官。根据候选人的知识库内容生成编程面试题。"
        "题目要覆盖概念理解、项目实践、排查思路和边界权衡。"
        "每题必须包含 question 和 reference_answer。"
        f"生成 {num_questions} 道题，只返回 JSON："
        '{"questions":[{"question":"...","reference_answer":"..."}]}'
    )
    try:
        raw = await llm.chat_json(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "\n".join(topics[:20]) or "用户暂未提供知识点。"},
            ]
        )
        payload = json.loads(raw)
        questions = _normalize_questions(payload.get("questions", []), num_questions)
        if questions:
            return questions
        logger.warning("LLM interview question generation returned no usable questions; using fallback")
    except Exception:
        logger.warning("LLM interview question generation failed; using fallback", exc_info=True)

    return _fallback_questions(topics, num_questions)


async def evaluate_answer(question: str, answer: str, reference: str | None = None) -> dict[str, int | str]:
    """评分单题回答，返回 score 和 feedback。"""

    llm = get_llm()
    if not llm.api_key:
        return _fallback_evaluation(answer)

    prompt = (
        "你是严谨但鼓励型的技术面试官。请根据题目、参考答案和候选人回答评分。"
        "评分标准：1-3=概念错误或未回答，4-6=部分正确有遗漏，7-8=基本正确，9-10=优秀有深度。"
        '只返回 JSON：{"score":1-10,"feedback":"评价和改进建议"}'
    )
    content = f"面试题：{question}\n"
    if reference:
        content += f"参考答案：{reference}\n"
    content += f"候选人回答：{answer}"
    try:
        raw = await llm.chat_json(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": content},
            ]
        )
        payload = json.loads(raw)
        return _normalize_evaluation(payload)
    except Exception:
        logger.warning("LLM answer evaluation failed; using fallback", exc_info=True)
        return _fallback_evaluation(answer)


async def generate_session_summary(questions: list[dict]) -> str:
    """生成面试总结。"""

    llm = get_llm()
    if not llm.api_key:
        return _fallback_summary(questions)

    prompt = (
        "你是技术面试复盘助手。根据每道题、候选人回答、评分和反馈，"
        "总结整体表现、薄弱点和下一步学习建议。回答用中文，控制在 300 字以内。"
    )
    try:
        return await llm.chat(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps({"questions": questions}, ensure_ascii=False)},
            ]
        )
    except Exception:
        logger.warning("LLM interview summary failed; using fallback", exc_info=True)
        return _fallback_summary(questions)


def _normalize_questions(items: list[dict], limit: int) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    for item in items:
        question = str(item.get("question", "")).strip()
        reference = str(item.get("reference_answer", "")).strip()
        if question:
            questions.append(
                {
                    "question": question,
                    "reference_answer": reference or "请围绕核心概念、实践场景和常见问题展开回答。",
                }
            )
    return questions[:limit]


def _normalize_evaluation(payload: dict) -> dict[str, int | str]:
    try:
        score = int(payload.get("score", 5))
    except (TypeError, ValueError):
        score = 5
    score = max(1, min(10, score))
    feedback = str(payload.get("feedback", "")).strip() or "回答已记录，请继续补充关键细节。"
    return {"score": score, "feedback": feedback}


def _fallback_questions(topics: list[str], num_questions: int) -> list[dict[str, str]]:
    if not topics:
        topics = ["你最近学习过的一个技术知识点"]
    result: list[dict[str, str]] = []
    for index in range(num_questions):
        topic = topics[index % len(topics)].splitlines()[0][:80]
        result.append(
            {
                "question": f"请解释 {topic} 的核心原理，并结合一个项目场景说明你会怎么使用它。",
                "reference_answer": f"回答应覆盖 {topic} 的定义、适用场景、常见坑点和权衡。",
            }
        )
    return result


def _fallback_evaluation(answer: str) -> dict[str, int | str]:
    word_count = len(answer.strip())
    if word_count >= 120:
        score = 7
        feedback = "回答较完整。建议继续补充具体项目案例、边界条件和排查步骤。"
    elif word_count >= 40:
        score = 6
        feedback = "回答有基本方向，但细节偏少。建议补充原理、示例和常见误区。"
    else:
        score = 4
        feedback = "回答较短，信息不足。建议先说明概念，再展开使用场景和实现细节。"
    return {"score": score, "feedback": feedback}


def _fallback_summary(questions: list[dict]) -> str:
    answered = [item for item in questions if item.get("user_answer")]
    scores = [int(item["ai_score"]) for item in answered if item.get("ai_score") is not None]
    if not scores:
        return "本次面试还没有有效评分。建议补全回答后再结束面试。"
    avg = sum(scores) / len(scores)
    return f"本次面试完成 {len(answered)} 道题，平均分 {avg:.1f}/10。建议优先复盘低分题，并把遗漏点补充到知识点中。"
