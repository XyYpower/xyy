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
        return f"我没有找到和“{query}”相关的知识库内容。你可以先导入或创建相关知识点。"
    source_lines = "\n".join(
        f"- {context['note_title']}：{context['chunk_text'][:160]}"
        for context in contexts
    )
    return f"根据当前知识库，和“{query}”相关的内容主要有：\n{source_lines}"
