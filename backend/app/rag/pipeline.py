import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag import prompts, retrieval
from app.rag.llm import get_llm


async def rag_query(db: AsyncSession, user_id: uuid.UUID, query: str) -> tuple[str, list[dict]]:
    contexts = await retrieval.search_similar(db, user_id, query, top_k=5)
    llm = get_llm()
    if not llm.api_key:
        return _fallback_answer(query, contexts), contexts

    messages = prompts.build_rag_messages(query, contexts)
    answer = await llm.chat(messages)
    return answer, contexts


def _fallback_answer(query: str, contexts: list[dict]) -> str:
    if not contexts:
        return "未配置 LLM API Key，无法调用 AI 模型。请前往 设置 → AI 配置 填入 API Key。"
    source_lines = "\n".join(
        "- {}: {}".format(ctx['note_title'], ctx['chunk_text'][:160])
        for ctx in contexts
    )
    return "从知识库中检索到相关内容（未配置 LLM，无法生成深度回答）：\n{}".format(source_lines)
